import asyncio
import os
import sys
import json
import logging
from contextlib import AsyncExitStack
from typing import List, Dict, Any

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from langchain_mcp_adapters.tools import load_mcp_tools
from langgraph.prebuilt import create_react_agent
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_core.chat_history import BaseChatMessageHistory
from langchain_core.runnables.history import RunnableWithMessageHistory

from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("mcp_client")

# Load environment variables
load_dotenv()
logger.info("Environment variables loaded from .env file")

# Default system prompt
DEFAULT_SYSTEM_PROMPT = """You are a helpful AI assistant with access to various tools.
Your goal is to provide accurate, helpful responses to user queries by using these tools appropriately.
Always approach questions step-by-step and use the most relevant tools when needed.
If you're not sure about something, be honest about your limitations.
Always use this D://Python//2025//Personal_Ai_Agent//workspace as the root directory for all file operations.
"""

class InMemoryHistory(BaseChatMessageHistory):
    """Simple in-memory implementation of chat message history."""
    
    def __init__(self):
        self._messages = []
    
    def add_message(self, message):
        self._messages.append(message)
    
    def clear(self):
        self._messages = []

    @property
    def messages(self) -> List[Any]:
        return self._messages
        
    @messages.setter
    def messages(self, messages: List[Any]):
        self._messages = messages

class MessageHistoryStore:
    """Store for managing conversation histories."""
    
    def __init__(self):
        self.histories: Dict[str, InMemoryHistory] = {}
    
    def get_session_history(self, session_id: str):
        if session_id not in self.histories:
            self.histories[session_id] = InMemoryHistory()
        return self.histories[session_id]

class CustomEncoder(json.JSONEncoder):
    def default(self, o):
        if hasattr(o, "content"):
            return {"type": o.__class__.__name__, "content": o.content}
        return super().default(o)

def read_config_json():
    config_path = os.getenv("CONFIG_PATH")

    if not config_path:
        logger.warning("CONFIG_PATH not set")
        script_dir = os.path.dirname(os.path.abspath(__file__))
        config_path = os.path.join(script_dir, "config.json")
        logger.info(f"Using default config path: {config_path}")

    try:
        with open(config_path, "r") as f:
            config = json.load(f)
            logger.info(f"Successfully loaded config from {config_path}")
            return config
    except Exception as e:
        logger.error(f"Failed to read config file at '{config_path}': {e}")
        sys.exit(1)

def format_string_with_env(text):
    """
    Replace environment variable placeholders in a string.
    Example: "Hello, ${{NAME}}" -> "Hello, John"
    """
    if not isinstance(text, str):
        return text
        
    result = text
    # Find all instances of ${{ENV_VAR}}
    import re
    matches = re.findall(r'\$\{\{(\w+)\}\}', text)
    
    for env_var_name in matches:
        env_var_value = os.getenv(env_var_name, "")
        result = result.replace(f"${{{{{env_var_name}}}}}", env_var_value)
        if env_var_value:
            logger.info(f"Replaced ${{{{{env_var_name}}}}} with its environment value")
        else:
            logger.warning(f"Environment variable {env_var_name} not found")
            
    return result

def format_env(env):
    """
    Process environment variables in the configuration.
    Replaces placeholders like ${{ENV_VAR}} with actual environment variable values.
    """
    if not env:
        return {}
        
    processed_env = env.copy()
    for key, value in processed_env.items():
        if isinstance(value, str) and value.startswith("${{") and value.endswith("}}"):
            env_var_name = value[3:-2]
            env_var_value = os.getenv(env_var_name)
            if env_var_value is None:
                logger.warning(f"Environment variable {env_var_name} not found")
                processed_env[key] = ""  # Set empty string instead of None
            else:
                processed_env[key] = env_var_value
                logger.info(f"Environment variable {env_var_name} successfully mapped to {key}")
    
    logger.debug(f"Processed environment variables: {processed_env}")
    return processed_env

