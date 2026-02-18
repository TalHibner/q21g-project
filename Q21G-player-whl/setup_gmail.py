#!/usr/bin/env python3
"""Gmail OAuth setup script for Q21 Player SDK.

Initializes Gmail API credentials by:
1. Copying your OAuth client secret (client_secret.json) to the project
2. Running the OAuth flow to generate a token
3. Verifying the connection works

Usage:
    python setup_gmail.py
    python setup_gmail.py --credentials /path/to/downloaded/client_secret_XXXXX.json
"""
import argparse
import json
import shutil
import sys
from pathlib import Path


def print_header(text: str) -> None:
    """Print a section header."""
    print(f"\n{'=' * 60}")
    print(f"  {text}")
    print('=' * 60)


def print_step(num: int, text: str) -> None:
    """Print a step."""
    print(f"\n  Step {num}: {text}")
    print("  " + "-" * 50)


def ask(prompt: str, default: str = "") -> str:
    """Ask user for input."""
    if default:
        value = input(f"  {prompt} [{default}]: ").strip()
        return value if value else default
    while True:
        value = input(f"  {prompt}: ").strip()
        if value:
            return value
        print("  Please enter a value.")


def check_credentials_file(path: Path) -> bool:
    """Validate that the file looks like Google OAuth credentials."""
    try:
        with open(path) as f:
            data = json.load(f)
        # Check for expected structure
        if "installed" in data or "web" in data:
            return True
        print(f"  Warning: {path} doesn't look like Google OAuth credentials.")
        print("  Expected 'installed' or 'web' key in JSON.")
        return False
    except json.JSONDecodeError:
        print(f"  Error: {path} is not valid JSON.")
        return False
    except Exception as e:
        print(f"  Error reading {path}: {e}")
        return False


def run_oauth_flow(credentials_path: Path, token_path: Path) -> bool:
    """Run the OAuth flow to generate a token."""
    try:
        from google.auth.transport.requests import Request
        from google.oauth2.credentials import Credentials
        from google_auth_oauthlib.flow import InstalledAppFlow

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
            print(f"\n  Token saved to: {token_path}")

        return True

    except ImportError:
        print("  Error: Required packages not installed.")
        print("  Run: pip install google-auth-oauthlib google-api-python-client")
        return False
    except Exception as e:
        print(f"  OAuth flow failed: {e}")
        return False


def verify_gmail_connection(credentials_path: Path, token_path: Path) -> bool:
    """Verify we can connect to Gmail API."""
    try:
        from google.oauth2.credentials import Credentials
        from googleapiclient.discovery import build

        SCOPES = [
            "https://www.googleapis.com/auth/gmail.readonly",
            "https://www.googleapis.com/auth/gmail.send",
            "https://www.googleapis.com/auth/gmail.modify",
        ]

        creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)
        service = build("gmail", "v1", credentials=creds)
        profile = service.users().getProfile(userId="me").execute()

        email = profile.get("emailAddress", "unknown")
        print(f"  Connected as: {email}")
        return True

    except Exception as e:
        print(f"  Connection failed: {e}")
        return False


def main() -> int:
    """Run the Gmail setup."""
    parser = argparse.ArgumentParser(description="Setup Gmail OAuth credentials")
    parser.add_argument("--credentials", "-c", type=str,
                        help="Path to downloaded client_secret_XXXXX.json from Google Cloud Console")
    parser.add_argument("--token-path", "-t", type=str, default="token.json",
                        help="Where to save the OAuth token (default: token.json)")
    parser.add_argument("--dest", "-d", type=str, default="client_secret.json",
                        help="Where to copy credentials in project (default: client_secret.json)")
    args = parser.parse_args()

    print_header("Gmail OAuth Setup for Q21 Player SDK")

    # -------------------------------------------------------------------------
    # Step 1: Get credentials file
    # -------------------------------------------------------------------------
    print_step(1, "Locate OAuth Credentials")

    if args.credentials:
        source_path = Path(args.credentials)
    else:
        print("""
  You need OAuth credentials from Google Cloud Console.

  If you don't have them yet:
    1. Go to https://console.cloud.google.com/
    2. Create a new project (or select existing)
    3. Enable the Gmail API:
       - Go to "APIs & Services" > "Library"
       - Search for "Gmail API" and enable it
    4. Create OAuth credentials:
       - Go to "APIs & Services" > "Credentials"
       - Click "Create Credentials" > "OAuth client ID"
       - Choose "Desktop app" as application type
       - Download the JSON file

  IMPORTANT: Enter the FULL path including the filename and .json extension!
  Example (Windows): C:\\Users\\YourName\\Downloads\\client_secret_123456.json
  Example (macOS):   /Users/YourName/Downloads/client_secret_123456.json
""")
        source_input = ask("Full path to your downloaded client_secret JSON file")
        source_path = Path(source_input).expanduser()

    if not source_path.exists():
        print(f"\n  Error: File not found: {source_path}")
        return 1

    if not check_credentials_file(source_path):
        return 1

    print(f"  Found: {source_path}")

    # -------------------------------------------------------------------------
    # Step 2: Copy to project directory
    # -------------------------------------------------------------------------
    print_step(2, "Copy Credentials to Project")

    dest_path = Path(args.dest)
    token_path = Path(args.token_path)

    if dest_path.exists():
        overwrite = input(f"  {dest_path} already exists. Overwrite? [y/N]: ").strip().lower()
        if overwrite != 'y':
            print("  Using existing credentials file.")
        else:
            shutil.copy(source_path, dest_path)
            print(f"  Copied to: {dest_path}")
    else:
        shutil.copy(source_path, dest_path)
        print(f"  Copied to: {dest_path}")

    # -------------------------------------------------------------------------
    # Step 3: Run OAuth flow
    # -------------------------------------------------------------------------
    print_step(3, "Authenticate with Google")

    if not run_oauth_flow(dest_path, token_path):
        return 1

    # -------------------------------------------------------------------------
    # Step 4: Verify connection
    # -------------------------------------------------------------------------
    print_step(4, "Verify Gmail Connection")

    if not verify_gmail_connection(dest_path, token_path):
        return 1

    # -------------------------------------------------------------------------
    # Success
    # -------------------------------------------------------------------------
    print_header("Setup Complete!")
    print(f"""
  Credentials: {dest_path}
  Token:       {token_path}

  Gmail API is ready to use.

  Next steps:
    1. Run: python setup_config.py  (if you haven't already)
    2. Run: python verify_setup.py  (to verify full setup)
    3. Run: python run.py --scan --demo  (to test)
""")

    return 0


if __name__ == "__main__":
    sys.exit(main())
