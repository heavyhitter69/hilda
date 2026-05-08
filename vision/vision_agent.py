"""
vision/vision_agent.py — Send screenshots to a vision model for reasoning.

Default: GPT-4o Vision (requires OPENAI_API_KEY)
Fallback: Returns description "vision model offline" when no key is set.
"""
import base64
import io
from typing import Optional

from config.settings import settings
from core.logger import get_logger

log = get_logger(__name__)


def _pil_to_base64(image) -> str:
    """Convert a PIL Image to a base64 PNG string."""
    buf = io.BytesIO()
    image.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode("utf-8")


async def analyse_screen(image, question: str = "What is on screen?") -> str:
    """
    Send a screenshot to GPT-4o Vision and return the model's description.

    Parameters
    ----------
    image   : PIL Image — the screenshot to analyse
    question: str — the question to ask about the screen
    """
    if not settings.OPENAI_API_KEY or not settings.USE_VISION:
        log.warning("Vision disabled — no API key or USE_VISION=false.")
        return "Vision is currently offline. Please set OPENAI_API_KEY in .env."

    try:
        from openai import AsyncOpenAI
        client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        b64 = _pil_to_base64(image)

        resp = await client.chat.completions.create(
            model=settings.OPENAI_VISION_MODEL,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:image/png;base64,{b64}"},
                        },
                        {"type": "text", "text": question},
                    ],
                }
            ],
            max_tokens=512,
        )
        answer = resp.choices[0].message.content or ""
        log.info("Vision response: '%s'", answer[:80])
        return answer

    except Exception as e:
        log.error("Vision model error: %s", e)
        return f"I couldn't analyse the screen: {e}"


async def describe_screen() -> str:
    """
    Convenience function: capture the current screen and describe it.
    """
    from vision.screen_capture import capture_fullscreen
    image = capture_fullscreen()
    return await analyse_screen(image)
