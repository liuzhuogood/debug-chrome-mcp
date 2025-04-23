import dataclasses
from playwright.async_api import async_playwright
import requests
from playwright.async_api._generated import Playwright as AsyncPlaywright, Browser, BrowserContext, Page
from typing import List, Dict, Any


@dataclasses.dataclass
class DebugBrowseMgr:
    playwright: AsyncPlaywright
    browser: Browser
    context: BrowserContext
    page: Page
    console_logs: List[Dict[str, Any]]


class DebugBrowser:
    def __init__(self):
        self.dbm: DebugBrowseMgr | None = None

    async def connect_to_existing_chrome(self, port=9222):
        """
        连接到已通过 remote-debugging 启动的 Chromium 浏览器
        返回 (playwright, browser, context, page)
        记得使用后手动关闭 browser.disconnect()
        """
        ws_url = None
        try:
            # 首先获取所有页面信息
            pages_resp = requests.get(f"http://localhost:{port}/json/list", timeout=2)
            pages_info = pages_resp.json()
            
            # 获取调试器WebSocket URL
            resp = requests.get(f"http://localhost:{port}/json/version", timeout=2)
            ws_url = resp.json().get("webSocketDebuggerUrl")
            if not ws_url:
                raise RuntimeError("无法获取 WebSocket 调试地址")
        except Exception as e:
            raise RuntimeError(f"连接失败，请确认浏览器是否已启动并开启调试端口：{e}")

        playwright = await async_playwright().start()
        browser = await playwright.chromium.connect_over_cdp(ws_url)
        
        # 获取已存在的context
        context = browser.contexts[0]
        
        # 获取已存在的页面
        pages = context.pages
        page = pages[0] if pages else await context.new_page()

        self.dbm = DebugBrowseMgr(playwright, browser, context, page, [])
        await self.start_console_loger()

    async def start_console_loger(self):
        """
        开始监听浏览器的 console 输出
        会收集所有类型的日志，包括 error、warning、info 等
        """
        def handle_console(msg):
            log_entry = {
                'type': msg.type,
                'text': msg.text,
                'args': [arg.json_value() for arg in msg.args],
                'location': {
                    'url': msg.location.get('url'),
                    'lineNumber': msg.location.get('lineNumber'),
                    'columnNumber': msg.location.get('columnNumber')
                }
            }
            self.dbm.console_logs.append(log_entry)
            print(f"[{msg.type.upper()}] {msg.text}")

        self.dbm.page.on("console", handle_console)

    def get_console_logs(self, log_type: str = None) -> List[Dict[str, Any]]:
        """
        获取收集到的 console 日志
        
        Args:
            log_type: 可选参数，指定要获取的日志类型（'error', 'warning', 'info', 'log' 等）
                     如果为 None，则返回所有日志
        
        Returns:
            List[Dict[str, Any]]: 日志列表，每个日志包含 type、text、args 和 location 信息
        """
        if log_type:
            return [log for log in self.dbm.console_logs if log['type'] == log_type]
        return self.dbm.console_logs

    def clear_console_logs(self):
        """清空已收集的日志"""
        self.dbm.console_logs = []
