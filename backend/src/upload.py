from fastapi import APIRouter, UploadFile, File, HTTPException
import shutil
import os
from .config import UPLOAD_DIR

router = APIRouter()

@router.post("/upload")
async def upload_apk(file: UploadFile = File(...)):
    if not file.filename.endswith(".apk"):
         raise HTTPException(status_code=400, detail="Only APK files allowed")
    
    file_path = os.path.join(UPLOAD_DIR, file.filename)
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    return {"filename": file.filename, "status": "uploaded", "path": file_path}
