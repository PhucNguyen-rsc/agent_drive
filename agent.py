import asyncio
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from mcp import ClientSession, StdioServerParameters
from mcp.client.sse import sse_client
from langchain_mcp_adapters.tools import load_mcp_tools

from langgraph.prebuilt import create_react_agent

load_dotenv()

async def main():
    async with sse_client("http://localhost:8080/sse") as (reader, writer):
        async with ClientSession(reader, writer) as session:
            await session.initialize()
            model = ChatOpenAI(model="gpt-4o")
            tools = await load_mcp_tools(session=session)
            agent = create_react_agent(model, tools)
            result = await agent.ainvoke({"messages": "Find any files related to philosophy and display their names here."})
            print(result["messages"][-1].content)

if __name__ == "__main__":
    asyncio.run(main())