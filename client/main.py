import asyncio
import os
import sys
import json
from contextlib import AsyncExitStack

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from langchain_mcp_adapters.tools import load_mcp_tools
from langgraph.prebuilt import create_react_agent
from langchain_google_genai import ChatGoogleGenerativeAI

from dotenv import load_dotenv
load_dotenv()

class CustomEncoder(json.JSONEncoder):
    def default(self, o):
        if hasattr(o, "content"):
            return {"type": o.__class__.__name__, "content": o.content}
        return super().default(o)

def read_config_json():
    config_path = os.getenv("CONFIG_PATH")

    if not config_path:
        print(f"⚠️ CONFIG_PATH not set. Falling back to: {config_path}")
        script_dir = os.path.dirname(os.path.abspath(__file__))
        config_path = os.path.join(script_dir, "config.json")
        print(f"⚠️ Trying default config path: {config_path}")
        

    try:
        with open(config_path, "r") as f:
            return json.load(f)
    except Exception as e:
        print(f"❌ Failed to read config file at '{config_path}': {e}")
        sys.exit(1)

llm = ChatGoogleGenerativeAI(
    model="gemini-2.0-flash",
    temperature=0,
    max_retries=2,
    google_api_key=os.getenv("GOOGLE_API_KEY")
)

async def run_agent():
    config = read_config_json()
    mcp_servers = config.get("mcpServers", {})
    if not mcp_servers:
        print("❌ No MCP servers found in the configuration.")
        return

    tools = []

    async with AsyncExitStack() as stack:
        for server_name, server_info in mcp_servers.items():
            print(f"\n🔗 Connecting to MCP Server: {server_name}...")

            server_params = StdioServerParameters(
                command=server_info["command"],
                args=server_info["args"]
            )

            try:
                read, write = await stack.enter_async_context(stdio_client(server_params))
                session = await stack.enter_async_context(ClientSession(read, write))
                await session.initialize()

                server_tools = await load_mcp_tools(session)

                for tool in server_tools:
                    print(f"\n🔧 Loaded tool: {tool.name}")
                    tools.append(tool)

                print(f"\n✅ {len(server_tools)} tools loaded from {server_name}.")
            except Exception as e:
                print(f"❌ Failed to connect to server {server_name}: {e}")

        if not tools:
            print("❌ No tools loaded from any server. Exiting.")
            return

        agent = create_react_agent(llm, tools)

        print("\n🚀 MCP Client Ready! Type 'quit' to exit.")
        while True:
            query = input("\nQuery: ").strip()
            if query.lower() == "quit":
                break

            response = await agent.ainvoke({"messages": query})

            print("\nResponse:")
            try:
                formatted = json.dumps(response, indent=2, cls=CustomEncoder)
                print(formatted)
            except Exception:
                print(str(response))

if __name__ == "__main__":
    asyncio.run(run_agent())