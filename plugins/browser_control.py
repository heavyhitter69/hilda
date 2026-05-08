"""
plugins/browser_control.py — Browser automation.

Prefer Playwright when installed (full automation). In bundled installs Playwright
may be omitted; fall back to the system default browser for navigate/search flows.

open_url_default_browser — instant open via OS default browser (fast path).
"""
import asyncio
import urllib.parse
import webbrowser

from core.logger import get_logger

log = get_logger(__name__)

try:
    import playwright  # noqa: F401

    HAS_PLAYWRIGHT = True
except ImportError:
    HAS_PLAYWRIGHT = False


def open_url_default_browser(url: str) -> str:
    """Open a URL in the user's default browser (no Playwright startup cost)."""
    url = (url or "").strip()
    if not url:
        return "No URL provided."
    if not url.startswith("http"):
        url = "https://" + url
    webbrowser.open(url)
    log.info("Default browser open: %s", url)
    return f"Opened {url} in your default browser."


_playwright = None
_browser = None
_page = None


async def _get_page():
    """Return a singleton Playwright page, launching browser if needed."""
    global _playwright, _browser, _page
    if not HAS_PLAYWRIGHT:
        raise RuntimeError("Playwright is not bundled in this build.")
    if _page is None or _page.is_closed():
        from playwright.async_api import async_playwright

        _playwright = await async_playwright().__aenter__()
        _browser = await _playwright.chromium.launch(headless=False)
        _page = await _browser.new_page()
        log.info("Browser launched.")
    return _page


async def open_url(url: str) -> str:
    """Navigate to a URL."""
    if not url.startswith("http"):
        url = "https://" + url
    if not HAS_PLAYWRIGHT:
        return open_url_default_browser(url)
    page = await _get_page()
    await page.goto(url, wait_until="domcontentloaded", timeout=30000)
    title = await page.title()
    log.info("Navigated to: %s (title: %s)", url, title)
    return f"Opened {url}."


async def search_youtube(query: str) -> str:
    """Open YouTube and search for the given query."""
    encoded = urllib.parse.quote(query)
    yt = f"https://www.youtube.com/results?search_query={encoded}"
    if not HAS_PLAYWRIGHT:
        return open_url_default_browser(yt)
    page = await _get_page()
    await page.goto(yt, wait_until="domcontentloaded", timeout=30000)
    log.info("YouTube search: %s", query)
    return f"Searched YouTube for '{query}'."


async def click_element(selector: str) -> str:
    if not HAS_PLAYWRIGHT:
        return "Browser automation (Playwright) is not available in this build."
    page = await _get_page()
    try:
        await page.click(selector, timeout=5000)
        return f"Clicked '{selector}'."
    except Exception as e:
        return f"Could not click '{selector}': {e}"


async def fill_form(selector: str, value: str) -> str:
    if not HAS_PLAYWRIGHT:
        return "Browser automation (Playwright) is not available in this build."
    page = await _get_page()
    try:
        await page.fill(selector, value)
        return f"Filled '{selector}' with '{value}'."
    except Exception as e:
        return f"Could not fill '{selector}': {e}"


async def get_page_text() -> str:
    if not HAS_PLAYWRIGHT:
        return ""
    page = await _get_page()
    text = await page.inner_text("body")
    return text[:2000]


async def close_browser() -> None:
    global _browser, _playwright, _page
    if not HAS_PLAYWRIGHT:
        return
    if _browser:
        await _browser.close()
    if _playwright:
        await _playwright.__aexit__(None, None, None)
    _browser = _playwright = _page = None
    log.info("Browser closed.")


def _run(coro):
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            import concurrent.futures

            with concurrent.futures.ThreadPoolExecutor() as pool:
                future = pool.submit(asyncio.run, coro)
                return future.result()
        else:
            return loop.run_until_complete(coro)
    except RuntimeError:
        return asyncio.run(coro)


def open_url_sync(url: str) -> str:
    return _run(open_url(url))


def search_youtube_sync(query: str) -> str:
    return _run(search_youtube(query))
