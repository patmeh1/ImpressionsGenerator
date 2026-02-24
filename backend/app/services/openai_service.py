"""Azure OpenAI service for clinical report generation."""

import json
import logging
from typing import Any

from azure.identity import DefaultAzureCredential, get_bearer_token_provider
from openai import AzureOpenAI

from app.config import settings

logger = logging.getLogger(__name__)


class OpenAIService:
    """Manages interactions with Azure OpenAI GPT-4o."""

    def __init__(self) -> None:
        self._client: AzureOpenAI | None = None

    async def initialize(self) -> None:
        """Initialize the Azure OpenAI client."""
        credential = DefaultAzureCredential()
        token_provider = get_bearer_token_provider(
            credential, "https://cognitiveservices.azure.com/.default"
        )
        self._client = AzureOpenAI(
            azure_endpoint=settings.OPENAI_ENDPOINT,
            azure_ad_token_provider=token_provider,
            api_version=settings.OPENAI_API_VERSION,
        )
        logger.info("Azure OpenAI client initialized")

    def _build_system_prompt(
        self,
        style_instructions: str,
        grounding_rules: str,
    ) -> str:
        """Build the system prompt with style and grounding instructions."""
        return f"""You are a clinical radiology/oncology report generation assistant.
Your task is to transform dictated radiology findings into a structured clinical report
that matches the writing style of the specific doctor.

STYLE INSTRUCTIONS:
{style_instructions}

GROUNDING RULES:
{grounding_rules}

IMPORTANT:
- You MUST NOT invent any clinical measurements, numbers, or findings.
- Only include clinical information explicitly stated or directly implied by the dictation.
- Do NOT fabricate measurements, dates, values, or findings.
- Every number, measurement, and percentage in the output MUST originate from the input.
- Maintain medical accuracy and appropriate clinical terminology.
- Structure the output as JSON with keys: "findings", "impressions", "recommendations".

Respond ONLY with valid JSON."""

    def _build_few_shot_messages(
        self, examples: list[dict[str, Any]]
    ) -> list[dict[str, str]]:
        """Build few-shot example messages from similar historical notes."""
        messages: list[dict[str, str]] = []
        for ex in examples[:3]:  # Limit to 3 examples
            messages.append({
                "role": "user",
                "content": f"Dictation: {ex.get('input_text', ex.get('content', ''))}",
            })
            output = {
                "findings": ex.get("findings", ""),
                "impressions": ex.get("impressions", ""),
                "recommendations": ex.get("recommendations", ""),
            }
            messages.append({
                "role": "assistant",
                "content": json.dumps(output),
            })
        return messages

    async def generate_report(
        self,
        dictated_text: str,
        style_instructions: str,
        grounding_rules: str,
        few_shot_examples: list[dict[str, Any]] | None = None,
        report_type: str = "",
        body_region: str = "",
    ) -> dict[str, str]:
        """
        Generate a structured clinical report from dictation.

        Returns dict with findings, impressions, and recommendations.
        """
        if self._client is None:
            raise RuntimeError("OpenAIService not initialized")

        system_prompt = self._build_system_prompt(style_instructions, grounding_rules)
        messages: list[dict[str, str]] = [
            {"role": "system", "content": system_prompt},
        ]

        if few_shot_examples:
            messages.extend(self._build_few_shot_messages(few_shot_examples))

        user_content = f"Dictation: {dictated_text}"
        if report_type:
            user_content += f"\nReport Type: {report_type}"
        if body_region:
            user_content += f"\nBody Region: {body_region}"

        messages.append({"role": "user", "content": user_content})

        logger.info(
            "Calling GPT-4o with %d messages (%d few-shot examples)",
            len(messages),
            len(few_shot_examples or []),
        )

        response = self._client.chat.completions.create(
            model=settings.OPENAI_DEPLOYMENT_NAME,
            messages=messages,
            temperature=0.3,
            max_tokens=2000,
            response_format={"type": "json_object"},
        )

        content = response.choices[0].message.content
        if not content:
            raise RuntimeError("Empty response from Azure OpenAI")

        # Extract token usage when available
        token_usage: dict[str, int] | None = None
        if response.usage:
            token_usage = {
                "prompt_tokens": response.usage.prompt_tokens or 0,
                "completion_tokens": response.usage.completion_tokens or 0,
                "total_tokens": response.usage.total_tokens or 0,
            }

        try:
            result = json.loads(content)
        except json.JSONDecodeError as e:
            logger.error("Failed to parse OpenAI response as JSON: %s", e)
            raise RuntimeError(f"Invalid JSON response from model: {e}") from e

        return {
            "findings": result.get("findings", ""),
            "impressions": result.get("impressions", ""),
            "recommendations": result.get("recommendations", ""),
            "token_usage": token_usage,
        }

    async def analyze_style(self, notes_text: str) -> dict[str, Any]:
        """
        Analyze a collection of notes to extract writing style features.

        Returns structured style profile data.
        """
        if self._client is None:
            raise RuntimeError("OpenAIService not initialized")

        system_prompt = """You are an expert linguistic analyst specializing in medical writing.
Analyze the provided clinical notes and extract the doctor's writing style features.

Return a JSON object with these keys:
- "vocabulary_patterns": list of common medical terms and phrases the doctor favors
- "abbreviation_map": dict mapping abbreviations to their full forms
- "sentence_structure": list describing typical sentence patterns
- "section_ordering": list of how the doctor typically orders report sections
- "sample_phrases": list of characteristic phrases the doctor commonly uses

Respond ONLY with valid JSON."""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Clinical notes to analyze:\n\n{notes_text}"},
        ]

        response = self._client.chat.completions.create(
            model=settings.OPENAI_DEPLOYMENT_NAME,
            messages=messages,
            temperature=0.2,
            max_tokens=2000,
            response_format={"type": "json_object"},
        )

        content = response.choices[0].message.content
        if not content:
            raise RuntimeError("Empty response from Azure OpenAI during style analysis")

        try:
            return json.loads(content)
        except json.JSONDecodeError as e:
            logger.error("Failed to parse style analysis response: %s", e)
            raise RuntimeError(f"Invalid JSON from style analysis: {e}") from e


# Singleton instance
openai_service = OpenAIService()
