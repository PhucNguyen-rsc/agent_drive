import time
from contextlib import asynccontextmanager

from mcp.server.fastmcp import FastMCP, Context
from auth import get_drive_service
from dotenv import load_dotenv
import os
from functools import wraps

from db import init_db

load_dotenv()

API_KEY = os.getenv("MCP_API_KEY")
PORT  = int(os.getenv("PORT", 8080))

@asynccontextmanager
async def lifespan(app): #only starting drive service once
    await init_db()
    service = await get_drive_service()  # once at startup
    yield {"drive": service} #store it

mcp = FastMCP("gdrive-server", host="0.0.0.0", port=PORT, lifespan=lifespan)

export_map = {
    "application/vnd.google-apps.document": "text/plain",
    "application/vnd.google-apps.spreadsheet": "text/csv",
    "application/vnd.google-apps.presentation": "text/plain",
}

def with_timing(func):
    @wraps(func)
    async def wrapper(*args, **kwargs):
        start = time.time()
        result = await func(*args, **kwargs)
        elapsed = time.time() - start
        print(f"{func.__name__} took {elapsed:.2f}s")
        return result
    return wrapper

@mcp.prompt()
async def find_and_summarize(topic: str) -> str:
    return f"Summarize the following topic: {topic} using the content of my Google Drive"

@mcp.resource("gdrive://recent-files")
async def recent_files() -> str:
    service = await get_drive_service()
    results = service.files().list(
        pageSize=10, orderBy="modifiedTime desc",
        fields="files(id, name, mimeType)"
    ).execute()
    files = results.get("files", [])
    if not files:
        return "No files found."
    return "\n".join(f"- {f['name']}" for f in files)

@mcp.resource("gdrive://folder/{folder_id}")
async def folder_contents( folder_id: str) -> str:
    service = await get_drive_service()

    contents = service.files().list(
        q=f"'{folder_id}' in parents",
        fields="files(id, name, mimeType)"
    ).execute()
    return "\n".join(f"- {f['name']}" for f in contents.get("files", []))


@mcp.tool()
@with_timing
async def search_files(query: str, ctx : Context, max_results: int = 10) -> str:
    await ctx.info(message=f"Searching for files with query '{query}'")
    service = ctx.request_context.lifespan_context["drive"]
    results = service.files().list(
        q=f"fullText contains '{query}' or name contains '{query}'",
        pageSize=max_results,
        fields="files(id, name, mimeType)"
    ).execute()
    files = results.get("files", [])
    if not files:
        return "No files found."
    return "\n".join(f"- {f['name']} (id: {f['id']})" for f in files)


@mcp.tool()
@with_timing
async def list_files(folder_name: str,  ctx : Context) -> str:
    await ctx.info(message=f"Listing files in folder '{folder_name}'")
    service = ctx.request_context.lifespan_context["drive"]
    results = service.files().list(
        q=f"name = '{folder_name}' and mimeType = 'application/vnd.google-apps.folder'",
        fields="files(id, name)"
    ).execute()
    folders = results.get("files", [])
    if not folders:
        return f"No folder found with name '{folder_name}'."

    contents = service.files().list(
        q=f"'{folders[0]['id']}' in parents",
        fields="files(id, name, mimeType)"
    ).execute()
    return "\n".join(f"- {f['name']}" for f in contents.get("files", []))


@mcp.tool()
@with_timing
async def read_file(file_name: str, ctx : Context) -> str:
    await ctx.info(message=f"Reading file '{file_name}'")
    service = ctx.request_context.lifespan_context["drive"]
    results = service.files().list(
        q=f"name = '{file_name}'", fields="files(id, mimeType, name)"
    ).execute()
    files = results.get("files", [])
    if not files:
        return f"No file found with name '{file_name}'."

    file = files[0]
    mime = file["mimeType"]
    if mime in export_map:
        content = service.files().export(
            fileId=file["id"], mimeType=export_map[mime]
        ).execute()
        return content.decode("utf-8")
    await ctx.warning(message=f"Cannot read file: {file['name']}")
    return f"Cannot read binary file: {file['name']}"

if __name__ == "__main__":
    mcp.run(transport="sse") # handles stdio transport automatically