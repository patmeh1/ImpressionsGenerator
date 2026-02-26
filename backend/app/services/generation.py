"""Orchestrator service for report generation pipeline."""

import logging
from typing import Any

from app.models.style_profile import StyleProfile
from app.services.ai_search import ai_search_service
from app.services.cosmos_db import cosmos_service
from app.services.grounding import validate_grounding
from app.services.openai_service import openai_service
from app.services.style_extraction import style_extraction_service

logger = logging.getLogger(__name__)


class DoctorNotFoundError(Exception):
    """Raised when the specified doctor does not exist."""


class GenerationService:
    """
    Orchestrates the full report generation pipeline:
    1. Retrieve or build the doctor's style profile
    2. Fetch few-shot examples from AI Search (RAG)
    3. Build prompt with style + grounding rules
    4. Call Azure OpenAI GPT-4o
    5. Validate grounding of generated output
    6. Persist and return the report
    """

    async def generate(
        self,
        dictated_text: str,
        doctor_id: str,
        report_type: str = "",
        body_region: str = "",
    ) -> dict[str, Any]:
        """Execute the full generation pipeline."""
        logger.info(
            "Starting generation for doctor %s (type=%s, region=%s)",
            doctor_id, report_type, body_region,
        )

        # 0. Verify the doctor exists
        doctor = await cosmos_service.get_doctor(doctor_id)
        if doctor is None:
            raise DoctorNotFoundError(f"Doctor '{doctor_id}' not found")

        # 1. Retrieve or extract the style profile
        style_profile = await self._get_or_build_style_profile(doctor_id)
        style_instructions = style_extraction_service.build_style_instructions(style_profile)

        # 2. Search for similar notes as few-shot examples
        few_shot_examples = await self._get_few_shot_examples(
            doctor_id, dictated_text, report_type, body_region
        )

        # 3. Build grounding rules from input
        grounding_rules = self._build_grounding_rules(dictated_text)

        # 4. Call Azure OpenAI
        generated = await openai_service.generate_report(
            dictated_text=dictated_text,
            style_instructions=style_instructions,
            grounding_rules=grounding_rules,
            few_shot_examples=few_shot_examples,
            report_type=report_type,
            body_region=body_region,
        )

        # 5. Validate grounding
        output_text = " ".join([
            generated.get("findings", ""),
            generated.get("impressions", ""),
            generated.get("recommendations", ""),
        ])
        grounding_result = validate_grounding(dictated_text, output_text)

        # 6. Persist the report
        report_data = {
            "doctor_id": doctor_id,
            "input_text": dictated_text,
            "report_type": report_type,
            "body_region": body_region,
            "findings": generated["findings"],
            "impressions": generated["impressions"],
            "recommendations": generated["recommendations"],
        }
        report = await cosmos_service.create_report(report_data)

        # Index the report for future RAG retrieval
        try:
            await ai_search_service.index_report(report)
        except Exception as e:
            logger.warning("Failed to index report for search: %s", e)

        # Attach grounding info to response
        report["grounding_validation"] = grounding_result.to_dict()

        logger.info(
            "Generation complete: report %s (grounded=%s)",
            report["id"], grounding_result.is_grounded,
        )
        return report

    async def _get_or_build_style_profile(self, doctor_id: str) -> StyleProfile:
        """Retrieve existing style profile or build one from notes."""
        existing = await cosmos_service.get_style_profile(doctor_id)
        if existing:
            logger.info("Using existing style profile for doctor %s", doctor_id)
            return StyleProfile(**{
                k: v for k, v in existing.items()
                if k in StyleProfile.model_fields
            })

        logger.info("No style profile found; extracting for doctor %s", doctor_id)
        try:
            return await style_extraction_service.extract_style(doctor_id)
        except Exception as e:
            logger.warning("Style extraction failed for doctor %s: %s", doctor_id, e)
            return StyleProfile(doctor_id=doctor_id)

    async def _get_few_shot_examples(
        self,
        doctor_id: str,
        query_text: str,
        report_type: str,
        body_region: str,
    ) -> list[dict[str, Any]]:
        """Fetch similar notes from AI Search for few-shot prompting."""
        try:
            examples = await ai_search_service.search_similar_notes(
                doctor_id=doctor_id,
                query_text=query_text,
                report_type=report_type or None,
                body_region=body_region or None,
                top=3,
            )
            logger.info("Retrieved %d few-shot examples", len(examples))
            return examples
        except Exception as e:
            logger.warning("Failed to retrieve few-shot examples: %s", e)
            return []

    def _build_grounding_rules(self, dictated_text: str) -> str:
        """Build grounding rules that instruct the model about input constraints."""
        return (
            "CRITICAL GROUNDING CONSTRAINTS:\n"
            "1. Every measurement, number, date, and percentage in your output "
            "MUST come directly from the dictated input.\n"
            "2. Do NOT invent or infer any quantitative values.\n"
            "3. If the dictation mentions a finding without specific measurements, "
            "describe it qualitatively without adding numbers.\n"
            "4. Preserve all specific values from the dictation exactly as stated.\n"
            f"5. The input dictation contains these key details to preserve:\n"
            f"   {dictated_text[:500]}"
        )


# Singleton instance
generation_service = GenerationService()
