#!/usr/bin/env python3
"""Q21 Player SDK entry point.

Provides a simple wrapper for the q21-player CLI with demo mode support.

Usage:
    python run.py --scan                    # Single scan (process once and exit)
    python run.py --watch                   # Continuous mode (poll every 30s)
    python run.py --watch -p 10             # Continuous mode (poll every 10s)
    python run.py --watch --demo            # Continuous mode with DemoAI
    python run.py --test-connectivity       # Test Gmail and database

Options:
    --scan              Process messages once and exit
    --watch             Continuously poll for messages
    --demo              Use DemoAI instead of your PlayerAI
    -p, --poll-interval Seconds between scans (default: 30)
    --test-connectivity Test Gmail and database connection
"""
import os
import sys
from pathlib import Path

# Load .env BEFORE any q21_player imports (so LOG_LEVEL is available to logger)
def _load_env():
    env_path = Path(__file__).parent / ".env"
    if env_path.exists():
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, value = line.split("=", 1)
                    os.environ.setdefault(key.strip(), value.strip())

_load_env()


def show_help():
    """Show usage help."""
    print("""
Q21 Player SDK

Usage:
    python run.py --scan                    # Single scan (process once and exit)
    python run.py --watch                   # Continuous mode (poll every 30s)
    python run.py --watch -p 10             # Continuous mode (poll every 10s)
    python run.py --watch --demo            # Continuous mode with DemoAI
    python run.py --test-connectivity       # Test Gmail and database

Options:
    --scan              Process messages once and exit
    --watch             Continuously poll for messages (use this for games!)
    --demo              Use DemoAI instead of your PlayerAI
    -p, --poll-interval Seconds between scans (default: 30)
    --test-connectivity Test Gmail and database connection
    --help, -h          Show this help message
""")


def check_database_initialized():
    """Check if database tables exist. Returns True if OK, False if not initialized."""
    try:
        from q21_player._infra.database.pool import ConnectionPool
        from sqlalchemy import text

        pool = ConnectionPool()
        with pool.session() as session:
            # Check if player_states table exists
            result = session.execute(text(
                "SELECT EXISTS(SELECT 1 FROM information_schema.tables WHERE table_name = 'player_states')"
            )).scalar()
            return result
    except Exception:
        return False


def main():
    """Run the Q21 player with optional demo mode."""
    args = sys.argv[1:]

    # Show help if no args or --help
    if not args or "--help" in args or "-h" in args:
        show_help()
        return 0

    # Handle --demo flag
    if "--demo" in args:
        args.remove("--demo")
        os.environ["DEMO_MODE"] = "true"
        print("[Demo Mode] Using DemoAI for predictable responses")

    # Warn if using --scan (single mode)
    if "--scan" in args and "--watch" not in args:
        print("[Note] Using --scan (single scan). For continuous polling, use --watch")

    # Check if running scan/watch modes (need database)
    if "--scan" in args or "--watch" in args:
        if "--test-connectivity" not in args:
            try:
                if not check_database_initialized():
                    print("\n" + "=" * 60)
                    print("  ERROR: Database not initialized!")
                    print("=" * 60)
                    print("\n  The database tables have not been created yet.")
                    print("\n  Run this command first:")
                    print("    python init_db.py")
                    print("\n  Then try again:")
                    print(f"    python run.py {' '.join(sys.argv[1:])}")
                    print()
                    return 1
            except Exception as e:
                # If we can't check, let it proceed and fail with detailed error
                pass

    # Import and run the main CLI
    try:
        from q21_player._infra.cli.main import main as cli_main
        sys.argv = ["q21-player"] + args
        return cli_main()
    except ImportError as e:
        print(f"Error: q21_player package not installed. Run:")
        print(f"  pip install dist/q21_player-1.0.0-py3-none-any.whl")
        return 1


if __name__ == "__main__":
    sys.exit(main())
