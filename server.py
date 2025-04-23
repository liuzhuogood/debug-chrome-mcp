from typing import Dict, List, Any
import asyncio

from mcp.server.fastmcp import FastMCP
from DrissionPage._base.chromium import Chromium
from debug_browser import DebugBrowser

mcp = FastMCP("Debug Chrome MCP")
browser = DebugBrowser()


async def init():
    global browser
    await browser.connect_to_existing_chrome()


@mcp.tool()
async def get_console_log() -> List[Dict[str, Any]]:
    """获取当前控制台的日志"""
    global browser
    logs = browser.get_console_logs()
    return logs


async def main():
    await init()
    await asyncio.sleep(8)
    await get_console_log()


if __name__ == '__main__':
    asyncio.run(main())
