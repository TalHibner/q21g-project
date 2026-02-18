#!/usr/bin/env python3
"""Unified setup script for Q21 Player SDK.

Runs all setup steps in the correct order:
1. Gmail OAuth (gets your email automatically)
2. Database configuration
3. Player identity and league settings
4. Verification

Usage:
    python setup.py
    python setup.py --skip-gmail    # Skip Gmail setup if already done
    python setup.py --skip-db       # Skip database setup
    python setup.py --skip-verify   # Skip verification step
"""
import argparse
import json
import shutil
import sys
from pathlib import Path


def print_header(text: str) -> None:
    print(f"\n{'=' * 60}")
    print(f"  {text}")
    print('=' * 60)


def print_step(num: int, total: int, text: str) -> None:
    print(f"\n  [{num}/{total}] {text}")
    print("  " + "-" * 50)


def ask(prompt: str, default: str = "", required: bool = True, password: bool = False) -> str:
    """Ask user for input with optional default value."""
    if default:
        display = f"  {prompt} [{default}]: "
    else:
        display = f"  {prompt}: "

    while True:
        if password:
            import getpass
            value = getpass.getpass(display)
        else:
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


def check_credentials_file(path: Path) -> bool:
    """Validate that the file looks like Google OAuth credentials."""
    try:
        with open(path) as f:
            data = json.load(f)
        if "installed" in data or "web" in data:
            return True
        print(f"    Warning: {path} doesn't look like Google OAuth credentials.")
        return False
    except json.JSONDecodeError:
        print(f"    Error: {path} is not valid JSON.")
        return False
    except Exception as e:
        print(f"    Error reading {path}: {e}")
        return False


def setup_gmail() -> tuple[bool, str, str, str]:
    """Setup Gmail OAuth and return (success, email, creds_path, token_path)."""
    print_header("Step 1: Gmail OAuth")

    credentials_path = Path("client_secret.json")
    token_path = Path("token.json")

    # Check if already set up
    if token_path.exists() and credentials_path.exists():
        print("\n  Gmail credentials already configured.")
        try:
            from google.oauth2.credentials import Credentials
            from googleapiclient.discovery import build

            SCOPES = [
                "https://www.googleapis.com/auth/gmail.readonly",
                "https://www.googleapis.com/auth/gmail.send",
                "https://www.googleapis.com/auth/gmail.modify",
            ]

            creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)
            if creds and creds.valid:
                service = build("gmail", "v1", credentials=creds)
                profile = service.users().getProfile(userId="me").execute()
                email = profile.get("emailAddress", "")
                print(f"  Already authenticated as: {email}")

                if ask_yes_no("Use this account?", default=True):
                    return True, email, str(credentials_path), str(token_path)
                else:
                    print("  Will re-authenticate...")
        except Exception:
            pass

    # Need to set up credentials
    if not credentials_path.exists():
        print("""
  You need OAuth credentials from Google Cloud Console.

  Quick setup:
    1. Go to https://console.cloud.google.com/
    2. Create project → Enable Gmail API
    3. OAuth consent screen → Add yourself as test user
    4. Credentials → Create OAuth client ID (Desktop app)
    5. Download the JSON file

  IMPORTANT: Enter the FULL path including the filename and .json extension!
  Example (Windows): C:\\Users\\YourName\\Downloads\\client_secret_123456.json
  Example (macOS):   /Users/YourName/Downloads/client_secret_123456.json
""")
        source_input = ask("Full path to your downloaded client_secret JSON file")
        source_path = Path(source_input).expanduser()

        if not source_path.exists():
            print(f"\n    Error: File not found: {source_path}")
            return False, "", "", ""

        if not check_credentials_file(source_path):
            return False, "", "", ""

        shutil.copy(source_path, credentials_path)
        print(f"  Copied credentials to: {credentials_path}")

    # Run OAuth flow
    print("\n  Starting OAuth flow...")
    try:
        from google.auth.transport.requests import Request
        from google.oauth2.credentials import Credentials
        from google_auth_oauthlib.flow import InstalledAppFlow
        from googleapiclient.discovery import build

        SCOPES = [
            "https://www.googleapis.com/auth/gmail.readonly",
            "https://www.googleapis.com/auth/gmail.send",
            "https://www.googleapis.com/auth/gmail.modify",
        ]

        creds = None
        if token_path.exists():
            creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                print("  Refreshing expired token...")
                creds.refresh(Request())
            else:
                print("  Opening browser for Google OAuth consent...")
                print("  (If browser doesn't open, check the URL in terminal)\n")
                flow = InstalledAppFlow.from_client_secrets_file(str(credentials_path), SCOPES)
                creds = flow.run_local_server(port=0)

            with open(token_path, "w") as token:
                token.write(creds.to_json())

        # Get email from profile
        service = build("gmail", "v1", credentials=creds)
        profile = service.users().getProfile(userId="me").execute()
        email = profile.get("emailAddress", "")

        print(f"\n  ✓ Authenticated as: {email}")
        print(f"  ✓ Token saved to: {token_path}")

        return True, email, str(credentials_path), str(token_path)

    except ImportError:
        print("    Error: Required packages not installed.")
        print("    Run: pip install google-auth-oauthlib google-api-python-client")
        return False, "", "", ""
    except Exception as e:
        print(f"    OAuth flow failed: {e}")
        return False, "", "", ""


