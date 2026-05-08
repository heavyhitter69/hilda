import asyncio, json
from langchain.agents import create_agent
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI

@tool
def dummy(): "dummy"

llm = ChatOpenAI(model="gpt-4o", api_key="sk-proj-dummy")
agent = create_agent(model=llm, tools=[dummy], system_prompt="Hello")

with open("out.json", "w") as f:
    json.dump({
        "input": agent.input_schema.schema(),
        "output": agent.output_schema.schema()
    }, f, indent=2)
