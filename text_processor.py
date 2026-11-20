"""Text cleanup, validation, and context-aware article chunking."""

from __future__ import annotations

import re


class ArticleTextError(ValueError):
    """Raised when article text is empty, too short, or too large to process."""


MIN_ARTICLE_CHARACTERS = 100
MAX_ARTICLE_CHARACTERS = 200_000
CHUNK_CHARACTERS = 8_000


def clean_text(text: str) -> str:
    """Normalize whitespace while retaining paragraph boundaries."""
    if not isinstance(text, str):
        raise ArticleTextError("Article content must be plain text.")
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    paragraphs = [
        re.sub(r"[ \t\f\v]+", " ", paragraph).strip()
        for paragraph in text.split("\n")
    ]
    paragraphs = [paragraph for paragraph in paragraphs if paragraph]
    return "\n\n".join(paragraphs)


def prepare_article(text: str) -> str:
    """Clean and validate input without truncating article content."""
    cleaned = clean_text(text)
    if len(cleaned) < MIN_ARTICLE_CHARACTERS:
        raise ArticleTextError(
            f"Please provide a longer article (at least {MIN_ARTICLE_CHARACTERS} characters)."
        )
    if len(cleaned) > MAX_ARTICLE_CHARACTERS:
        raise ArticleTextError(
            f"The article is too long to process safely ({len(cleaned):,} characters). "
            f"The limit is {MAX_ARTICLE_CHARACTERS:,}; shorten it and try again."
        )
    return cleaned


def _split_long_paragraph(paragraph: str, limit: int) -> list[str]:
    sentences = re.split(r"(?<=[.!?])\s+", paragraph)
    pieces: list[str] = []
    current = ""
    for sentence in sentences:
        if len(sentence) > limit:
            if current:
                pieces.append(current)
                current = ""
            words = sentence.split()
            segment = ""
            for word in words:
                if len(word) > limit:
                    if segment:
                        pieces.append(segment)
                        segment = ""
                    pieces.extend(
                        word[start : start + limit]
                        for start in range(0, len(word), limit)
                    )
                    continue
                candidate = f"{segment} {word}".strip()
                if len(candidate) > limit and segment:
                    pieces.append(segment)
                    segment = word
                else:
                    segment = candidate
            if segment:
                pieces.append(segment)
        else:
            candidate = f"{current} {sentence}".strip()
            if len(candidate) > limit and current:
                pieces.append(current)
                current = sentence
            else:
                current = candidate
    if current:
        pieces.append(current)
    return pieces


def chunk_article(text: str, max_characters: int = CHUNK_CHARACTERS) -> list[str]:
    """Split all article content into bounded chunks, preserving its order."""
    if max_characters < 1:
        raise ValueError("max_characters must be positive.")
    paragraphs = clean_text(text).split("\n\n")
    chunks: list[str] = []
    current = ""

    for paragraph in paragraphs:
        pieces = (
            _split_long_paragraph(paragraph, max_characters)
            if len(paragraph) > max_characters
            else [paragraph]
        )
        for piece in pieces:
            candidate = f"{current}\n\n{piece}".strip()
            if len(candidate) > max_characters and current:
                chunks.append(current)
                current = piece
            else:
                current = candidate
    if current:
        chunks.append(current)
    return chunks
