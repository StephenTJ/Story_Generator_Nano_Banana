import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    GEMINI_API_KEY = os.getenv("GOOGLE_API_KEY")
    MODEL_ID = os.getenv("MODEL_ID", "gemini-1.5-flash")

    SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-here")
    DEBUG = os.getenv("DEBUG", "True").lower() in ['true', '1', 'yes']

    DEFAULT_PROMPT = (
        "Short illustrated story about a middle-class person from India who founds a startup "
        "that becomes a unicorn and builds humanoid robots that help society."
    )
    DEFAULT_DESIRED_SCENES = 6
    MAX_ATTEMPTS = 3
    
    OUTPUT_DIR = "outputs"
    UPLOAD_FOLDER = "uploads"
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file size
