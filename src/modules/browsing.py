import asyncio
import os
import sys
import time
from playwright.async_api import async_playwright
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from utils import log

class BrowserSession:
    def __init__(self):
        self.playwright = None
        self.browser = None
        self.page = None
        self.is_active = False

    async def start(self, headless=False):
        """Start a new browser session"""
        try:
            self.playwright = await async_playwright().start()
            self.browser = await self.playwright.chromium.launch(headless=headless)
            self.page = await self.browser.new_page()
            self.is_active = True
            log("Browser session started successfully", "INFO", "browsing.py")
        except Exception as e:
            log(f"Failed to start browser session: {e}", "ERROR", "browsing.py")
            await self.cleanup()

    async def cleanup(self):
        """Clean up browser resources"""
        if self.page:
            await self.page.close()
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()
        self.is_active = False

# Global browser session instance
_browser_session = BrowserSession()

async def run_async(action=None, url=None, selector=None, text=None, headless=True, **kwargs):
    """Main async function for browsing operations"""
    script_name = "browsing.py"
    
    if not action:
        log("Missing required argument: action", "ERROR", script_name)
        return
    
    try:
        # Convert headless string to boolean if needed
        if isinstance(headless, str):
            headless = headless.lower() in ('true', '1', 'yes')
        
        # Start browser session if not active
        if not _browser_session.is_active:
            await _browser_session.start(headless=headless)
        
        page = _browser_session.page
        
        if action == "navigate":
            if not url:
                log("Missing required argument: url for navigate action", "ERROR", script_name)
                return
            await page.goto(url)
            log(f"Navigated to: {url}", "INFO", script_name)
            
        elif action == "click":
            if not selector:
                log("Missing required argument: selector for click action", "ERROR", script_name)
                return
            await page.click(selector)
            log(f"Clicked element: {selector}", "INFO", script_name)
            
        elif action == "type":
            if not selector or not text:
                log("Missing required arguments: selector and text for type action", "ERROR", script_name)
                return
            await page.fill(selector, text)
            log(f"Typed '{text}' into element: {selector}", "INFO", script_name)
            
        elif action == "submit":
            if not selector:
                log("Missing required argument: selector for submit action", "ERROR", script_name)
                return
            await page.press(selector, "Enter")
            log(f"Submitted form with element: {selector}", "INFO", script_name)
            
        elif action == "wait":
            seconds = kwargs.get("seconds", 2)
            try:
                seconds = float(seconds)
            except ValueError:
                seconds = 2
            await page.wait_for_timeout(seconds * 1000)
            log(f"Waited for {seconds} seconds", "INFO", script_name)
            
        elif action == "screenshot":
            filename = kwargs.get("filename", f"browser_screenshot_{int(time.time())}.png")
            temp_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../temp'))
            os.makedirs(temp_dir, exist_ok=True)
            filename_only = os.path.basename(filename)
            full_path = os.path.join(temp_dir, filename_only)
            await page.screenshot(path=full_path)
            log(f"Screenshot saved to: {full_path}", "INFO", script_name)
            
        elif action == "get_text":
            if not selector:
                log("Missing required argument: selector for get_text action", "ERROR", script_name)
                return
            text_content = await page.text_content(selector)
            log(f"Text from {selector}: {text_content}", "INFO", script_name)
            return text_content
            
        elif action == "get_title":
            title = await page.title()
            log(f"Page title: {title}", "INFO", script_name)
            return title
            
        elif action == "close":
            await _browser_session.cleanup()
            log("Browser session closed", "INFO", script_name)
            
        else:
            log(f"Unknown action: {action}", "ERROR", script_name)
            
    except Exception as e:
        log(f"Error executing browsing action '{action}': {e}", "ERROR", script_name)

def run(action=None, url=None, selector=None, text=None, headless=True, **kwargs):
    """Synchronous wrapper for the async browsing function"""
    try:
        # Try to get the current event loop
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # If we're already in an async context, create a new task
            task = loop.create_task(run_async(action, url, selector, text, headless, **kwargs))
            return task
        else:
            # If no loop is running, run the async function
            return loop.run_until_complete(run_async(action, url, selector, text, headless, **kwargs))
    except RuntimeError:
        # If no event loop exists, create one
        return asyncio.run(run_async(action, url, selector, text, headless, **kwargs))
