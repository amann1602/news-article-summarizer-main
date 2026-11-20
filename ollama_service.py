"""Ollama local REST API integration for structured article summaries."""

from __future__ import annotations

import re

import requests

from news_summarizer.text_processor import chunk_article, prepare_article

OLLAMA_CHAT_ENDPOINT = "http://localhost:11434/api/chat"
OLLAMA_TAGS_ENDPOINT = "http://localhost:11434/api/tags"
OLLAMA_MODEL = "qwen2.5:3b"
_REQUEST_TIMEOUT = (5, 180)


class OllamaServiceError(RuntimeError):
    """Base error for Ollama availability, response, or generation failures."""


class OllamaUnavailableError(OllamaServiceError):
    """Raised when the local Ollama server cannot be reached."""


class OllamaModelMissingError(OllamaServiceError):
    """Raised when the configured model is not installed locally."""


class OllamaResponseError(OllamaServiceError):
    """Raised when Ollama returns an unusable or malformed response."""


_FORMAT_INSTRUCTIONS = """Summarize the provided news article in exactly 5 concise lines. Then provide exactly 3 important key points. Preserve important names, dates, events, facts, and figures. Do not add information that is not present in the original article.

Use exactly this output format, with one summary sentence on each numbered line:
SUMMARY:
1. ...
2. ...
3. ...
4. ...
5. ...
KEY POINTS:
- ...
- ...
- ..."""


def _check_ollama() -> None:
    try:
        response = requests.get(OLLAMA_TAGS_ENDPOINT, timeout=(3, 5))
    except requests.RequestException:
        raise OllamaUnavailableError(
            "Ollama is not running or is unavailable at http://localhost:11434. "
            "Start Ollama and try again."
        ) from None

    if response.status_code >= 500:
        raise OllamaUnavailableError(
            f"Ollama returned HTTP {response.status_code} while checking availability."
        )
    if response.status_code >= 400:
        raise OllamaServiceError(
            f"Ollama returned HTTP {response.status_code} while checking availability."
        )
    try:
        tags = response.json().get("models", [])
        installed_models = {model.get("name") for model in tags if isinstance(model, dict)}
    except (ValueError, AttributeError, TypeError):
        raise OllamaResponseError("Ollama returned an invalid model list.") from None

    if not any(
        name == OLLAMA_MODEL or (isinstance(name, str) and name.startswith(OLLAMA_MODEL + ":"))
        for name in installed_models
    ):
        raise OllamaModelMissingError(
            f"The local model {OLLAMA_MODEL} is not installed. Run: ollama pull {OLLAMA_MODEL}"
        )


def _chat(user_prompt: str) -> str:
    payload = {
        "model": OLLAMA_MODEL,
        "messages": [
            {"role": "system", "content": "You are a precise news article summarizer."},
            {"role": "user", "content": user_prompt},
        ],
        "stream": False,
        "options": {"temperature": 0.2},
    }
    try:
        response = requests.post(
            OLLAMA_CHAT_ENDPOINT,
            json=payload,
            timeout=_REQUEST_TIMEOUT,
        )
    except requests.Timeout:
        raise OllamaServiceError(
            "Ollama took too long to generate a response. Try a shorter article or retry."
        ) from None
    except requests.RequestException:
        raise OllamaUnavailableError(
            "Could not connect to Ollama. Confirm it is running and try again."
        ) from None

    if response.status_code == 404:
        raise OllamaModelMissingError(
            f"The local model {OLLAMA_MODEL} is unavailable. Run: ollama pull {OLLAMA_MODEL}"
        )
    if response.status_code >= 400:
        raise OllamaServiceError(f"Ollama returned HTTP {response.status_code}.")
    try:
        data = response.json()
        content = data["message"]["content"]
    except (ValueError, KeyError, TypeError):
        raise OllamaResponseError("Ollama returned an invalid chat response.") from None
    if not isinstance(content, str) or not content.strip():
        raise OllamaResponseError("Ollama returned an empty response.")
    return content.strip()


def _parse_summary(response: str) -> dict[str, list[str]]:
    match = re.search(
        r"SUMMARY\s*:\s*(.*?)\s*KEY\s*POINTS\s*:\s*(.*)",
        response,
        flags=re.IGNORECASE | re.DOTALL,
    )
    if not match:
        raise OllamaResponseError(
            "Ollama's response did not contain the required summary and key-points sections. "
            "Please try again."
        )

    summary_lines = [
        re.sub(r"^\s*(?:[-*•]|\d+[.)])\s*", "", line).strip()
        for line in match.group(1).splitlines()
    ]
    key_points = [
        re.sub(r"^\s*(?:[-*•]|\d+[.)])\s*", "", line).strip()
        for line in match.group(2).splitlines()
    ]
    summary_lines = [line for line in summary_lines if line]
    key_points = [line for line in key_points if line]
    if len(summary_lines) != 5 or len(key_points) != 3:
        raise OllamaResponseError(
            "Ollama did not provide exactly 5 summary lines and 3 key points. "
            "Please try again."
        )
    return {"summary": summary_lines, "key_points": key_points}


def _generate_summary(article_material: str) -> dict[str, list[str]]:
    initial_response = _chat(
        f"{_FORMAT_INSTRUCTIONS}\n\nArticle:\n{article_material}"
    )
    try:
        return _parse_summary(initial_response)
    except OllamaResponseError:
        corrected_response = _chat(
            f"{_FORMAT_INSTRUCTIONS}\n\n"
            "Your previous attempt did not follow the required item counts. "
            "Rewrite it with exactly five numbered summary lines and exactly three "
            "key-point bullets. Count them before responding; do not include extra "
            "items or any text outside the specified sections. Use no facts beyond "
            "the article material and retain its important information.\n\n"
            f"Article material:\n{article_material}\n\n"
            f"Previous attempt:\n{initial_response}"
        )
        try:
            return _parse_summary(corrected_response)
        except OllamaResponseError:
            raise OllamaResponseError(
                "Ollama did not follow the required format after a correction attempt. "
                "Please try again."
            ) from None


def summarize_article(article_text: str) -> dict[str, list[str]]:
    """Summarize an article through Ollama and return validated, structured output."""
    article = prepare_article(article_text)
    _check_ollama()
    chunks = chunk_article(article)

    if len(chunks) == 1:
        return _generate_summary(chunks[0])

    notes = []
    for index, chunk in enumerate(chunks, start=1):
        notes.append(
            _chat(
                "Extract concise factual notes from this section of a news article. "
                "Retain every material name, date, event, claim, and figure. "
                f"This is section {index} of {len(chunks)}; do not infer missing context.\n\n"
                f"Article section:\n{chunk}"
            )
        )

    combined_notes = "\n\n".join(
        f"Section {index} notes:\n{note}" for index, note in enumerate(notes, start=1)
    )
    return _generate_summary(
        "The following are factual notes covering all sections of the original article. "
        "Use only these notes and do not add facts:\n\n"
        f"{combined_notes}"
    )
