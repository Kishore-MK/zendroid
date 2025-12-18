from typing import List, Dict, Any, Optional
from .appium_client import AppiumDriver
from .llm import GeminiClient
from .graph import WorkflowManager
import asyncio
from fastapi import WebSocket
from enum import Enum

class AgentStatus(Enum):
    """Agent execution states"""
    INITIALIZED = "initialized"
    SETTING_UP = "setting_up"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    STOPPED = "stopped"

class AgentRunner:
    """Main agent orchestrator with WebSocket communication"""
    
    MAX_HISTORY_SIZE = 50
    
    def __init__(self, run_id: str, apk_path: str, test_prompt: str):
        self.run_id = run_id
        self.apk_path = apk_path
        self.test_prompt = test_prompt
        
        # Core components
        self.driver = AppiumDriver()
        self.llm = GeminiClient()
        self.graph_manager: Optional[WorkflowManager] = None
        
        # Communication
        self.websocket: Optional[WebSocket] = None
        
        # State management
        self.status = AgentStatus.INITIALIZED
        self.history: List[Dict] = []
        self.should_stop = False
        
        # Tool dispatcher for user chat
        self.tool_dispatcher = {
            "stop_agent": self._tool_stop_agent,
            "restart_agent": self._tool_restart_agent,
            "update_goal": self._tool_update_goal,
            "reply_to_user": self._tool_reply_to_user,
            "pause_agent": self._tool_pause_agent,
            "resume_agent": self._tool_resume_agent
        }
        
    def set_websocket(self, websocket: WebSocket) -> None:
        """Attach WebSocket for frontend communication"""
        self.websocket = websocket
        
    async def send_message(self, message_type: str, **kwargs) -> None:
        """Send structured message to frontend via WebSocket"""
        if not self.websocket:
            return
            
        try:
            await self.websocket.send_json({
                "type": message_type,
                "timestamp": self._get_timestamp(),
                **kwargs
            })
        except Exception as e:
            print(f"WebSocket send error: {e}")
            
    async def handle_user_input(self, message: str) -> None:
        """
        Process user chat input using LLM intent classification
        Routes to appropriate tool handler
        """
        try:
            # Get recent context for better understanding
            recent_history = self.history[-5:] if self.history else []
            
            # LLM interprets user intent and returns tool call
            tool_call = await self.llm.interpret_chat(
                message=message,
                history=recent_history,
                current_status=self.status.value
            )
            
            intent = tool_call.get("intent", "reply_to_user")
            handler = self.tool_dispatcher.get(intent, self._tool_reply_to_user)
            
            await handler(tool_call)
            
        except Exception as e:
            await self.send_message(
                "chat_response",
                message=f"Sorry, I encountered an error: {str(e)}",
                sender="agent"
            )

    async def _tool_stop_agent(self, args: Dict) -> None:
        """Stop agent execution"""
        self.stop()
        await self.send_message(
            "chat_response",
            message="Stopping the agent as requested.",
            sender="agent"
        )
        await self.send_message("status", message="Agent stopped by user")

    async def _tool_pause_agent(self, args: Dict) -> None:
        """Pause agent execution"""
        if self.status == AgentStatus.RUNNING:
            self.status = AgentStatus.PAUSED
            await self.send_message(
                "chat_response",
                message="Pausing agent execution.",
                sender="agent"
            )

    async def _tool_resume_agent(self, args: Dict) -> None:
        """Resume agent execution"""
        if self.status == AgentStatus.PAUSED:
            self.status = AgentStatus.RUNNING
            await self.send_message(
                "chat_response",
                message="Resuming agent execution.",
                sender="agent"
            )

    async def _tool_restart_agent(self, args: Dict) -> None:
        """Restart agent from beginning"""
        self.stop()
        await asyncio.sleep(1)  # Allow cleanup
        
        self._reset_state()
        
        await self.send_message(
            "chat_response",
            message="Restarting the agent...",
            sender="agent"
        )
        
        # Start new run
        asyncio.create_task(self.run())

    async def _tool_update_goal(self, args: Dict) -> None:
        """Update goal and restart"""
        new_goal = args.get("new_goal", "")
        
        if not new_goal:
            await self.send_message(
                "chat_response",
                message="Please provide a valid goal.",
                sender="agent"
            )
            return
        
        self.stop()
        await asyncio.sleep(1)
        
        self.test_prompt = new_goal
        self._reset_state()
        
        await self.send_message(
            "chat_response",
            message=f"Updated goal to: '{new_goal}'. Restarting...",
            sender="agent"
        )
        
        asyncio.create_task(self.run())

    async def _tool_reply_to_user(self, args: Dict) -> None:
        """Send conversational reply to user"""
        message = args.get("message", "I'm here to help!")
        await self.send_message(
            "chat_response",
            message=message,
            sender="agent"
        )

    def _reset_state(self) -> None:
        """Reset agent state for fresh run"""
        self.should_stop = False
        self.status = AgentStatus.INITIALIZED
        self.history = []
        self.graph_manager = None
        
    def get_status(self) -> str:
        """Get current agent status"""
        return self.status.value
        
    def get_history(self) -> List[Dict]:
        """Get execution history"""
        return self.history
        
    def stop(self) -> None:
        """Signal agent to stop"""
        self.should_stop = True
        self.status = AgentStatus.STOPPED
        
    async def run(self) -> None:
        """
        Main agent execution loop using LangGraph workflow
        Orchestrates setup, execution, and cleanup
        """
        try:
            # === SETUP PHASE ===
            self.status = AgentStatus.SETTING_UP
            await self.send_message("status", message="Initializing Appium session...")
            
            try:
                self.driver.start_session(self.apk_path)
                await self.send_message(
                    "status",
                    message="Appium connected. Initializing AI brain..."
                )
            except Exception as e:
                await self.send_message("error", message=f"Setup failed: {str(e)}")
                self.status = AgentStatus.FAILED
                return

            # === EXECUTION PHASE ===
            self.status = AgentStatus.RUNNING
            
            # Initialize workflow graph
            self.graph_manager = WorkflowManager(self.llm, self.driver)
            
            # Initial state
            initial_state = {
                "run_id": self.run_id,
                "goal": self.test_prompt,
                "plan": [],
                "current_step_index": 0,
                "history": [],
                "screenshot": "",
                "page_source": "",
                "last_action": {},
                "status": "running",
                "messages": [],
                "retry_count": 0
            }
            
            await self.send_message("status", message="Agent executing workflow...")
            
            # Stream execution through graph
            async for event in self.graph_manager.workflow.astream(initial_state):
                # Check for stop signal
                if self.should_stop:
                    await self.send_message("status", message="Agent stopped by user")
                    break
                
                # Check for pause
                while self.status == AgentStatus.PAUSED:
                    await asyncio.sleep(0.5)
                    if self.should_stop:
                        break
                
                # Process graph events
                for node_name, state_update in event.items():
                    print(f"Node '{node_name}' executed")
                    
                    # Track history
                    if "history" in state_update:
                        self._update_history(state_update["history"])
                    
                    # Forward messages to frontend
                    if "messages" in state_update:
                        for msg in state_update["messages"]:
                            await self.send_message(
                                msg["type"],
                                **{k: v for k, v in msg.items() if k != "type"}
                            )
                    
                    # Check terminal states
                    status = state_update.get("status")
                    if status == "failed":
                        self.status = AgentStatus.FAILED
                        await self.send_message(
                            "error",
                            message="Workflow failed"
                        )
                    elif status == "completed":
                        self.status = AgentStatus.COMPLETED
            
            # Workflow completed
            if self.status == AgentStatus.RUNNING:
                self.status = AgentStatus.COMPLETED
                
            await self.send_message(
                "complete",
                status=self.status.value,
                message="Workflow execution finished"
            )
                
        except Exception as e:
            print(f"Fatal error in agent run: {e}")
            await self.send_message("error", message=f"Fatal error: {str(e)}")
            self.status = AgentStatus.FAILED
            
        finally:
            await self.cleanup()
            
    def _update_history(self, new_entries: List[Dict]) -> None:
        """Update history with size limit"""
        self.history.extend(new_entries)
        
        # Trim if exceeds max size
        if len(self.history) > self.MAX_HISTORY_SIZE:
            self.history = self.history[-self.MAX_HISTORY_SIZE:]
            
    def _get_timestamp(self) -> str:
        """Get current timestamp"""
        from datetime import datetime
        return datetime.utcnow().isoformat()
            
    async def cleanup(self) -> None:
        """Cleanup resources gracefully"""
        await self.send_message("status", message="Cleaning up resources...")
        
        try:
            self.driver.quit()
            print("Driver cleanup completed")
        except Exception as e:
            print(f"Cleanup error: {e}")
            
        await self.send_message("status", message="Cleanup complete")