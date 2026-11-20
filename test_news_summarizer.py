from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

from bs4 import BeautifulSoup

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from news_summarizer.article_extractor import _remove_unwanted_elements
from news_summarizer.ollama_service import (
    OllamaResponseError,
    _parse_summary,
    summarize_article,
)
from news_summarizer.text_processor import chunk_article, clean_text


VALID_RESPONSE = """SUMMARY:
1. First summary line.
2. Second summary line.
3. Third summary line.
4. Fourth summary line.
5. Fifth summary line.
KEY POINTS:
- First key point.
- Second key point.
- Third key point."""


class ArticleExtractorTests(unittest.TestCase):
    def test_removing_nested_unwanted_elements_does_not_raise(self) -> None:
        soup = BeautifulSoup(
            '<html><body><div class="advertisement"><p>Ignore this content.</p></div>'
            "<nav><aside><p>Ignore nested navigation.</p></aside></nav>"
            "<main><p>Keep this article content.</p></main></body></html>",
            "lxml",
        )

        _remove_unwanted_elements(soup)

        self.assertIsNone(soup.find(class_="advertisement"))
        self.assertEqual(soup.main.get_text(" ", strip=True), "Keep this article content.")


class TextProcessorTests(unittest.TestCase):
    def test_chunking_respects_limit_without_dropping_text(self) -> None:
        article = (
            "First paragraph contains a report with names and figures. " * 20
            + "\n\n"
            + "x" * 10_000
        )

        chunks = chunk_article(article, max_characters=300)

        self.assertGreater(len(chunks), 1)
        self.assertTrue(all(len(chunk) <= 300 for chunk in chunks))
        self.assertEqual(
            "".join(clean_text(article).split()),
            "".join("".join(chunks).split()),
        )


class OllamaServiceTests(unittest.TestCase):
    def test_parser_requires_exact_output_counts(self) -> None:
        parsed = _parse_summary(VALID_RESPONSE)
        self.assertEqual(len(parsed["summary"]), 5)
        self.assertEqual(len(parsed["key_points"]), 3)

        with self.assertRaises(OllamaResponseError):
            _parse_summary(VALID_RESPONSE.replace("5. Fifth summary line.\n", ""))

    def test_service_returns_structured_model_output(self) -> None:
        with (
            patch("news_summarizer.ollama_service._check_ollama"),
            patch("news_summarizer.ollama_service._chat", return_value=VALID_RESPONSE),
        ):
            result = summarize_article(
                "The report describes an event and provides the relevant facts. " * 4
            )

        self.assertEqual(len(result["summary"]), 5)
        self.assertEqual(len(result["key_points"]), 3)
        self.assertEqual(result["summary"][0], "First summary line.")

    def test_service_retries_model_output_with_wrong_item_counts(self) -> None:
        invalid_response = VALID_RESPONSE + "\n- Unrequested fourth point."
        with (
            patch("news_summarizer.ollama_service._check_ollama"),
            patch(
                "news_summarizer.ollama_service._chat",
                side_effect=[invalid_response, VALID_RESPONSE],
            ) as chat,
        ):
            result = summarize_article(
                "The report describes an event and provides the relevant facts. " * 4
            )

        self.assertEqual(chat.call_count, 2)
        self.assertEqual(len(result["key_points"]), 3)

    def test_long_article_summarizes_each_chunk_before_final_output(self) -> None:
        article = "The report includes relevant events, people, and figures. " * 250
        with (
            patch("news_summarizer.ollama_service._check_ollama"),
            patch(
                "news_summarizer.ollama_service._chat",
                side_effect=[
                    "Facts from section one.",
                    "Facts from section two.",
                    VALID_RESPONSE,
                ],
            ) as chat,
        ):
            result = summarize_article(article)

        self.assertEqual(chat.call_count, 3)
        final_prompt = chat.call_args_list[-1].args[0]
        self.assertIn("Facts from section one.", final_prompt)
        self.assertIn("Facts from section two.", final_prompt)
        self.assertEqual(len(result["summary"]), 5)


if __name__ == "__main__":
    unittest.main()
