"""Script to test different Gemini model names in Vertex AI"""
import sys
sys.path.insert(0, 'app')
from config import Config
import vertexai
from vertexai.generative_models import GenerativeModel

config = Config()
project_id = config.project_id
region = config.region

print(f"Testing models for project: {project_id}, region: {region}\n")

# List of model names to try
models_to_test = [
    'gemini-1.5-flash',
    'gemini-1.5-flash-001',
    'gemini-1.5-flash-002',
    'gemini-1.5-pro',
    'gemini-1.5-pro-001',
    'gemini-pro',
    'gemini-1.0-pro',
]

vertexai.init(project=project_id, location=region)

for model_name in models_to_test:
    try:
        print(f"Testing: {model_name}... ", end="", flush=True)
        model = GenerativeModel(model_name)
        response = model.generate_content("Say hello")
        print(f"✅ SUCCESS! Response: {response.text[:50]}...")
        print(f"   → This model works! Update config.py to use: '{model_name}'\n")
        break
    except Exception as e:
        error_msg = str(e)
        if "404" in error_msg:
            print("❌ Not found")
        elif "403" in error_msg:
            print("❌ Permission denied")
        else:
            print(f"❌ Error: {error_msg[:60]}")

print("\nIf none worked, check Model Garden:")
print(f"https://console.cloud.google.com/vertex-ai/model-garden?project={project_id}")
print("\nLook for Gemini models and note the exact model name/ID.")
