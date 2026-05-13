import asyncio
import os
from pathlib import Path
from agents import Agent, OpenAIChatCompletionsModel, Runner, set_default_openai_client, set_tracing_disabled

from agents.mcp import MCPServerStdio
from dotenv import load_dotenv
from openai import AsyncOpenAI

load_dotenv(override=True)
set_tracing_disabled(disabled=True)
TOOL_CALL_LOG_FILE = Path(__file__).resolve().parent / "tool_calls.log"


def print_recent_tool_calls() -> None:
    if TOOL_CALL_LOG_FILE.exists():
        lines = TOOL_CALL_LOG_FILE.read_text(encoding="utf-8").splitlines()
        recent_calls = lines[-5:]
        if recent_calls:
            print("Recent MCP tool calls:")
            for line in recent_calls:
                print(f"- {line}")
    else:
        print("No tool calls found.")

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

    instruction = """
    You are a helpful assistant for employee data.

    For HR records (name, email, role, salary, department): use the employee tools
    (e.g. list_employees, get_employee).

    For performance reviews, ratings, strengths, improvements, or goals: you MUST
    use the performance tools list_employee_performance or get_employee_performance
    (optionally after finding employee_id). Do not claim performance data is
    unavailable if those tools exist and return data.
    """
    async with MCPServerStdio(
        params=params, client_session_timeout_seconds=30
    ) as server:
        agent = Agent(
            name="Employee Assistant",
            instructions=instruction,
            model=agent_model,
            mcp_servers=[server]
        )

        await server.list_tools()

        # print("Tools:")
        # if isinstance(mcp_tools, list):
        #     for tool in mcp_tools:
        #         name = getattr(tool, "name", None)
        #         description = getattr(tool, "description", "")
        #         if name:
        #             print(f"- {name}: {description}")
        #         else:
        #             print(f"- {tool}")
        # else:
        #     print(mcp_tools)

        # request = "How many employees are there? Return only the number."
        # request = "List all employees"
        # request = "Give me the email of 'Jordan Kim'"
        # request = "who are you?"
        request = "give me the performance of 'Jordan Kim'"

        result = await Runner.run(
            agent, request
        )


        print_recent_tool_calls()
        print(f"Answer: {result.final_output}")

if __name__ == "__main__":
    asyncio.run(main())