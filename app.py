"""Streamlit interface for the local News Article Summarizer."""

from __future__ import annotations

import hashlib
import html
import sys
from pathlib import Path

import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parent
SOURCE_ROOT = PROJECT_ROOT / "src"
if str(SOURCE_ROOT) not in sys.path:
    sys.path.insert(0, str(SOURCE_ROOT))

from news_summarizer.article_extractor import ArticleExtractionError, extract_article
from news_summarizer.ollama_service import OllamaServiceError, summarize_article
from news_summarizer.text_processor import ArticleTextError

st.set_page_config(
    page_title="News Article Summarizer",
    page_icon="N",
    layout="wide",
)

st.markdown(
    """
    <style>
    .block-container {
        box-sizing: border-box;
        width: 100%;
        max-width: 1120px;
        padding: clamp(1.25rem, 3vw, 2rem) clamp(1rem, 3vw, 2rem);
    }
    .hero {
        border-bottom: 1px solid color-mix(in srgb, currentColor 16%, transparent);
        padding-bottom: 1.4rem;
        margin-bottom: 1.5rem;
    }
    .eyebrow {
        color: color-mix(
            in srgb,
            currentColor 78%,
            var(--primary-color, #2463a6) 22%
        );
        font-size: .76rem;
        font-weight: 700;
        letter-spacing: .12em;
        text-transform: uppercase;
    }
    .hero h1 {
        color: var(--text-color, inherit);
        font-size: clamp(2rem, 4vw, 2.65rem);
        line-height: 1.15;
        margin: .4rem 0 .65rem;
        overflow-wrap: anywhere;
    }
    .hero p {
        color: var(--text-color, inherit);
        font-size: 1.05rem;
        line-height: 1.65;
        margin: 0;
        max-width: 760px;
        opacity: .82;
    }
    [data-testid="stWidgetLabel"] {
        color: var(--text-color, inherit);
    }
    [data-testid="stTextInput"] input,
    [data-testid="stTextArea"] textarea {
        color: var(--text-color, inherit);
        border-color: color-mix(in srgb, currentColor 30%, transparent);
    }
    [data-testid="stTextInput"] input::placeholder,
    [data-testid="stTextArea"] textarea::placeholder {
        color: var(--text-color, inherit);
        opacity: .65;
    }
    [data-testid="stTextInput"] input:focus,
    [data-testid="stTextArea"] textarea:focus {
        border-color: var(--primary-color, #2463a6);
        box-shadow: 0 0 0 1px var(--primary-color, #2463a6);
    }
    div.stButton > button {
        border-radius: .6rem;
        font-weight: 600;
    }
    .source-line {
        color: var(--text-color, inherit);
        font-size: .9rem;
        overflow-wrap: anywhere;
        opacity: .82;
    }
    @media (max-width: 640px) {
        .hero { padding-bottom: 1.1rem; }
        .hero p { font-size: 1rem; }
        [data-testid="stHorizontalBlock"] { gap: .75rem; }
    }
    </style>
    """,
    unsafe_allow_html=True,
)


def _clear_session() -> None:
    for key in ("url_input", "article_input", "summary_result", "last_request"):
        st.session_state.pop(key, None)


def _request_fingerprint(source_type: str, source: str) -> str:
    return hashlib.sha256(f"{source_type}\0{source.strip()}".encode("utf-8")).hexdigest()


def _process(source_type: str, source: str) -> None:
    if not source.strip():
        st.error("Enter an article URL or paste article text before summarizing.")
        return

    fingerprint = _request_fingerprint(source_type, source)
    cached = st.session_state.get("last_request")
    if cached and cached["fingerprint"] == fingerprint:
        st.session_state["summary_result"] = cached["result"]
        st.info("Showing the existing result for this input.")
        return

    st.session_state.pop("summary_result", None)
    try:
        with st.spinner("Reading the article and generating your summary..."):
            if source_type == "url":
                title, article_text = extract_article(source)
                source_url = source.strip()
            else:
                title, article_text, source_url = None, source, None
            summary = summarize_article(article_text)
        result = {
            "title": title,
            "source_url": source_url,
            "summary": summary["summary"],
            "key_points": summary["key_points"],
        }
        st.session_state["summary_result"] = result
        st.session_state["last_request"] = {
            "fingerprint": fingerprint,
            "result": result,
        }
        st.success("Article summary generated.")
    except (ArticleExtractionError, ArticleTextError, OllamaServiceError) as exc:
        st.error(str(exc))


st.markdown(
    """
    <div class="hero">
      <div class="eyebrow">Local AI · News intelligence</div>
      <h1>News Article Summarizer</h1>
      <p>Turn a full news story into a clear five-line briefing and three essential takeaways.
      Article processing runs locally through Ollama.</p>
    </div>
    """,
    unsafe_allow_html=True,
)

if st.button("Clear", help="Clear the current article and generated result"):
    _clear_session()

url_tab, paste_tab = st.tabs(["Article URL", "Paste Article"])
with url_tab:
    url_value = st.text_input(
        "Article URL",
        placeholder="https://example.com/news/article",
        key="url_input",
    )
    if st.button("Summarize article", type="primary", key="summarize_url"):
        _process("url", url_value)

with paste_tab:
    article_value = st.text_area(
        "Article text",
        placeholder="Paste the complete news article here...",
        height=250,
        key="article_input",
    )
    if st.button("Summarize article", type="primary", key="summarize_text"):
        _process("text", article_value)

result = st.session_state.get("summary_result")
if result:
    st.divider()
    if result["title"]:
        st.subheader(result["title"])
    if result["source_url"]:
        st.markdown(
            f'<div class="source-line">Original source: '
            f'<a href="{html.escape(result["source_url"], quote=True)}" '
            f'target="_blank" rel="noopener noreferrer">'
            f'{html.escape(result["source_url"])}</a></div>',
            unsafe_allow_html=True,
        )
    st.markdown("")
    with st.container(border=True):
        st.markdown("#### Five-line summary")
        for index, line in enumerate(result["summary"], start=1):
            st.markdown(f"{index}. {html.escape(line)}")
    st.markdown("")
    with st.container(border=True):
        st.markdown("#### Key points")
        for point in result["key_points"]:
            st.markdown(f"- {html.escape(point)}")

st.divider()
st.caption("News Article Summarizer | Generative AI Mini Project | Roll No. 32")
