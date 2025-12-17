import google.generativeai as genai
import os
from .config import GEMINI_API_KEY
import json

class GeminiClient:
    def __init__(self):
        if not GEMINI_API_KEY:
            print("Warning: GEMINI_API_KEY not set")
            self.model = None
        else:
            genai.configure(api_key=GEMINI_API_KEY)
            self.model = genai.GenerativeModel('gemini-2.5-flash')

    async def plan_task(self, prompt: str) -> list:
        if not self.model:
            return ["Error: No API Key"]
            
        sys_prompt = f"""
        You are a mobile automation planner.
        Break down the user's high-level goal into a sequence of granular, verifiable steps.
        Goal: {prompt}
        
        Return a JSON array of strings, where each string is a step.
        Example: ["Tap the email field", "Type 'user@test.com'", "Tap the password field", "Type '1234'", "Tap Login"]
        """
        
        try:
            response = self.model.generate_content(sys_prompt)
            text = response.text
             # Basic cleanup
            if "```json" in text:
                text = text.split("```json")[1].split("```")[0]
            elif "```" in text:
                text = text.split("```")[1].split("```")[0]
            return json.loads(text)
        except Exception as e:
            print(f"Planning Error: {e}")
            return [prompt] # Fallback to single step

    async def verify_step(self, screenshot_b64: str, current_task: str) -> dict:
        if not self.model:
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
            image_part = {"mime_type": "image/png", "data": screenshot_b64}
            response = self.model.generate_content([prompt, image_part])
            text = response.text
            if "```json" in text:
                text = text.split("```json")[1].split("```")[0]
            elif "```" in text:
                text = text.split("```")[1].split("```")[0]
            return json.loads(text)
        except Exception as e:
            return {"status": "error", "reason": str(e)}

    async def get_action(self, screenshot_b64: str, goal: str, history: list):
        if not self.model:
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
            image_part = {"mime_type": "image/png", "data": screenshot_b64}
            response = self.model.generate_content([prompt, image_part])
            text = response.text
            if "```json" in text:
                text = text.split("```json")[1].split("```")[0]
            elif "```" in text:
                text = text.split("```")[1].split("```")[0]
            return json.loads(text)
        except Exception as e:
            return {"action": "fail", "reason": f"LLM Error: {str(e)}"}
