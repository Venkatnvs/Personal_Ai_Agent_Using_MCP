import math
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("Calculator")

@mcp.tool()
def add(a: int, b: int, **kwargs) -> int:
    """Add two numbers"""
    return a + b

@mcp.tool()
def subtract(a: int, b: int, **kwargs) -> int:
    """Subtract two numbers"""
    return a - b

@mcp.tool()
def multiply(a: int, b: int, **kwargs) -> int:
    """Multiply two numbers"""
    return a * b

@mcp.tool()
def divide(a: int, b: int, **kwargs) -> float:
    """Divide two numbers"""
    return a / b

@mcp.tool()
def power(a: int, b: int, **kwargs) -> int:
    """Raise a number to the power of another number"""
    return a ** b

if __name__ == "__main__":
    mcp.run(transport='stdio')