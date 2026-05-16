import os

# Base Directory Locators
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Model Definitions
OLLAMA_MODEL = "zero"

# Default AUR binary path locator for Piper models
PIPER_MODEL_PATH = os.path.join(BASE_DIR, "voices", "en_US-ryan-high.onnx")
