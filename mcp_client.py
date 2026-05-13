import asyncio
import os
from agents import Agent, OpenAIChatCompletionsModel, Runner, set_default_openai_client, set_tracing_disabled

from agents.mcp import MCPServerStdio
from dotenv import load_dotenv
from openai import AsyncOpenAI


params = {"command": "npx", "args": ["-y", "chrome-devtools-mcp@latest"]}

async def main() -> None:
    async with MCPServerStdio(params=params, client_session_timeout_seconds=30) as server:
        mcp_tools = await server.list_tools()
    
    print("Tools:")
    if isinstance(mcp_tools, list):
        for tool in mcp_tools:
            name = getattr(tool, "name", None)
            description = getattr(tool, "description", "")
            if name:
                print(f"- {name}: {description}")
            else:
                print(f"- {tool}")
    else:
        print(mcp_tools)

if __name__ == "__main__":
    asyncio.run(main())