"""Historical notes management endpoints."""

import logging
import uuid
from typing import Any

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status

from app.auth.dependencies import get_current_user
from app.models.note import NoteResponse, SourceType
from app.services.blob_storage import blob_service
from app.services.cosmos_db import cosmos_service
from app.services.ai_search import ai_search_service
from app.services.style_extraction import style_extraction_service
from app.utils.file_parser import FileParserError, extract_text

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/doctors/{doctor_id}/notes", tags=["notes"])


@router.post("", response_model=NoteResponse, status_code=status.HTTP_201_CREATED)
async def create_note(
    doctor_id: str,
    content: str | None = Form(default=None),
    file: UploadFile | None = File(default=None),
    user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    """
    Upload a file or paste text as a historical note for a doctor.

    Either `content` (pasted text) or `file` (uploaded document) must be provided.
    """
    _enforce_note_access(user, doctor_id)

    if file and file.filename:
        # Handle file upload
        file_content = await file.read()
        try:
            text = extract_text(file.filename, file_content)
        except FileParserError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)
            ) from e

        # Store the original file in blob storage
        unique_name = f"{uuid.uuid4()}_{file.filename}"
        await blob_service.upload_file(
            doctor_id=doctor_id,
            file_name=unique_name,
            content=file_content,
            content_type=file.content_type or "application/octet-stream",
        )

        note_data = {
            "content": text,
            "source_type": SourceType.UPLOAD,
            "file_name": file.filename,
        }
    elif content:
        note_data = {
            "content": content,
            "source_type": SourceType.PASTE,
            "file_name": None,
        }
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Either 'content' or 'file' must be provided",
        )

    note = await cosmos_service.create_note(doctor_id, note_data)

    # Index note in AI Search for RAG retrieval
    try:
        await ai_search_service.index_note({
            "id": note["id"],
            "doctor_id": doctor_id,
            "content": note["content"],
            "report_type": "",
            "body_region": "",
            "findings": "",
            "impressions": "",
            "recommendations": "",
            "created_at": note["created_at"],
        })
    except Exception as e:
        logger.warning("Failed to index note in AI Search: %s", e)

    # Re-extract style profile asynchronously (best-effort)
    try:
        await style_extraction_service.extract_style(doctor_id)
    except Exception as e:
        logger.warning("Style re-extraction failed after note upload: %s", e)

    return note


@router.get("", response_model=list[NoteResponse])
async def list_notes(
    doctor_id: str,
    user: dict[str, Any] = Depends(get_current_user),
) -> list[dict[str, Any]]:
    """List all notes for a doctor."""
    _enforce_note_access(user, doctor_id)
    return await cosmos_service.list_notes(doctor_id)


@router.delete("/{note_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_note(
    doctor_id: str,
    note_id: str,
    user: dict[str, Any] = Depends(get_current_user),
) -> None:
    """Delete a specific note."""
    _enforce_note_access(user, doctor_id)

    note = await cosmos_service.get_note(doctor_id, note_id)
    if not note:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Note not found")

    # Delete from blob storage if it was an uploaded file
    if note.get("file_name"):
        try:
            await blob_service.delete_file(doctor_id, note["file_name"])
        except Exception as e:
            logger.warning("Failed to delete blob for note %s: %s", note_id, e)

    # Delete from search index
    try:
        await ai_search_service.delete_document(note_id)
    except Exception as e:
        logger.warning("Failed to delete note %s from search index: %s", note_id, e)

    await cosmos_service.delete_note(doctor_id, note_id)

    # Re-extract style profile after note removal (best-effort)
    try:
        await style_extraction_service.extract_style(doctor_id)
    except Exception as e:
        logger.warning("Style re-extraction failed after note deletion: %s", e)


def _enforce_note_access(user: dict[str, Any], doctor_id: str) -> None:
    """Ensure non-admin users can only access their own notes."""
    if "Admin" in user.get("roles", []):
        return
    if user.get("user_id") != doctor_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only manage your own notes",
        )
