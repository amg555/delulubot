
import os
from dotenv import load_dotenv

print(f"CWD: {os.getcwd()}")
print(f".env exists: {os.path.exists('.env')}")

# Clear GEMINI_MODEL if it exists in env to see if .env loads it
if "GEMINI_MODEL" in os.environ:
    print(f"GEMINI_MODEL already in environ: {os.environ['GEMINI_MODEL']}")
    # os.environ.pop("GEMINI_MODEL") # Don't pop yet, just observe

load_dotenv()

print(f"GEMINI_MODEL after load_dotenv: {os.getenv('GEMINI_MODEL')}")
print(f"GEMINI_FALLBACK_MODELS: {os.getenv('GEMINI_FALLBACK_MODELS')}")

with open('.env', 'r') as f:
    print("Content of .env:")
    print(f.read())
