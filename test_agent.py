import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from core.agent import get_agent

async def test():
    r = await get_agent().think('open notepad')
    print("Agent Response:", r)

if __name__ == '__main__':
    asyncio.run(test())
