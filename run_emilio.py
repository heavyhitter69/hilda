"""Launch Hilda — kept as run_emilio.py for existing shortcuts."""
import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

if __name__ == "__main__":
    print("Starting Hilda...")
    import main

    try:
        asyncio.run(main.main())
    except KeyboardInterrupt:
        print("Hilda shut down.")
