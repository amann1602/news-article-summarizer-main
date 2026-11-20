"""Fetch and extract readable article content from a web page."""

from __future__ import annotations

import ipaddress
import socket
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup


class ArticleExtractionError(Exception):
    """Raised when an article cannot be safely fetched or extracted."""


_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)
_REQUEST_TIMEOUT = (8, 20)
_MIN_ARTICLE_LENGTH = 100
_UNWANTED_TAGS = (
    "script",
    "style",
    "noscript",
    "svg",
    "iframe",
    "nav",
    "footer",
    "header",
    "aside",
    "form",
    "button",
)
_UNWANTED_MARKERS = (
    "advert",
    "cookie",
    "menu",
    "nav",
    "newsletter",
    "promo",
    "related",
    "share",
    "social",
    "subscribe",
)


def _validate_public_http_url(url: str) -> None:
    parsed = urlparse(url.strip())
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise ArticleExtractionError("Enter a valid article URL beginning with http:// or https://.")
    if parsed.username or parsed.password:
        raise ArticleExtractionError("URLs containing embedded credentials are not supported.")

    hostname = parsed.hostname.rstrip(".").lower()
    if hostname == "localhost" or hostname.endswith(".localhost"):
        raise ArticleExtractionError("Local and private network URLs cannot be fetched.")

    try:
        addresses = socket.getaddrinfo(hostname, None, type=socket.SOCK_STREAM)
    except socket.gaierror:
        raise ArticleExtractionError("The URL's host could not be found.") from None

    for address in addresses:
        ip = ipaddress.ip_address(address[4][0])
        if not ip.is_global:
            raise ArticleExtractionError("Local and private network URLs cannot be fetched.")


def _remove_unwanted_elements(soup: BeautifulSoup) -> None:
    for element in reversed(soup.find_all(_UNWANTED_TAGS)):
        element.decompose()

    for element in reversed(soup.find_all(True)):
        marker = " ".join(
            [str(element.get("id", "")), " ".join(element.get("class", []))]
        ).lower()
        if any(unwanted in marker for unwanted in _UNWANTED_MARKERS):
            element.decompose()


def _text_from_container(container: BeautifulSoup) -> str:
    paragraphs = []
    seen = set()
    for paragraph in container.find_all(["p", "h2", "h3", "blockquote"]):
        text = " ".join(paragraph.get_text(" ", strip=True).split())
        if text and text not in seen:
            paragraphs.append(text)
            seen.add(text)
    if paragraphs:
        return "\n\n".join(paragraphs)
    return " ".join(container.get_text(" ", strip=True).split())


def extract_article(url: str) -> tuple[str | None, str]:
    """Return the page title and article text, without fabricating missing content."""
    if not isinstance(url, str) or not url.strip():
        raise ArticleExtractionError("Enter an article URL.")

    url = url.strip()
    _validate_public_http_url(url)

    try:
        response = requests.get(
            url,
            headers={"User-Agent": _USER_AGENT, "Accept": "text/html,application/xhtml+xml"},
            timeout=_REQUEST_TIMEOUT,
            allow_redirects=True,
        )
        response.raise_for_status()
    except requests.Timeout:
        raise ArticleExtractionError("The website took too long to respond. Try again later.") from None
    except requests.RequestException as exc:
        raise ArticleExtractionError(f"Could not access this website: {exc}") from None

    content_type = response.headers.get("Content-Type", "").lower()
    if content_type and "html" not in content_type:
        raise ArticleExtractionError("The URL did not return an HTML page.")

    soup = BeautifulSoup(response.content, "lxml")
    title_element = (
        soup.find("meta", property="og:title")
        or soup.find("meta", attrs={"name": "twitter:title"})
    )
    title = (
        title_element.get("content", "").strip()
        if title_element
        else (soup.title.get_text(" ", strip=True) if soup.title else "")
    )
    if not title:
        heading = soup.find("h1")
        title = heading.get_text(" ", strip=True) if heading else ""

    _remove_unwanted_elements(soup)
    candidates = soup.find_all(["article", "main"])
    candidates.sort(key=lambda item: len(item.get_text(" ", strip=True)), reverse=True)

    article_text = ""
    for candidate in candidates:
        candidate_text = _text_from_container(candidate)
        if len(candidate_text) > len(article_text):
            article_text = candidate_text
    if len(article_text) < _MIN_ARTICLE_LENGTH:
        body = soup.body or soup
        article_text = _text_from_container(body)

    if len(article_text) < _MIN_ARTICLE_LENGTH:
        raise ArticleExtractionError(
            "The page did not contain enough readable article text. "
            "Some sites block automated access; you can paste the article text instead."
        )

    return title or None, article_text
