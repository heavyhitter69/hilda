import asyncio
from core.planner import HildaPlanner

async def main():
    p = HildaPlanner()
    r1 = await p._direct_tool_mode("What's wrong? Open chat GPT.")
    print("Test 1:", r1)
    
    r2 = await p._direct_tool_mode("Open the Snapchat app.")
    print("Test 2:", r2)

asyncio.run(main())
