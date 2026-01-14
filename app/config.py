import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Config:
    def __init__(self):
        self.project_id = os.getenv('GOOGLE_CLOUD_PROJECT')
        self.region = os.getenv('GOOGLE_CLOUD_REGION', 'us-central1')
        self.api_key = os.getenv('GOOGLE_AI_API_KEY')
        self.chat_model = 'gemini-2.5-flash'
        self.embedding_model = 'text-embedding-004'
        
        # API key is required for Google AI API
        if not self.api_key:
            raise ValueError(
                "GOOGLE_AI_API_KEY environment variable is not set. "
                "Please set it in your .env file or environment."
            )