"""
main.py — Run your Q21 Referee
================================

    python main.py

The runner will:
  1. Connect to your email inbox (OAuth)
  2. Poll for incoming protocol messages
  3. Call YOUR AI functions when triggered
  4. Send responses automatically

Press Ctrl+C to stop.
"""

import json
import logging
import os
import sys
from pathlib import Path

# Load .env for ANTHROPIC_API_KEY and other vars
_DIR = Path(__file__).resolve().parent
_ROOT = _DIR.parents[1]  # q21g-project/

for env_path in [_DIR.parent / ".env", _ROOT / ".env"]:
    if env_path.exists():
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, value = line.split("=", 1)
                    os.environ.setdefault(key.strip(), value.strip())

# ── Setup logging ──
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    datefmt="%H:%M:%S",
)

# ── Load config ──
config_path = _DIR.parent / "config.json"
if not config_path.exists():
    print(f"ERROR: config.json not found at {config_path}")
    print("Run: python setup_config.py")
    sys.exit(1)

with open(config_path) as f:
    config = json.load(f)

# ── Create AI and run ──
from q21_referee import RLGMRunner
from my_ai import MyRefereeAI

my_ai = MyRefereeAI()
runner = RLGMRunner(config=config, ai=my_ai)
runner.run()