def setup_database() -> tuple[str, str, str, str, str]:
    """Setup database configuration. Returns (host, port, name, user, password)."""
    print_header("Step 2: Database Configuration")
    print("\n  PostgreSQL database for storing game state.\n")

    use_database = ask_yes_no("Do you have a PostgreSQL database set up?", default=True)

    if use_database:
        db_host = ask("Database host", default="localhost")
        db_port = ask("Database port", default="5432")
        db_name = ask("Database name", default="gtai_player")
        db_user = ask("Database user", default="postgres")
        db_password = ask("Database password", password=True)
        return db_host, db_port, db_name, db_user, db_password
    else:
        print("\n    Note: Some features may not work without a database.")
        print("    You can set this up later in .env")
        return "localhost", "5432", "gtai_player", "postgres", ""


def setup_player_config(gmail_account: str = "") -> bool:
    """Setup player identity and league settings in config.json."""
    print_header("Step 3: Player & League Configuration")

    config_path = Path("js/config.json")

    if config_path.exists():
        if not ask_yes_no("config.json already exists. Overwrite?", default=False):
            print("  Keeping existing configuration.")
            return True

    # Player Identity
    print("\n  --- Your Player Identity ---\n")

    user_id = ask("Your user ID (provided by instructor)")

    default_name = user_id if user_id else ""
    display_name = ask("Your display name", default=default_name)

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
    return True


def generate_env_file(
    gmail_account: str,
    creds_path: str,
    token_path: str,
    db_host: str,
    db_port: str,
    db_name: str,
    db_user: str,
    db_password: str
) -> None:
    """Generate .env file with all environment variables."""
    env_path = Path(".env")

    env_lines = [
        "# Q21 Player SDK Environment Configuration",
        "# Generated by setup.py - DO NOT COMMIT",
        "",
        "# =============================================================================",
        "# Gmail API Configuration",
        "# =============================================================================",
        f"GMAIL_ACCOUNT={gmail_account}",
        f"GMAIL_CREDENTIALS_PATH={creds_path}",
        f"GMAIL_TOKEN_PATH={token_path}",
        "",
        "# =============================================================================",
        "# Database Configuration",
        "# =============================================================================",
        f"GTAI_DB_HOST={db_host}",
        f"GTAI_DB_PORT={db_port}",
        f"GTAI_DB_NAME={db_name}",
        f"GTAI_DB_USER={db_user}",
        f"GTAI_DB_PASSWORD={db_password}",
        "",
        "# =============================================================================",
        "# Application Settings",
        "# =============================================================================",
        "# Log level: Set to WARNING to only see protocol messages (suppress verbose INFO)",
        "LOG_LEVEL=WARNING",
        "",
        "POLL_INTERVAL_SEC=30",
        "DEMO_MODE=false",
        "",
        "# =============================================================================",
        "# LLM Configuration (Optional)",
        "# =============================================================================",
        "# LLM_METHOD=cli",
        "# LLM_DEFAULT_AGENT=CLAUDE_STRATEGY",
        "# LLM_TIMEOUT_SEC=120",
        "# LLM_MAX_RETRIES=3",
        "# LLM_FALLBACK_ENABLED=true",
        "",
        "# API Keys (only needed if LLM_METHOD=api)",
        "# ANTHROPIC_API_KEY=sk-ant-your-key-here",
        "# OPENAI_API_KEY=sk-your-key-here",
        "",
    ]

    with open(env_path, "w") as f:
        f.write("\n".join(env_lines))

    print(f"  ✓ Created: {env_path}")


