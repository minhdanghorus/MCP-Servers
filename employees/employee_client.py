import asyncio
import os
from agents import Agent, OpenAIChatCompletionsModel, Runner, set_default_openai_client, set_tracing_disabled

from agents.mcp import MCPServerStdio
from dotenv import load_dotenv
from openai import AsyncOpenAI

load_dotenv(override=True)
set_tracing_disabled(disabled=True)


async def main() -> None:
    api_key = os.getenv("GREENNODE_API_KEY")
    base_url = os.getenv("GREENNODE_BASE_URL")
    model = os.getenv("GREENNODE_MODEL")
    if not model:
        raise RuntimeError(
            "GREENNODE_MODEL is not set. Please set it to a model available in your provider."
        )
    openai_client = None
    if api_key and base_url:
        openai_client = AsyncOpenAI(api_key=api_key, base_url=base_url)
        set_default_openai_client(openai_client)
    if openai_client is None:
        raise RuntimeError("GREENNODE_API_KEY and GREENNODE_BASE_URL are required.")
    agent_model = OpenAIChatCompletionsModel(model=model, openai_client=openai_client)

    params = {"command": "uv", "args": ["run", "-m", "employees.employee_server"]}
    async with MCPServerStdio(
        params=params, client_session_timeout_seconds=30
    ) as server:
        agent = Agent(
            name="Employee Assistant",
            instructions="Use available MCP tools to answer questions about employees.",
            model=agent_model,
            mcp_servers=[server]
        )

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

        result = await Runner.run(
            agent, "How many employees are there? Return only the number."
        )
        print(f"Answer: {result.final_output}")


if __name__ == "__main__":
    asyncio.run(main())