"""
plugins/plugin_template.py — Example template for creating custom Hilda plugins.

To create your own plugin:
1. Copy this file into the `user_plugins/` directory.
2. Rename it (e.g., `my_plugin.py`).
3. Define your functions and wrap them in StructuredTool.from_function.
4. Hilda will automatically load it on startup!
"""
from langchain_core.tools import StructuredTool

# 1. Define your plugin metadata
PLUGIN_NAME = "example_plugin"
PLUGIN_DESCRIPTION = "An example plugin that demonstrates how to extend Hilda."


# 2. Write your custom Python functions
def my_custom_tool(name: str, count: int = 1) -> str:
    """
    A custom tool that says hello. The docstring is important—Hilda's AI reads it
    to know when and how to use this tool!
    """
    greetings = [f"Hello, {name}!"] * count
    return "\n".join(greetings)


def get_crypto_price(symbol: str) -> str:
    """
    Get the current price of a cryptocurrency.
    Example: get_crypto_price("BTC")
    """
    # Example logic (replace with real API call)
    prices = {"BTC": "65000", "ETH": "3500", "SOL": "150"}
    sym = symbol.upper()
    if sym in prices:
        return f"The current price of {sym} is ${prices[sym]}."
    return f"I don't know the price of {sym}."


# 3. Register your tools by adding them to PLUGIN_TOOLS
PLUGIN_TOOLS = [
    StructuredTool.from_function(
        my_custom_tool,
        name="say_hello",
        description="Say hello to a specific person multiple times."
    ),
    StructuredTool.from_function(
        get_crypto_price,
        name="get_crypto_price",
        description="Check the current price of a cryptocurrency symbol."
    ),
]
