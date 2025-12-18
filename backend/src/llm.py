from google import genai
from google.genai import types
import os
from .config import GEMINI_API_KEY
import json
import base64

class GeminiClient:
    def __init__(self):
        if not GEMINI_API_KEY:
            print("Warning: GEMINI_API_KEY not set")
            self.client = None
        else:
            self.client = genai.Client(api_key=GEMINI_API_KEY)

    async def plan_task(self, prompt: str) -> list:
        if not self.client:
            return ["Error: No API Key"]
            
        sys_prompt = f"""
        You are a mobile automation planner.
        Break down the user's high-level goal into a sequence of granular, verifiable steps.
        Goal: {prompt}
        
        Return a JSON array of strings, where each string is a step.
        Example: ["Tap the email field", "Type 'user@test.com'", "Tap the password field", "Type '1234'", "Tap Login"]
        """
        
        try:
            response = self.client.models.generate_content(
                model='gemini-2.5-flash',
                contents=sys_prompt
            )
            text = response.text.strip()
            if "```json" in text:
                text = text.split("```json")[1].split("```")[0].strip()
            elif "```" in text:
                text = text.split("```")[1].split("```")[0].strip()
            return json.loads(text)
        except Exception as e:
            print(f"Planning Error: {e}")
            return [prompt]

    async def verify_step(self, screenshot_b64: str, current_task: str) -> dict:
        if not self.client:
            return {"status": "error", "reason": "No API Key"}

        prompt = f"""
        You are a mobile testing verifier.
        Current Task: {current_task}
        
        Analyze the screenshot. Is the Current Task ALREADY completed or is the state such that we can proceed to the next task?
        - If the task was "Type email" and you see the email in the box, return "completed".
        - If the task was "Tap Login" and you see the home screen (meaning login worked), return "completed".
        - If the task is NOT done, return "not_completed".
        
        Return JSON: {{ "status": "completed" | "not_completed", "reason": "..." }}
        """
        
        try:
            image_bytes = base64.b64decode(screenshot_b64)
            
            response = self.client.models.generate_content(
                model='gemini-2.5-flash',
                contents=[
                    prompt,
                    types.Part.from_bytes(data=image_bytes, mime_type="image/png")
                ]
            )
            text = response.text.strip()
            if "```json" in text:
                text = text.split("```json")[1].split("```")[0].strip()
            elif "```" in text:
                text = text.split("```")[1].split("```")[0].strip()
            return json.loads(text)
        except Exception as e:
            return {"status": "error", "reason": str(e)}

    async def get_action(self, screenshot_b64: str, goal: str, history: list):
        if not self.client:
            return {"action": "error", "reason": "No API Key"}
        
        prompt = f"""
        You are a mobile testing agent.
        The current active task is: {goal}
        History: {history}
        
        Analyze the screenshot. Generate the immediate physical action to perform to move towards completing the active task.
        
        Return a valid JSON object:
        {{
            "action": "tap" | "type" | "swipe" | "done" | "fail",
            "params": {{ "x": int, "y": int, "text": str, "start_x": int, "start_y": int, "end_x": int, "end_y": int }},
            "reason": "explanation"
        }}
        """
        
        try:
            image_bytes = base64.b64decode(screenshot_b64)
            
            response = self.client.models.generate_content(
                model='gemini-2.5-flash',
                contents=[
                    prompt,
                    types.Part.from_bytes(data=image_bytes, mime_type="image/png")
                ]
            )
            text = response.text.strip()
            if "```json" in text:
                text = text.split("```json")[1].split("```")[0].strip()
            elif "```" in text:
                text = text.split("```")[1].split("```")[0].strip()
            return json.loads(text)
        except Exception as e:
            return {"action": "fail", "reason": f"LLM Error: {str(e)}"}

    async def analyze_screen(self, screenshot_b64: str, current_task: str, history: list) -> dict:
        if not self.client:
            return {"action": "fail", "reason": "No API Key"}
        
        prompt = f"""
        You are a mobile automation agent.
        Goal Task: {current_task}
        Recent History: {history}
        
        Your job is to:
        1. Analyze the screenshot.
        2. Determine if the Goal Task is ALREADY completed.
        3. If NOT completed, determine the immediate physical action (tap/type/swipe) to perform.
        
        Return a JSON object:
        {{
            "status": "completed" | "in_progress" | "failed",
            "action": "tap" | "type" | "swipe" | "done" | "fail",
            "params": {{ "x": int, "y": int, "text": str, "start_x": int, "start_y": int, "end_x": int, "end_y": int }},
            "reason": "Clear explanation of what you see and why you chose this action."
        }}
        
        Rules:
        - If you see the effect of the previous action (e.g. keyboard opened), proceed.
        - If the task is "Type password" and the field is empty, tap it. If focused, type.
        - If the task is "Login" and you are on the home screen, action="done".
        """
        
        try:
            image_bytes = base64.b64decode(screenshot_b64)
            response = self.client.models.generate_content(
                model='gemini-2.5-flash',
                contents=[prompt, types.Part.from_bytes(data=image_bytes, mime_type="image/png")]
            )
            text = response.text.strip()
            if "```json" in text:
                text = text.split("```json")[1].split("```")[0].strip()
            elif "```" in text:
                text = text.split("```")[1].split("```")[0].strip()
            return json.loads(text)
        except Exception as e:
            return {"action": "fail", "reason": f"LLM Error: {str(e)}"}
    
    async def analyze_screen_with_hierarchy(
    self, 
    screenshot_b64: str, 
    page_source: str, 
    current_task: str, 
    history: list
) -> dict:
        if not self.client:
            return {"action": "fail", "reason": "No API Key"}
        
        # Truncate page_source if too long (token limits)
        truncated_xml = page_source[:8000] if len(page_source) > 8000 else page_source
        
        prompt = f"""
CRITICAL: You MUST extract selectors DIRECTLY from the XML provided below. Do NOT guess or make up resource-id values.

Current Task: {current_task}

UI Hierarchy XML:
{truncated_xml}

INSTRUCTIONS:
1. Search the XML for elements that match the task
2. Extract the EXACT resource-id, text, or content-desc from the XML
3. For "Enter phone number" task, look for EditText with hint/text containing "phone" or "mobile"
4. ALWAYS provide fallback coordinates from bounds="[x1,y1][x2,y2]" - calculate center point

VALID SELECTOR TYPES:
- "id" → Use resource-id value (e.g., "com.application.zomato:id/fw_mobile_edit_text")
- "text" → Use exact text value
- "xpath" → Use XPath expression

Return JSON:
{{
    "action": "click|type|swipe|done",
    "selector": {{"type": "id", "value": "EXACT_resource-id_from_XML"}},
    "text": "text to type",
    "coordinates": {{"x": 500, "y": 1500}},  // REQUIRED - calculate from bounds
    "reason": "Found element at bounds [x,y]"
}}

Example from XML: bounds="[385,1504][1017,1563]" → coordinates: {{"x": 701, "y": 1533}}
    """
        
        try:
            image_bytes = base64.b64decode(screenshot_b64)
            response = self.client.models.generate_content(
                model='gemini-2.5-flash',
                contents=[
                    prompt,
                    types.Part.from_bytes(data=image_bytes, mime_type="image/png")
                ]
            )
            
            text = response.text.strip()
            if "```json" in text:
                text = text.split("```json")[1].split("```")[0].strip()
            elif "```" in text:
                text = text.split("```")[1].split("```")[0].strip()
                
            return json.loads(text)
            
        except Exception as e:
            return {"action": "fail", "reason": f"Analysis error: {str(e)}"}

    async def interpret_chat(self, message: str, history: list, current_status: str) -> dict:
        if not self.client:
            return {"intent": "reply_to_user", "message": "Sorry, I am currently offline."}

        # Define native tools
        tools = [
            {
                "function_declarations": [
                    {
                        "name": "stop_agent",
                        "description": "Stop the current agent execution and cleanup resources. Use when the user wants to abort or stop."
                    },
                    {
                        "name": "restart_agent",
                        "description": "Restart the current agent task from the beginning. Use when the user says 'try again' or 'restart'."
                    },
                    {
                        "name": "update_goal",
                        "description": "Update the agent's goal/task and restart the execution with this new goal.",
                        "parameters": {
                            "type": "OBJECT",
                            "properties": {
                                "new_goal": {"type": "STRING", "description": "The updated task description from the user."}
                            },
                            "required": ["new_goal"]
                        }
                    },
                    {
                        "name": "reply_to_user",
                        "description": "Send a natural language response back to the user for general questions or chitchat.",
                        "parameters": {
                            "type": "OBJECT",
                            "properties": {
                                "message": {"type": "STRING", "description": "The response message to the user."}
                            },
                            "required": ["message"]
                        }
                    }
                ]
            }
        ]

        system_instruction = f"""
        You are an intelligent agent supervisor. 
        Analyze the user's message and the current context.
        Current Agent Status: {current_status}
        
        The user may want to stop the agent, restart it, change what it's doing, or just talk.
        Use the appropriate tool to respond. Do NOT provide text if a tool call is more appropriate.
        If you update the goal, ALWAYS use the update_goal tool.
        """

        try:
            # We use the new SDK format for tools
            config = types.GenerateContentConfig(
                tools=tools,
                system_instruction=system_instruction
            )
            
            response = self.client.models.generate_content(
                model='gemini-2.5-flash',
                contents=message,
                config=config
            )

            # Extract function call
            for part in response.candidates[0].content.parts:
                if part.function_call:
                    return {
                        "intent": part.function_call.name,
                        **part.function_call.args
                    }
            
            # Fallback to chat if no tool was called
            return {"intent": "reply_to_user", "message": response.text or "I'm not sure what you mean."}
            
        except Exception as e:
            return {"intent": "reply_to_user", "message": f"Intent recognition failed: {e}"}