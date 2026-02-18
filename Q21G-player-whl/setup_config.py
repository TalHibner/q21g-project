#!/usr/bin/env python3
"""Configuration setup script for Q21 Player SDK.

Generates js/config.json with player identity and league settings.
For full setup including Gmail and database, use: python setup.py

Usage:
    python setup_config.py
"""
import json
import sys
from pathlib import Path


def ask(prompt: str, default: str = "", required: bool = True) -> str:
    """Ask user for input with optional default value."""
    if default:
        display = f"  {prompt} [{default}]: "
    else:
        display = f"  {prompt}: "

    while True:
        value = input(display).strip()
        if not value and default:
            return default
        if value:
            return value
        if not required:
            return ""
        print("    This field is required. Please enter a value.")


def ask_yes_no(prompt: str, default: bool = False) -> bool:
    """Ask user for yes/no input."""
    default_str = "Y/n" if default else "y/N"
    while True:
        value = input(f"  {prompt} [{default_str}]: ").strip().lower()
        if not value:
            return default
        if value in ("y", "yes"):
            return True
        if value in ("n", "no"):
            return False
        print("    Please enter 'y' or 'n'.")


def main() -> int:
    """Run the configuration setup."""
    print("\n" + "=" * 60)
    print("  Q21 Player SDK - Configuration Setup")
    print("=" * 60)
    print("\n  This script creates js/config.json with player & league settings.")
    print("  Press Enter to accept default values shown in [brackets].\n")

    config_path = Path("js/config.json")

    if config_path.exists():
        if not ask_yes_no("config.json already exists. Overwrite?", default=False):
            print("  Keeping existing configuration.")
            return 0

    # Player Identity
    print("  --- Your Player Identity ---\n")

    user_id = ask("Your user ID (provided by instructor)")
    display_name = ask("Your display name", default=user_id)

    # League Settings
    print("\n  --- League Settings ---\n")

    manager_email = ask("League Manager email (provided by instructor)")

    # Generate config.json
    config = {
        "league": {
            "manager_email": manager_email,
            "league_id": "LEAGUE001",
            "protocol_version": "league.v2"
        },
        "player": {
            "user_id": user_id,
            "display_name": display_name,
            "game_types": ["q21"]
        },
        "app": {
            "player_ai_module": "my_player",
            "player_ai_class": "MyPlayerAI"
        }
    }

    Path("js").mkdir(exist_ok=True)
    with open(config_path, "w") as f:
        json.dump(config, f, indent=2)
        f.write("\n")

    print(f"\n  ✓ Created: {config_path}")

    print("""
  Note: This only creates config.json.

  For full setup (Gmail, database, .env), run:
    python setup.py
""")

    return 0


if __name__ == "__main__":
    sys.exit(main())