def verify_setup() -> bool:
    """Run quick verification."""
    print_header("Step 4: Verification")

    issues = []

    # Check files
    checks = [
        ("js/config.json", "Configuration"),
        ("client_secret.json", "Gmail credentials"),
        ("token.json", "Gmail token"),
        ("my_player.py", "PlayerAI module"),
        (".env", "Environment file"),
    ]

    for path, name in checks:
        if Path(path).exists():
            print(f"  ✓ {name}")
        else:
            print(f"  ✗ {name} (missing)")
            issues.append(f"Missing: {path}")

    # Check config has required fields
    config_path = Path("js/config.json")
    if config_path.exists():
        try:
            with open(config_path) as f:
                config = json.load(f)

            if config.get("player", {}).get("user_id"):
                print(f"  ✓ Player ID: {config['player']['user_id']}")
            else:
                print("  ✗ Player ID not set")
                issues.append("player.user_id not set in config.json")

            if config.get("league", {}).get("manager_email"):
                print(f"  ✓ League Manager: {config['league']['manager_email']}")
            else:
                print("  ✗ League Manager not set")
                issues.append("league.manager_email not set in config.json")
        except Exception as e:
            print(f"  ✗ Config error: {e}")
            issues.append(f"Config error: {e}")

    # Quick Gmail check
    try:
        from google.oauth2.credentials import Credentials
        from googleapiclient.discovery import build

        token_path = Path("token.json")
        if token_path.exists():
            SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]
            creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)
            service = build("gmail", "v1", credentials=creds)
            profile = service.users().getProfile(userId="me").execute()
            print(f"  ✓ Gmail API: {profile.get('emailAddress', 'connected')}")
    except Exception as e:
        print(f"  ✗ Gmail API: {e}")
        issues.append(f"Gmail error: {e}")

    if issues:
        print(f"\n  {len(issues)} issue(s) found.")
        return False

    print("\n  All checks passed!")
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description="Setup Q21 Player SDK")
    parser.add_argument("--skip-gmail", action="store_true", help="Skip Gmail OAuth setup")
    parser.add_argument("--skip-db", action="store_true", help="Skip database setup")
    parser.add_argument("--skip-verify", action="store_true", help="Skip verification")
    args = parser.parse_args()

    print("\n" + "=" * 60)
    print("  Q21 Player SDK - Setup Wizard")
    print("=" * 60)
    print("\n  This wizard will configure your Q21 player.")
    print("  Press Enter to accept default values shown in [brackets].")

    gmail_account = ""
    creds_path = "client_secret.json"
    token_path = "token.json"
    db_host, db_port, db_name, db_user, db_password = "localhost", "5432", "gtai_player", "postgres", ""

    # Step 1: Gmail OAuth
    if not args.skip_gmail:
        success, gmail_account, creds_path, token_path = setup_gmail()
        if not success:
            print("\n  Gmail setup failed. You can retry with: python setup_gmail.py")
            if not ask_yes_no("Continue anyway?", default=False):
                return 1
            gmail_account = ask("Your Gmail address")

    # Step 2: Database
    if not args.skip_db:
        db_host, db_port, db_name, db_user, db_password = setup_database()

    # Step 3: Player & League config
    if not setup_player_config(gmail_account):
        return 1

    # Generate .env file
    print_header("Generating .env file")
    if not gmail_account:
        gmail_account = ask("Your Gmail address")
    generate_env_file(
        gmail_account, creds_path, token_path,
        db_host, db_port, db_name, db_user, db_password
    )

    # Step 4: Verification
    if not args.skip_verify:
        verify_setup()

    # Done
    print_header("Setup Complete!")
    print("""
  Files created:
    • .env           - Gmail & database credentials
    • js/config.json - Player identity & league settings

  Next steps:

    1. Test with demo mode:
       python run.py --scan --demo

    2. Implement your AI in my_player.py

    3. Run with your implementation:
       python run.py --scan
""")

    return 0


if __name__ == "__main__":
    sys.exit(main())
