# News Article Summarizer

A local, AI-powered news briefing application. Enter a public article URL or paste article text to create an exactly five-line summary and exactly three key points using Ollama and Qwen 2.5 (3B). No API key or cloud AI service is used.

## Problem statement

News stories can be lengthy and time-consuming to read. This application extracts readable content from a web article, or accepts text directly, and presents its central facts in a compact format while retaining names, events, dates, and figures.

## Objectives

- Accept article content from a URL or pasted text.
- Extract article titles and readable text where available.
- Generate a concise five-line summary and three important key points.
- Run language-model inference locally through Ollama.
- Report access, configuration, and model-response errors instead of fabricating output.

## Features

- URL extraction using Requests, BeautifulSoup, and lxml.
- Separate URL and paste-text workflows in a Streamlit dashboard.
- Article cleaning, length validation, and ordered chunking for longer articles.
- Local Qwen 2.5 (3B) generation through Ollama's REST API.
- Exact-count output validation; malformed model responses are displayed as errors.
- Session-state result reuse and a Clear control.

## Technologies

- Python 3.13 (Python 3.10 or later recommended)
- Streamlit
- Ollama with `qwen2.5:3b`
- Requests, BeautifulSoup4, and lxml

## Project structure

```text
News Article Summarizer/
├── .venv/
├── .streamlit/
│   └── config.toml
├── src/
│   └── news_summarizer/
│       ├── __init__.py
│       ├── article_extractor.py
│       ├── text_processor.py
│       └── ollama_service.py
├── app.py
├── requirements.txt
├── README.md
└── .gitignore
```

## Setup on Windows PowerShell

Open PowerShell in the project folder, or change to it using the actual project path:

```powershell
cd "D:\MIT\Sem 7\Aman\News Article Summarizer"
```

Create the virtual environment once, then activate it:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

If PowerShell prevents activation due to its execution policy, run this for the current terminal session and activate again:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

Install the application dependencies into the active environment:

```powershell
python -m pip install -r requirements.txt
```

## Install and configure Ollama

Install Ollama for Windows from [ollama.com/download](https://ollama.com/download). Ollama must be running locally and listening at `http://localhost:11434`. The Ollama desktop application normally starts the local service. If it is not running, open a separate PowerShell window and start it with:

```powershell
ollama serve
```

In a terminal where the Ollama command is available, download the required model:

```powershell
ollama pull qwen2.5:3b
```

The application checks the local server and model before generating a summary. If the model is missing, it displays this command. No `.env` file, API key, or hosted model service is required.

## Run the application

From the project directory with `.venv` activated:

```powershell
streamlit run app.py
```

The app opens at [http://localhost:8501](http://localhost:8501). Keep Ollama running separately while using the app.

## Example usage

1. Open the **Article URL** tab and enter a public news article URL, then select **Summarize article**; or
2. Open **Paste Article**, paste at least 100 characters of article text, and select **Summarize article**.
3. Review the article title and original URL when available, the five summary lines, and the three key points.
4. Select **Clear** to remove the current inputs and result.

Some publishers block automated fetching, require subscriptions, or render article text only in JavaScript. For those pages, paste text you are authorized to use. URL fetching is restricted to public HTTP/HTTPS hosts.

## Testing

Run the offline unit tests from the project directory:

```powershell
python -m unittest discover -s tests -v
```

To check syntax and launch the app:

```powershell
python -m compileall app.py src tests
streamlit run app.py
```

Confirm that the interface opens at `http://localhost:8501`, that missing Ollama/model conditions show helpful errors, and that a valid article produces five lines and three points. Generation requires a running Ollama server and the downloaded model.

## Limitations

- Article extraction depends on publisher HTML and may not work for paywalled, blocked, JavaScript-only, or unusual pages.
- The local 3B model may omit nuance or make mistakes; verify important claims against the source article.
- Very large input is limited to 200,000 characters. Longer articles must be shortened explicitly; content is not silently truncated.
- Processing longer articles requires multiple local model calls and can take longer.
- Summarization quality and speed depend on the local computer's available memory and hardware.

## Future enhancements

- Add focused tests for extraction, chunk boundaries, and response validation.
- Add configurable local models and generation limits.
- Add article-language detection and multilingual summaries.
- Add optional local history and export to Markdown or PDF.
- Improve extraction for publisher-specific structured metadata.

## Conclusion

News Article Summarizer provides a straightforward, local-first workflow for converting article text into a five-line briefing and three key takeaways. Ollama keeps language-model processing on the user's machine, and the application reports failures rather than substituting fabricated content.
