import os
from dotenv import load_dotenv

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
APPIUM_SERVER_URL = os.getenv("APPIUM_SERVER_URL", "http://localhost:4723")
UPLOAD_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "uploads")
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")

os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(DATA_DIR, exist_ok=True)
