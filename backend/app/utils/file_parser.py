"""File parser utilities for extracting text from uploaded documents."""

import io
import logging

from PyPDF2 import PdfReader
from docx import Document

logger = logging.getLogger(__name__)

MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB
ALLOWED_EXTENSIONS = {".pdf", ".docx", ".txt"}


class FileParserError(Exception):
    """Raised when file parsing fails."""


def validate_file(file_name: str, file_size: int) -> None:
    """Validate file size and extension."""
    if file_size > MAX_FILE_SIZE:
        raise FileParserError(
            f"File size {file_size} bytes exceeds maximum of {MAX_FILE_SIZE} bytes (10 MB)"
        )

    ext = _get_extension(file_name)
    if ext not in ALLOWED_EXTENSIONS:
        raise FileParserError(
            f"Unsupported file type '{ext}'. Allowed types: {', '.join(sorted(ALLOWED_EXTENSIONS))}"
        )


def _get_extension(file_name: str) -> str:
    """Extract lowercase file extension."""
    dot_index = file_name.rfind(".")
    if dot_index == -1:
        return ""
    return file_name[dot_index:].lower()


def extract_text(file_name: str, content: bytes) -> str:
    """
    Extract plain text from a file based on its extension.

    Supports PDF, DOCX, and TXT files.
    """
    validate_file(file_name, len(content))
    ext = _get_extension(file_name)

    if ext == ".pdf":
        return _extract_from_pdf(content)
    elif ext == ".docx":
        return _extract_from_docx(content)
    elif ext == ".txt":
        return _extract_from_txt(content)
    else:
        raise FileParserError(f"Unsupported file type: {ext}")


def _extract_from_pdf(content: bytes) -> str:
    """Extract text from a PDF file."""
    try:
        reader = PdfReader(io.BytesIO(content))
        pages = []
        for page in reader.pages:
            text = page.extract_text()
            if text:
                pages.append(text)
        result = "\n\n".join(pages).strip()
        if not result:
            raise FileParserError("PDF contains no extractable text")
        return result
    except FileParserError:
        raise
    except Exception as e:
        logger.error("Failed to parse PDF: %s", e)
        raise FileParserError(f"Failed to parse PDF: {e}") from e


def _extract_from_docx(content: bytes) -> str:
    """Extract text from a DOCX file."""
    try:
        doc = Document(io.BytesIO(content))
        paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
        result = "\n\n".join(paragraphs).strip()
        if not result:
            raise FileParserError("DOCX contains no extractable text")
        return result
    except FileParserError:
        raise
    except Exception as e:
        logger.error("Failed to parse DOCX: %s", e)
        raise FileParserError(f"Failed to parse DOCX: {e}") from e


def _extract_from_txt(content: bytes) -> str:
    """Extract text from a plain text file."""
    try:
        text = content.decode("utf-8").strip()
        if not text:
            raise FileParserError("TXT file is empty")
        return text
    except UnicodeDecodeError as e:
        raise FileParserError(f"Failed to decode text file: {e}") from e
