import asyncio
from mcp.client.sse import sse_client
from mcp import StdioServerParameters, ClientSession
import logging
from mcp import types

async def main():
    async with sse_client("http://localhost:8080/sse") as (reader, writer):
        async with ClientSession(reader, writer) as session:
            await session.initialize()
            resources = await session.list_tools()
            print(resources)

            content = await session.call_tool(name="search_files", arguments={"query": "philosophy"})
            print(content)

if __name__ == "__main__":
    asyncio.run(main())