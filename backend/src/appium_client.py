from appium import webdriver
from appium.options.android import UiAutomator2Options
from typing import Dict, Any
import base64
from .config import APPIUM_SERVER_URL

class AppiumDriver:
    def __init__(self):
        self.driver = None

    def start_session(self, apk_path: str):
        options = UiAutomator2Options()
        options.app = apk_path
        options.platform_name = "Android"
        options.automation_name = "UiAutomator2"
        options.no_reset = False
        options.auto_grant_permissions = True
        
        print(f"Connecting to Appium at {APPIUM_SERVER_URL} with app {apk_path}")
        self.driver = webdriver.Remote(APPIUM_SERVER_URL, options=options)

    def get_screenshot(self) -> str:
        if not self.driver:
            raise RuntimeError("Driver not initialized")
        return self.driver.get_screenshot_as_base64()

    def tap(self, x: int, y: int):
        if not self.driver:
             raise RuntimeError("Driver not initialized")
        self.driver.tap([(x, y)])
        
    def type_text(self, text: str):
        if not self.driver:
             raise RuntimeError("Driver not initialized")
        # Try to find active element, or finding specific element might be needed?
        # For agentic usage, we often type into the focused element or click first then type.
        try:
            self.driver.switch_to.active_element.send_keys(text)
        except Exception as e:
            print(f"Error typing text: {e}")

    def swipe(self, start_x, start_y, end_x, end_y):
        if not self.driver:
             raise RuntimeError("Driver not initialized")
        self.driver.swipe(start_x, start_y, end_x, end_y)

    def quit(self):
        if self.driver:
            self.driver.quit()
