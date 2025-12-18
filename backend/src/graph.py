from typing import TypedDict, Annotated, List, Dict, Any
from langgraph.graph import StateGraph, END
import operator
from .llm import GeminiClient
from .appium_client import AppiumDriver, ElementSelector

class AgentState(TypedDict):
    """State schema for the agent workflow"""
    run_id: str
    goal: str
    plan: List[str]
    current_step_index: int
    history: Annotated[List[Dict], operator.add]
    screenshot: str
    page_source: str
    last_action: Dict[str, Any]
    status: str
    messages: List[Dict]
    retry_count: int

class WorkflowManager:
    """Manages the LangGraph workflow for test automation"""
    
    MAX_RETRIES = 3
    
    def __init__(self, llm: GeminiClient, driver: AppiumDriver):
        self.llm = llm
        self.driver = driver
        self.workflow = self._build_graph()
        
    def _build_graph(self) -> StateGraph:
        """Build the execution graph"""
        workflow = StateGraph(AgentState)
        
        workflow.add_node("planner", self.plan_node)
        workflow.add_node("navigator", self.navigator_node)
        workflow.add_node("executor", self.executor_node)
        
        workflow.set_entry_point("planner")
        workflow.add_edge("planner", "navigator")
        
        workflow.add_conditional_edges(
            "navigator",
            self._should_continue,
            {
                "execute": "executor",
                "end": END
            }
        )
        
        workflow.add_conditional_edges(
            "executor",
            self._after_execution,
            {
                "continue": "navigator",
                "end": END
            }
        )
        
        return workflow.compile()

    async def plan_node(self, state: AgentState) -> Dict[str, Any]:
        """Create execution plan from goal"""
        print("=== PLANNER NODE ===")
        
        try:
            plan = await self.llm.plan_task(state["goal"])
            
            return {
                "plan": plan,
                "retry_count": 0,
                "history": [{
                    "role": "system",
                    "content": f"Plan created with {len(plan)} steps"
                }],
                "messages": [{
                    "type": "plan",
                    "tasks": plan,
                    "message": f"Created {len(plan)}-step plan"
                }]
            }
        except Exception as e:
            return {
                "status": "failed",
                "messages": [{
                    "type": "error",
                    "message": f"Planning failed: {str(e)}"
                }]
            }

    async def navigator_node(self, state: AgentState) -> Dict[str, Any]:
        """Analyze UI and decide next action"""
        print("=== NAVIGATOR NODE ===")
        
        # Get current task
        if state["current_step_index"] >= len(state["plan"]):
            return {
                "last_action": {"action": "complete"},
                "messages": [{
                    "type": "info",
                    "message": "All tasks completed"
                }]
            }
        
        current_task = state["plan"][state["current_step_index"]]
        print(f"Current task: {current_task}")
        
        try:
            # Capture UI state
            ui_context = self.driver.get_ui_context()
            screenshot = ui_context["screenshot"]
            page_source = ui_context["page_source"]
            
            # Get LLM decision with UI hierarchy
            analysis = await self.llm.analyze_screen_with_hierarchy(
                screenshot_b64=screenshot,
                page_source=page_source,
                current_task=current_task,
                history=state["history"][-10:]  # Keep recent context
            )
            
            return {
                "screenshot": screenshot,
                "page_source": page_source,
                "last_action": analysis,
                "messages": [
                    {
                        "type": "screenshot",
                        "data": screenshot
                    },
                    {
                        "type": "action_plan",
                        "action": analysis["action"],
                        "reason": analysis.get("reason", ""),
                        "selector": analysis.get("selector", {})
                    }
                ]
            }
            
        except Exception as e:
            print(f"Navigator error: {e}")
            return {
                "status": "failed",
                "messages": [{
                    "type": "error",
                    "message": f"Navigation failed: {str(e)}"
                }]
            }

    async def executor_node(self, state: AgentState) -> Dict[str, Any]:
        """Execute the planned action"""
        print("=== EXECUTOR NODE ===")
        
        action = state["last_action"]
        cmd = action.get("action")
        
        if not cmd:
            return self._execution_error("No action specified")
        
        try:
            if cmd == "click":
                success = self._execute_click(action)
                
            elif cmd == "type":
                success = self._execute_type(action)
                
            elif cmd == "swipe":
                success = self._execute_swipe(action)
                
            elif cmd == "done":
                return self._task_completed(state)
                
            elif cmd == "complete":
                return self._workflow_completed()
                
            elif cmd == "wait":
                return self._execute_wait(action)
                
            else:
                return self._execution_error(f"Unknown action: {cmd}")
            
            # Handle success/failure
            if success:
                return self._action_success(cmd, action)
            else:
                return self._action_failed(state, cmd, action)
                
        except Exception as e:
            print(f"Executor error: {e}")
            return self._execution_error(str(e))

    def _execute_click(self, action: Dict) -> bool:
        """Execute click action"""
        selector_data = action.get("selector")
        
        if selector_data:
            # Primary: Element-based click
            selector = ElementSelector(
                selector_type=selector_data.get("type", "id"),
                value=selector_data.get("value", "")
            )
            return self.driver.click_element(selector)
        
        # Fallback: Coordinate-based
        coords = action.get("coordinates", {})
        if coords:
            x, y = coords.get("x"), coords.get("y")
            if x and y:
                self.driver.tap_coordinates(x, y)
                return True
        
        return False

    def _execute_type(self, action: Dict) -> bool:
        """Execute type action"""
        text = action.get("text", "")
        selector_data = action.get("selector")
        
        if selector_data:
            selector = ElementSelector(
                selector_type=selector_data.get("type", "id"),
                value=selector_data.get("value", "")
            )
            return self.driver.type_into_element(selector, text)
        
        return False

    def _execute_swipe(self, action: Dict) -> bool:
        """Execute swipe action"""
        params = action.get("params", {})
        self.driver.swipe(
            start_x=params.get("start_x", 0),
            start_y=params.get("start_y", 0),
            end_x=params.get("end_x", 0),
            end_y=params.get("end_y", 0)
        )
        return True

    def _execute_wait(self, action: Dict) -> Dict[str, Any]:
        """Execute wait action"""
        import asyncio
        duration = action.get("duration", 2)
        asyncio.sleep(duration)
        return self._action_success("wait", action)

    def _task_completed(self, state: AgentState) -> Dict[str, Any]:
        """Handle task completion"""
        completed_task = state["plan"][state["current_step_index"]]
        
        return {
            "current_step_index": state["current_step_index"] + 1,
            "retry_count": 0,
            "history": [{
                "role": "assistant",
                "action": "task_complete",
                "task": completed_task
            }],
            "messages": [{
                "type": "task_complete",
                "message": f"✓ Completed: {completed_task}"
            }]
        }

    def _workflow_completed(self) -> Dict[str, Any]:
        """Handle workflow completion"""
        return {
            "status": "completed",
            "messages": [{
                "type": "complete",
                "message": "All tasks completed successfully"
            }]
        }

    def _action_success(self, cmd: str, action: Dict) -> Dict[str, Any]:
        """Handle successful action"""
        return {
            "retry_count": 0,
            "history": [{
                "role": "assistant",
                "action": cmd,
                "details": action
            }],
            "messages": [{
                "type": "action_executed",
                "message": f"✓ Executed: {cmd}"
            }]
        }

    def _action_failed(self, state: AgentState, cmd: str, action: Dict) -> Dict[str, Any]:
        """Handle failed action with retry logic"""
        retry_count = state.get("retry_count", 0) + 1
        
        if retry_count >= self.MAX_RETRIES:
            return {
                "status": "failed",
                "messages": [{
                    "type": "error",
                    "message": f"Action '{cmd}' failed after {retry_count} attempts"
                }]
            }
        
        return {
            "retry_count": retry_count,
            "messages": [{
                "type": "warning",
                "message": f"Action '{cmd}' failed, retrying ({retry_count}/{self.MAX_RETRIES})"
            }]
        }

    def _execution_error(self, error_msg: str) -> Dict[str, Any]:
        """Handle execution error"""
        return {
            "status": "failed",
            "messages": [{
                "type": "error",
                "message": f"Execution error: {error_msg}"
            }]
        }

    def _should_continue(self, state: AgentState) -> str:
        """Decide whether to execute or end"""
        if state.get("status") == "failed":
            return "end"
        
        action = state.get("last_action", {}).get("action")
        
        if action == "complete":
            return "end"
        
        if action in ["click", "type", "swipe", "wait"]:
            return "execute"
        
        return "end"

    def _after_execution(self, state: AgentState) -> str:
        """Decide next step after execution"""
        if state.get("status") in ["failed", "completed"]:
            return "end"
        
        # Continue to next navigation cycle
        return "continue"