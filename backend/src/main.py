from fastapi import FastAPI, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import os
from pydantic import BaseModel
from .config import DATA_DIR
from .upload import router as upload_router
from .agent import agent_app

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

# In-memory store for run results (MVP)
runs = {}

async def run_agent_task(run_id: str, apk_path: str, test_prompt: str):
    print(f"Background task started for run {run_id}")
    try:
        initial_state = {
            "test_prompt": test_prompt,
            "apk_path": apk_path,
            "history": [],
            "status": "running",
            "step_count": 0,
            "screenshot": ""
        }
        # Run the graph
        final_state = await agent_app.ainvoke(initial_state)
        runs[run_id] = final_state
    except Exception as e:
        print(f"Run {run_id} failed: {e}")
        runs[run_id] = {"status": "failed", "error": str(e)}

@app.post("/test")
async def start_test(request: TestRequest, background_tasks: BackgroundTasks):
    import uuid
    run_id = str(uuid.uuid4())
    runs[run_id] = {"status": "starting"}
    background_tasks.add_task(run_agent_task, run_id, request.apk_path, request.test_prompt)
    return {"run_id": run_id, "status": "started"}

@app.get("/test/{run_id}")
async def get_test_status(run_id: str):
    return runs.get(run_id, {"status": "not_found"})

@app.get("/")
async def root():
    return {"message": "Zendroid API is running"}

if __name__ == "__main__":
    uvicorn.run("src.main:app", host="0.0.0.0", port=8000, reload=True)