async def run_agent():
    config = read_config_json()
    mcp_servers = config.get("mcpServers", {})
    if not mcp_servers:
        logger.error("No MCP servers found in the configuration")
        return

    tools = []
    
    # Get system prompt from config or use default
    system_prompt = config.get("systemPrompt", DEFAULT_SYSTEM_PROMPT)
    # Replace any environment variables in the system prompt
    system_prompt = format_string_with_env(system_prompt)
    logger.info("System prompt loaded and processed")

    # Initialize LLM
    try:
        google_api_key = os.getenv("GOOGLE_API_KEY")
        if not google_api_key:
            logger.error("GOOGLE_API_KEY not set in environment")
            return
            
        llm = ChatGoogleGenerativeAI(
            model="gemini-2.0-flash",
            temperature=0,
            max_retries=2,
            google_api_key=google_api_key
        )
        logger.info("LLM initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize LLM: {e}")
        return

    async with AsyncExitStack() as stack:
        for server_name, server_info in mcp_servers.items():
            logger.info(f"Connecting to MCP Server: {server_name}")

            # Format the environment variables for this server
            env_vars = format_env(server_info.get("env", {}))
            
            # Debug what environment variables are being passed
            logger.info(f"Environment variables for {server_name}: {list(env_vars.keys())}")
            
            server_params = StdioServerParameters(
                command=server_info["command"],
                args=server_info["args"],
                env=env_vars
            )

            try:
                read, write = await stack.enter_async_context(stdio_client(server_params))
                session = await stack.enter_async_context(ClientSession(read, write))
                
                logger.info(f"Initializing session with {server_name}")
                await session.initialize()

                logger.info(f"Loading tools from {server_name}")
                server_tools = await load_mcp_tools(session)

                for tool in server_tools:
                    logger.info(f"Loaded tool: {tool.name}")
                    tools.append(tool)

                logger.info(f"{len(server_tools)} tools loaded from {server_name}.")
            except Exception as e:
                logger.error(f"Failed to connect to server {server_name}: {e}", exc_info=True)

        if not tools:
            logger.error("No tools loaded from any server. Exiting.")
            return

        # Create the base agent
        base_agent = create_react_agent(llm, tools)
        logger.info("Base agent created successfully with all tools")
        
        # Set up message history store
        message_history_store = MessageHistoryStore()
        session_id = "main"  # Default session ID
        
        # Wrap the agent with message history
        agent_with_memory = RunnableWithMessageHistory(
            base_agent,
            lambda session_id: message_history_store.get_session_history(session_id),
            input_messages_key="messages",
            history_messages_key="chat_history",
        )
        
        logger.info("Agent wrapped with memory functionality")

        print("\n🚀 MCP Client Ready! Type 'quit' to exit.")
        chat_history = []  # Initialize empty chat history
        
        while True:
            query = input("\nQuery: ").strip()
            if query.lower() == "quit":
                break
            
            if query.lower() == "clear memory":
                chat_history = []
                message_history_store.get_session_history(session_id).clear()
                print("Memory cleared!")
                continue

            try:
                logger.info(f"Processing query: {query}")
                
                # Prepare input with system prompt and history
                input_data = {
                    "messages": [
                        SystemMessage(content=system_prompt),
                        HumanMessage(content=query)
                    ],
                    "chat_history": chat_history
                }
                
                # Invoke agent with memory
                response = await agent_with_memory.ainvoke(
                    input_data, 
                    config={"configurable": {"session_id": session_id}}
                )
                
                # Extract the response content for display
                ai_response = response["messages"][-1].content if response.get("messages") else "No response"
                
                # Update our tracking of chat history
                chat_history.append(HumanMessage(content=query))
                chat_history.append(AIMessage(content=ai_response))
                
                print("\nResponse:")
                print(ai_response)
                
                # Optionally print full response details for debugging
                if os.getenv("DEBUG") == "true":
                    try:
                        formatted = json.dumps(response, indent=2, cls=CustomEncoder)
                        print("\nDebug - Full response:")
                        print(formatted)
                    except Exception as e:
                        logger.error(f"Failed to format response: {e}")
                        
            except Exception as e:
                logger.error(f"Error processing query: {e}", exc_info=True)
                print(f"Error: {e}")

if __name__ == "__main__":
    try:
        asyncio.run(run_agent())
    except KeyboardInterrupt:
        logger.info("Application terminated by user")
    except Exception as e:
        logger.error(f"Unhandled exception: {e}", exc_info=True)