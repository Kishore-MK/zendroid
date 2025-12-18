from appium import webdriver
from appium.options.android import UiAutomator2Options
from appium.webdriver.common.appiumby import AppiumBy
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.actions import interaction
from selenium.webdriver.common.actions.action_builder import ActionBuilder
from selenium.webdriver.common.actions.pointer_input import PointerInput
from typing import Dict, Any, Tuple, Optional
import base64
import io
from PIL import Image
from .config import APPIUM_SERVER_URL

class ElementSelector:
    """Represents a UI element selector"""
    def __init__(self, selector_type: str, value: str):
        self.selector_type = selector_type
        self.value = value
        
    def to_appium_by(self) -> Tuple[str, str]:
        """Convert to Appium locator strategy"""
        mapping = {
            "id": AppiumBy.ID,
            "xpath": AppiumBy.XPATH,
            "text": AppiumBy.ANDROID_UIAUTOMATOR,
            "accessibility_id": AppiumBy.ACCESSIBILITY_ID,
            "class": AppiumBy.CLASS_NAME
        }
        
        by = mapping.get(self.selector_type, AppiumBy.XPATH)
        
        # For text-based selectors, wrap in UiSelector
        if self.selector_type == "text":
            value = f'new UiSelector().text("{self.value}")'
        else:
            value = self.value
            
        return by, value

class AppiumDriver:
    """Enhanced Appium driver with element-based interactions"""
    
    ELEMENT_TIMEOUT = 10  # seconds
    
    def __init__(self):
        self.driver = None

    def start_session(self, apk_path: str) -> None:
        """Initialize Appium session"""
        options = UiAutomator2Options()
        options.app = apk_path
        options.platform_name = "Android"
        options.automation_name = "UiAutomator2"
        options.no_reset = False
        options.auto_grant_permissions = True
        options.app_wait_activity = "*"  
        options.app_wait_duration = 30000 
        
        print(f"Connecting to Appium at {APPIUM_SERVER_URL}")
        self.driver = webdriver.Remote(APPIUM_SERVER_URL, options=options)

    def get_screenshot(self) -> str:
        """Capture screenshot as base64"""
        self._ensure_driver()
        return self.driver.get_screenshot_as_base64()

    def get_page_source(self) -> str:
        """Get UI hierarchy XML"""
        self._ensure_driver()
        return self.driver.page_source
    
    def get_ui_context(self) -> Dict[str, str]:
        """Get both screenshot and page source for analysis"""
        return {
            "screenshot": self.get_screenshot(),
            "page_source": self.get_page_source()
        }

    def click_element(self, selector: ElementSelector) -> bool:
        """
        Click element using selector (primary method)
        Returns True if successful, False otherwise
        """
        try:
            element = self._find_element(selector)
            if element:
                element.click()
                print(f"Clicked element: {selector.selector_type}={selector.value}")
                return True
        except Exception as e:
            print(f"Failed to click element: {e}")
        return False

    def type_into_element(self, selector: ElementSelector, text: str) -> bool:
        """
        Type text into element using selector
        Returns True if successful
        """
        try:
            element = self._find_element(selector)
            if element:
                element.clear()
                element.send_keys(text)
                print(f"Typed '{text}' into element: {selector.selector_type}={selector.value}")
                return True
        except Exception as e:
            print(f"Failed to type into element: {e}")
        return False

    def element_exists(self, selector: ElementSelector) -> bool:
        """Check if element exists without throwing exception"""
        try:
            element = self._find_element(selector, timeout=2)
            return element is not None
        except:
            return False

    def get_element_text(self, selector: ElementSelector) -> Optional[str]:
        """Get text content of element"""
        try:
            element = self._find_element(selector)
            return element.text if element else None
        except:
            return None

    def _find_element(self, selector: ElementSelector, timeout: int = None):
        """
        Find element with explicit wait
        Returns element or None
        """
        self._ensure_driver()
        timeout = timeout or self.ELEMENT_TIMEOUT
        
        by, value = selector.to_appium_by()
        
        try:
            wait = WebDriverWait(self.driver, timeout)
            element = wait.until(EC.presence_of_element_located((by, value)))
            return element
        except (NoSuchElementException, TimeoutException) as e:
            print(f"Element not found: {selector.selector_type}={selector.value}")
            return None

    # Fallback coordinate-based methods
    def tap_coordinates(self, x: int, y: int) -> None:
        """Fallback: Tap at specific coordinates (use only when element-based fails)"""
        print(f"⚠️ Fallback: Coordinate tap at ({x}, {y})")
        self._ensure_driver()
        
        scale_x, scale_y = self._get_scale_ratio()
        logic_x = int(x * scale_x)
        logic_y = int(y * scale_y)
        
        touch_input = PointerInput(interaction.POINTER_TOUCH, "touch")
        actions = ActionBuilder(self.driver, mouse=touch_input)
        actions.pointer_action.move_to_location(logic_x, logic_y)
        actions.pointer_action.pointer_down()
        actions.pointer_action.pause(0.1)
        actions.pointer_action.pointer_up()
        actions.perform()

    def swipe(self, start_x: int, start_y: int, end_x: int, end_y: int, duration: int = 500) -> None:
        """Perform swipe gesture"""
        self._ensure_driver()
        
        scale_x, scale_y = self._get_scale_ratio()
        s_x = int(start_x * scale_x)
        s_y = int(start_y * scale_y)
        e_x = int(end_x * scale_x)
        e_y = int(end_y * scale_y)
        
        touch_input = PointerInput(interaction.POINTER_TOUCH, "touch")
        actions = ActionBuilder(self.driver, mouse=touch_input)
        actions.pointer_action.move_to_location(s_x, s_y)
        actions.pointer_action.pointer_down()
        actions.pointer_action.pause(duration / 1000)
        actions.pointer_action.move_to_location(e_x, e_y)
        actions.pointer_action.pointer_up()
        actions.perform()
        
        print(f"Swiped from ({start_x},{start_y}) to ({end_x},{end_y})")

    def _get_scale_ratio(self) -> Tuple[float, float]:
        """Calculate scale ratio between physical screenshot and logical window"""
        if not self.driver:
            return 1.0, 1.0
            
        window = self.driver.get_window_size()
        win_w, win_h = window['width'], window['height']
        
        screenshot_b64 = self.driver.get_screenshot_as_base64()
        image = Image.open(io.BytesIO(base64.b64decode(screenshot_b64)))
        img_w, img_h = image.size
        
        scale_x = win_w / img_w
        scale_y = win_h / img_h
        
        return scale_x, scale_y

    def _ensure_driver(self) -> None:
        """Ensure driver is initialized"""
        if not self.driver:
            raise RuntimeError("Driver not initialized. Call start_session() first.")

    def quit(self) -> None:
        """Close driver session"""
        if self.driver:
            try:
                self.driver.quit()
                print("Driver session closed")
            except Exception as e:
                print(f"Error closing driver: {e}")
            finally:
                self.driver = None