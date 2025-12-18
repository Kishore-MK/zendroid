from fastapi import FastAPI, BackgroundTasks, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import asyncio
from pydantic import BaseModel
from .config import DATA_DIR
from .upload import router as upload_router
from .agent import AgentRunner
from typing import Dict
import json

app = FastAPI(title="Zendroid API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(upload_router)

class TestRequest(BaseModel):
    apk_path: str
    test_prompt: str

# In-memory store for active agent runners
active_agents: Dict[str, AgentRunner] = {}

@app.post("/test/start")
async def start_test(request: TestRequest):
    """Initialize a new test run and return run_id"""
    import uuid
    run_id = str(uuid.uuid4())
    
    agent = AgentRunner(run_id, request.apk_path, request.test_prompt)
    active_agents[run_id] = agent
    
    return {
        "run_id": run_id,
        "status": "created",
        "message": "Connect to WebSocket to start execution"
    }

@app.websocket("/ws/test/{run_id}")
async def websocket_endpoint(websocket: WebSocket, run_id: str):
    """WebSocket endpoint for real-time agent interaction"""
    await websocket.accept()
    
    if run_id not in active_agents:
        await websocket.send_json({
            "type": "error",
            "message": "Invalid run_id. Please start a test first."
        })
        await websocket.close()
        return
    
    agent = active_agents[run_id]
    agent.set_websocket(websocket)
    
    try:
        # Start agent execution in background
        agent_task = asyncio.create_task(agent.run())
        
        # Listen for user messages
        while True:
            try:
                data = await websocket.receive_text()
                message = json.loads(data)
                
                # Handle user input
                if message.get("type") == "user_message":
                    await agent.handle_user_input(message.get("message", ""))
                    
            except WebSocketDisconnect:
                print(f"WebSocket disconnected for run {run_id}")
                agent.stop()
                break
            except json.JSONDecodeError:
                await websocket.send_json({
                    "type": "error",
                    "message": "Invalid JSON format"
                })
            except Exception as e:
                print(f"Error in WebSocket handler: {e}")
                break
        
        # Wait for agent to finish
        await agent_task
        
    except Exception as e:
        print(f"WebSocket error for run {run_id}: {e}")
        await websocket.send_json({
            "type": "error",
            "message": f"Internal error: {str(e)}"
        })
    finally:
        # Cleanup
        if run_id in active_agents:
            del active_agents[run_id]
        try:
            await websocket.close()
        except:
            pass

@app.get("/test/{run_id}")
async def get_test_status(run_id: str):
    """Get current status of a test run"""
    if run_id in active_agents:
        agent = active_agents[run_id]
        return {
            "run_id": run_id,
            "status": agent.get_status(),
            "history": agent.get_history()
        }
    return {"status": "not_found"}

@app.delete("/test/{run_id}")
async def stop_test(run_id: str):
    """Stop a running test"""
    if run_id in active_agents:
        agent = active_agents[run_id]
        agent.stop()
        del active_agents[run_id]
        return {"status": "stopped"}
    return {"status": "not_found"}

@app.get("/")
async def root():
    return {"message": "Zendroid API is running"}

if __name__ == "__main__":
    uvicorn.run("src.main:app", host="0.0.0.0", port=8000, reload=True)