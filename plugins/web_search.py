"""
plugins/web_search.py — Web search and content reading for Hilda.

Uses DuckDuckGo (no API key required) for real-time search.
Fetches and extracts readable content from URLs.
"""
from __future__ import annotations

import re
from typing import Optional

from config.settings import settings
from core.logger import get_logger

log = get_logger(__name__)


def search_web(query: str, max_results: int = 5) -> list[dict[str, str]]:
    """
    Search the web using DuckDuckGo.

    Returns list of {"title": ..., "url": ..., "snippet": ...}
    """
    try:
        from duckduckgo_search import DDGS
        results = []
        with DDGS() as ddgs:
            for r in ddgs.text(query, max_results=max_results):
                results.append({
                    "title": r.get("title", ""),
                    "url": r.get("href", r.get("link", "")),
                    "snippet": r.get("body", r.get("snippet", "")),
                })
        log.info("Web search '%s': %d results", query[:40], len(results))
        return results
    except ImportError:
        log.warning("duckduckgo-search not installed — web search unavailable.")
        return []
    except Exception as e:
        log.error("Web search failed: %s", e)
        return []


def search_and_summarize(query: str) -> str:
    """
    Search the web and return an LLM-generated summary of the results.
    """
    results = search_web(query, max_results=5)
    if not results:
        return f"I couldn't find any results for '{query}'."

    # Build context from search results
    context_parts = []
    for i, r in enumerate(results, 1):
        context_parts.append(
            f"{i}. {r['title']}\n   {r['snippet']}\n   URL: {r['url']}"
        )
    context = "\n\n".join(context_parts)

    # Summarize with LLM
    try:
        import ollama
        response = ollama.chat(
            model=settings.OLLAMA_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a helpful assistant that summarizes web search results. "
                        "Provide a concise, accurate answer based on the search results. "
                        "If the results don't contain enough info, say so. "
                        "Cite sources when relevant."
                    ),
                },
                {
                    "role": "user",
                    "content": f"Query: {query}\n\nSearch Results:\n{context}\n\nProvide a concise answer:",
                },
            ],
            options={"temperature": 0.3, "num_predict": 300},
        )
        answer = response["message"]["content"].strip()
        log.info("Search summary generated for: %s", query[:40])
        return answer
    except Exception as e:
        log.error("Search summarization failed: %s", e)
        # Fallback: just return snippets
        lines = [f"Results for '{query}':"]
        for r in results[:3]:
            lines.append(f"• {r['title']}: {r['snippet'][:100]}")
        return "\n".join(lines)


def get_page_content(url: str, max_chars: int = 3000) -> str:
    """
    Fetch and extract the main text content from a URL.
    """
    if not url:
        return "No URL provided."

    if not url.startswith("http"):
        url = "https://" + url

    try:
        import trafilatura
        downloaded = trafilatura.fetch_url(url)
        if downloaded:
            text = trafilatura.extract(downloaded, include_comments=False, include_tables=True)
            if text:
                result = text[:max_chars]
                log.info("Extracted %d chars from %s", len(result), url[:60])
                return result
    except ImportError:
        log.debug("trafilatura not installed, falling back to basic fetch.")
    except Exception as e:
        log.debug("trafilatura failed: %s", e)

    # Fallback: basic urllib fetch
    try:
        import urllib.request
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            html = resp.read().decode("utf-8", errors="replace")
            # Basic HTML stripping
            text = re.sub(r"<script[^>]*>.*?</script>", "", html, flags=re.DOTALL | re.I)
            text = re.sub(r"<style[^>]*>.*?</style>", "", text, flags=re.DOTALL | re.I)
            text = re.sub(r"<[^>]+>", " ", text)
            text = re.sub(r"\s+", " ", text).strip()
            return text[:max_chars] if text else "Could not extract content."
    except Exception as e:
        log.error("Page fetch failed: %s", e)
        return f"Could not fetch content from {url}: {e}"


def summarize_url(url: str, question: Optional[str] = None) -> str:
    """
    Fetch a URL's content and summarize it with the LLM.
    Optionally answer a specific question about the content.
    """
    content = get_page_content(url, max_chars=4000)
    if content.startswith("Could not") or content.startswith("No URL"):
        return content

    prompt = f"Content from {url}:\n\n{content}\n\n"
    if question:
        prompt += f"Answer this question based on the content: {question}"
    else:
        prompt += "Provide a concise summary of this content."

    try:
        import ollama
        response = ollama.chat(
            model=settings.OLLAMA_MODEL,
            messages=[
                {"role": "system", "content": "Summarize web content accurately and concisely."},
                {"role": "user", "content": prompt},
            ],
            options={"temperature": 0.2, "num_predict": 400},
        )
        return response["message"]["content"].strip()
    except Exception as e:
        log.error("URL summarization failed: %s", e)
        return content[:500]  # Return raw content as fallback
