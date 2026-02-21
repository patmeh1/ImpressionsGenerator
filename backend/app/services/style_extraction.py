"""Style extraction service for analyzing doctor writing patterns."""

import logging
from typing import Any

from app.models.style_profile import StyleProfile
from app.services.cosmos_db import cosmos_service
from app.services.openai_service import openai_service

logger = logging.getLogger(__name__)


class StyleExtractionService:
    """Analyzes doctor notes to extract and maintain writing style profiles."""

    async def extract_style(self, doctor_id: str) -> StyleProfile:
        """
        Analyze all notes for a doctor and extract their writing style.

        Fetches historical notes, sends them to Azure OpenAI for analysis,
        and persists the resulting style profile.
        """
        notes = await cosmos_service.list_notes(doctor_id)
        if not notes:
            logger.warning("No notes found for doctor %s; returning empty style profile", doctor_id)
            return StyleProfile(doctor_id=doctor_id)

        # Combine all note content for analysis
        combined_text = self._prepare_notes_text(notes)
        logger.info(
            "Analyzing %d notes for doctor %s (%d chars)",
            len(notes), doctor_id, len(combined_text),
        )

        style_data = await openai_service.analyze_style(combined_text)

        profile = StyleProfile(
            doctor_id=doctor_id,
            vocabulary_patterns=style_data.get("vocabulary_patterns", []),
            abbreviation_map=style_data.get("abbreviation_map", {}),
            sentence_structure=style_data.get("sentence_structure", []),
            section_ordering=style_data.get("section_ordering", []),
            sample_phrases=style_data.get("sample_phrases", []),
        )

        # Persist the style profile
        profile_dict = profile.model_dump()
        existing = await cosmos_service.get_style_profile(doctor_id)
        if existing:
            profile_dict["id"] = existing["id"]
        await cosmos_service.upsert_style_profile(profile_dict)

        logger.info("Style profile updated for doctor %s", doctor_id)
        return profile

    def _prepare_notes_text(self, notes: list[dict[str, Any]]) -> str:
        """Combine notes into a single text block for analysis."""
        sections = []
        for i, note in enumerate(notes, 1):
            content = note.get("content", "").strip()
            if content:
                sections.append(f"--- Note {i} ---\n{content}")

        combined = "\n\n".join(sections)

        # Truncate to avoid token limits (roughly 100K chars ~ 25K tokens)
        max_chars = 100_000
        if len(combined) > max_chars:
            logger.info("Truncating notes text from %d to %d chars", len(combined), max_chars)
            combined = combined[:max_chars]

        return combined

    def build_style_instructions(self, profile: StyleProfile) -> str:
        """Convert a style profile into natural language instructions for the LLM."""
        parts: list[str] = []

        if profile.vocabulary_patterns:
            terms = ", ".join(profile.vocabulary_patterns[:20])
            parts.append(f"Use these preferred medical terms: {terms}")

        if profile.abbreviation_map:
            abbrevs = ", ".join(
                f"{k} = {v}" for k, v in list(profile.abbreviation_map.items())[:15]
            )
            parts.append(f"Apply these abbreviations: {abbrevs}")

        if profile.sentence_structure:
            structures = "; ".join(profile.sentence_structure[:10])
            parts.append(f"Sentence style: {structures}")

        if profile.section_ordering:
            ordering = " → ".join(profile.section_ordering)
            parts.append(f"Section order: {ordering}")

        if profile.sample_phrases:
            phrases = "; ".join(f'"{p}"' for p in profile.sample_phrases[:10])
            parts.append(f"Characteristic phrases to emulate: {phrases}")

        if not parts:
            return "No specific style preferences available. Use standard radiology reporting style."

        return "\n".join(parts)


# Singleton instance
style_extraction_service = StyleExtractionService()
