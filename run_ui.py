"""Run the Jarvis web UI."""
import uvicorn, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

if __name__ == "__main__":
    print("\n  Jarvis UI → http://localhost:7860\n")
    uvicorn.run("ui.app:app", host="0.0.0.0", port=7860, reload=False)
