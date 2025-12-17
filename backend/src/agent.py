from langgraph.graph import StateGraph, END
from typing import TypedDict, List, Dict, Any
from .appium_client import AppiumDriver
from .llm import GeminiClient
import asyncio

# Global instances (for MVP simplicity)
driver = AppiumDriver()
llm = GeminiClient()

class AgentState(TypedDict):
    test_prompt: str
    apk_path: str
    history: List[Dict]
    screenshot: str # base64
    status: str
    step_count: int
    task_list: List[str]
    current_task_index: int

def setup(state: AgentState):
    print(f"Starting test for: {state['apk_path']}")
    try:
        driver.start_session(state["apk_path"])
        return {
            "history": [{"role": "system", "content": "Session started"}], 
            "step_count": 0, 
            "status": "planning",
            "current_task_index": 0
        }
    except Exception as e:
        print(f"Setup failed: {e}")
        return {"status": "failed", "history": [{"role": "system", "content": f"Setup failed: {str(e)} "}]}

async def plan_node(state: AgentState):
    print("Generating Plan...")
    try:
        tasks = await llm.plan_task(state["test_prompt"])
        print(f"Plan Generated: {tasks}")
        return {
            "task_list": tasks,
            "status": "running",
            "history": state["history"] + [{"role": "model", "content": f"Plan: {tasks}"}]
        }
    except Exception as e:
         return {"status": "failed", "history": state["history"] + [{"role": "system", "content": f"Planning failed: {e}"}]}

async def step_node(state: AgentState):
    if state.get("status") != "running":
        return {}
    
    tasks = state.get("task_list", [])
    idx = state.get("current_task_index", 0)
    
    if idx >= len(tasks):
        return {"status": "passed", "history": state["history"] + [{"role": "system", "content": "All tasks completed"}]}

    current_task = tasks[idx]
    print(f"Executing Task [{idx+1}/{len(tasks)}]: {current_task} (Global Step {state.get('step_count')})")
    
    # 1. Get Screenshot
    try:
        screenshot = driver.get_screenshot()
    except Exception as e:
        return {"status": "failed", "history": state["history"] + [{"role": "system", "content": f"Screenshot failed: {e}"}]}
    
    # 2. Verify Current Task
    try:
        verification = await llm.verify_step(screenshot, current_task)
        print(f"Verification: {verification}")
        
        if verification.get("status") == "completed":
             return {
                 "current_task_index": idx + 1,
                 "history": state["history"] + [{"role": "model", "content": f"Task '{current_task}' Verified as Complete. Moving to next."}],
                 "screenshot": screenshot,
                 "step_count": state.get("step_count", 0) + 1
             }
    except Exception as e:
        print(f"Verification Warning: {e}") 
        # proceed to act if verification fails? or fail? let's proceed to try and act.

    # 3. If Not Verified, Act
    try:
        action_plan = await llm.get_action(
            screenshot_b64=screenshot, 
            goal=current_task,
            history=state["history"][-5:] # Keep history short
        )
        print(f"Action: {action_plan}")
    except Exception as e:
        return {"status": "failed", "history": state["history"] + [{"role": "system", "content": f"LLM failed: {e}"}]}
    
    action = action_plan.get("action", "fail")
    reason = action_plan.get("reason", "No reason provided")
    params = action_plan.get("params", {})
    
    new_history_item = {
        "role": "model",
        "action": action,
        "params": params,
        "reason": reason,
        "current_task": current_task
    }
    
    if action == "fail":
        return {"status": "failed", "history": state["history"] + [new_history_item]}
        
    try:
        if action == "tap":
            driver.tap(params.get("x"), params.get("y"))
        elif action == "type":
            driver.type_text(params.get("text"))
        elif action == "swipe":
            driver.swipe(params.get("start_x"), params.get("start_y"), params.get("end_x"), params.get("end_y"))
        elif action == "done":
             # Use explicit done action to force next task if verify failed but model thinks it's done
             return {
                 "current_task_index": idx + 1,
                 "history": state["history"] + [new_history_item],
                 "screenshot": screenshot,
                 "step_count": state.get("step_count", 0) + 1
             }

    except Exception as e:
         return {"status": "failed", "history": state["history"] + [new_history_item, {"role": "system", "content": f"Execution failed: {e}"}]}

    return {
        "history": state["history"] + [new_history_item], 
        "step_count": state.get("step_count", 0) + 1,
        "screenshot": screenshot 
    }

def check_loop(state: AgentState):
    if state["status"] in ["passed", "failed"]:
        return "cleanup"
    if state.get("step_count", 0) > 30: # increased limit
        return "cleanup"
    return "step_node"

def cleanup(state: AgentState):
    print("Cleaning up session")
    driver.quit()
    return {"status": state["status"] if state["status"] in ["passed", "failed"] else "timeout"}

workflow = StateGraph(AgentState)
workflow.add_node("setup", setup)
workflow.add_node("plan_node", plan_node)
workflow.add_node("step_node", step_node)
workflow.add_node("cleanup", cleanup)

workflow.set_entry_point("setup")
workflow.add_edge("setup", "plan_node")
workflow.add_edge("plan_node", "step_node")
workflow.add_conditional_edges("step_node", check_loop, {"step_node": "step_node", "cleanup": "cleanup"})
workflow.add_edge("cleanup", END)

agent_app = workflow.compile()
