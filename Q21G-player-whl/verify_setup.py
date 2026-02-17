#!/usr/bin/env python3
"""Verification script for Q21 Player SDK setup.

Checks that all components are properly configured:
1. Required files exist (.env, config.json, credentials)
2. Environment variables are set
3. Config has required fields
4. Gmail API works
5. Database connection works (optional)
6. PlayerAI can be loaded

Usage:
    python verify_setup.py
    python verify_setup.py --verbose
"""
import argparse
import importlib
import json
import os
import sys
from pathlib import Path


class Colors:
    """ANSI color codes for terminal output."""
    GREEN = "\033[92m"
    RED = "\033[91m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    RESET = "\033[0m"
    BOLD = "\033[1m"


def ok(msg: str) -> None:
    print(f"  {Colors.GREEN}✓{Colors.RESET} {msg}")


def fail(msg: str) -> None:
    print(f"  {Colors.RED}✗{Colors.RESET} {msg}")


def warn(msg: str) -> None:
    print(f"  {Colors.YELLOW}!{Colors.RESET} {msg}")


def info(msg: str) -> None:
    print(f"  {Colors.BLUE}ℹ{Colors.RESET} {msg}")


def header(msg: str) -> None:
    print(f"\n{Colors.BOLD}{msg}{Colors.RESET}")
    print("-" * 50)


class SetupVerifier:
    """Verifies Q21 Player SDK setup."""

    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        self.errors: list[str] = []
        self.warnings: list[str] = []
        self.config: dict = {}

    def load_env(self) -> None:
        """Load .env file if it exists."""
        env_path = Path(".env")
        if env_path.exists():
            try:
                from dotenv import load_dotenv
                load_dotenv(env_path)
            except ImportError:
                # Manual parsing if dotenv not installed
                with open(env_path) as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith("#") and "=" in line:
                            key, value = line.split("=", 1)
                            os.environ[key.strip()] = value.strip()

    def check_required_files(self) -> bool:
        """Check that required files exist."""
        header("1. Required Files")

        results = []

        # .env file
        if Path(".env").exists():
            ok(".env file")
            results.append(True)
        else:
            fail(".env file (not found)")
            info("Run: python setup.py")
            self.errors.append("Missing .env file")
            results.append(False)

        # config.json
        if Path("js/config.json").exists():
            ok("js/config.json")
            results.append(True)
        else:
            fail("js/config.json (not found)")
            info("Run: python setup.py")
            self.errors.append("Missing js/config.json")
            results.append(False)

        # client_secret.json
        creds_path = os.getenv("GMAIL_CREDENTIALS_PATH", "client_secret.json")
        if Path(creds_path).exists():
            ok(f"Gmail credentials: {creds_path}")
            results.append(True)
        else:
            fail(f"Gmail credentials: {creds_path} (not found)")
            info("Run: python setup_gmail.py")
            self.errors.append("Missing Gmail credentials")
            results.append(False)

        # token.json (optional but recommended)
        token_path = os.getenv("GMAIL_TOKEN_PATH", "token.json")
        if Path(token_path).exists():
            ok(f"Gmail token: {token_path}")
        else:
            warn(f"Gmail token: {token_path} (not found)")
            info("Will be created on first Gmail connection")
            self.warnings.append("Gmail token not yet created")

        # my_player.py
        if Path("my_player.py").exists():
            ok("my_player.py")
            results.append(True)
        else:
            fail("my_player.py (not found)")
            self.errors.append("Missing my_player.py")
            results.append(False)

        return all(results)

    def check_env_vars(self) -> bool:
        """Check that required environment variables are set."""
        header("2. Environment Variables")

        required_vars = [
            ("GMAIL_ACCOUNT", "Gmail account"),
            ("GMAIL_CREDENTIALS_PATH", "Gmail credentials path"),
        ]

        optional_vars = [
            ("GTAI_DB_HOST", "Database host"),
            ("GTAI_DB_NAME", "Database name"),
            ("GTAI_DB_USER", "Database user"),
        ]

        all_ok = True

        for var, desc in required_vars:
            value = os.getenv(var)
            if value:
                # Mask sensitive parts
                display = value if "@" not in value else value
                ok(f"{desc}: {display}")
            else:
                fail(f"{desc}: {var} not set")
                self.errors.append(f"{var} not set in .env")
                all_ok = False

        for var, desc in optional_vars:
            value = os.getenv(var)
            if value:
                ok(f"{desc}: {value}")
            else:
                warn(f"{desc}: {var} not set")

        return all_ok

    def check_config(self) -> bool:
        """Check that config.json is valid and has required fields."""
        header("3. Configuration (js/config.json)")

        config_path = Path("js/config.json")
        if not config_path.exists():
            fail("Config file not found")
            return False

        try:
            with open(config_path) as f:
                self.config = json.load(f)
            ok("Valid JSON")
        except json.JSONDecodeError as e:
            fail(f"Invalid JSON: {e}")
            self.errors.append("Invalid JSON in config.json")
            return False

        all_ok = True

        # Check player section
        player = self.config.get("player", {})
        if player.get("user_id"):
            ok(f"player.user_id: {player['user_id']}")
        else:
            fail("player.user_id: not set")
            self.errors.append("player.user_id not set")
            all_ok = False

        if player.get("display_name"):
            ok(f"player.display_name: {player['display_name']}")
        else:
            warn("player.display_name: not set")

        # Check league section
        league = self.config.get("league", {})
        if league.get("manager_email"):
            ok(f"league.manager_email: {league['manager_email']}")
        else:
            fail("league.manager_email: not set")
            self.errors.append("league.manager_email not set")
            all_ok = False

        # Check app section
        app = self.config.get("app", {})
        if app.get("player_ai_module"):
            ok(f"app.player_ai_module: {app['player_ai_module']}")
        else:
            warn("app.player_ai_module: not set (using default)")

        return all_ok

    def check_gmail(self) -> bool:
        """Check Gmail API connection."""
        header("4. Gmail API")

        token_path = Path(os.getenv("GMAIL_TOKEN_PATH", "token.json"))
        creds_path = Path(os.getenv("GMAIL_CREDENTIALS_PATH", "client_secret.json"))

        if not creds_path.exists():
            fail(f"Credentials not found: {creds_path}")
            return False

        if not token_path.exists():
            warn("Token not found - Gmail not yet authenticated")
            info("Run: python setup_gmail.py")
            self.warnings.append("Gmail not yet authenticated")
            return True  # Not a fatal error

        try:
            from google.oauth2.credentials import Credentials
            from googleapiclient.discovery import build

            SCOPES = [
                "https://www.googleapis.com/auth/gmail.readonly",
                "https://www.googleapis.com/auth/gmail.send",
                "https://www.googleapis.com/auth/gmail.modify",
            ]

            creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)

            if creds.expired:
                warn("Gmail token is expired")
                info("Run: python setup_gmail.py")
                self.warnings.append("Gmail token expired")
                return True

            service = build("gmail", "v1", credentials=creds)
            profile = service.users().getProfile(userId="me").execute()
            email = profile.get("emailAddress", "unknown")

            ok(f"Connected as: {email}")

            # Verify email matches .env
            env_email = os.getenv("GMAIL_ACCOUNT", "")
            if email.lower() != env_email.lower():
                warn(f"Email mismatch: .env has {env_email}")
                self.warnings.append(f"Gmail account mismatch")

            return True

        except ImportError:
            fail("Google API packages not installed")
            info("Run: pip install google-auth-oauthlib google-api-python-client")
            self.errors.append("Missing Google API packages")
            return False
        except Exception as e:
            fail(f"Gmail connection failed: {e}")
            self.errors.append(f"Gmail error: {e}")
            return False

    def check_database(self) -> bool:
        """Check database connection (optional)."""
        header("5. Database")

        host = os.getenv("GTAI_DB_HOST")
        if not host:
            info("Database not configured (optional)")
            return True

        port = os.getenv("GTAI_DB_PORT", "5432")
        name = os.getenv("GTAI_DB_NAME", "gtai_player")
        user = os.getenv("GTAI_DB_USER", "postgres")
        password = os.getenv("GTAI_DB_PASSWORD", "")

        info(f"Connecting to: {user}@{host}:{port}/{name}")

        try:
            import psycopg2

            conn = psycopg2.connect(
                host=host,
                port=int(port),
                dbname=name,
                user=user,
                password=password,
                connect_timeout=5
            )
            conn.close()
            ok("Connection successful")
            return True

        except ImportError:
            warn("psycopg2 not installed - cannot verify database")
            info("Install with: pip install psycopg2-binary")
            self.warnings.append("Cannot verify database")
            return True
        except Exception as e:
            fail(f"Connection failed: {e}")
            self.errors.append(f"Database error: {e}")
            return False

    def check_player_ai(self) -> bool:
        """Check that PlayerAI can be loaded."""
        header("6. PlayerAI")

        # Check for demo mode
        demo_mode = os.getenv("DEMO_MODE", "false").lower() == "true"
        if demo_mode:
            info("Demo mode enabled - using built-in DemoAI")
            ok("DemoAI will be used")
            return True

        module_name = self.config.get("app", {}).get("player_ai_module", "my_player")
        class_name = self.config.get("app", {}).get("player_ai_class", "MyPlayerAI")

        info(f"Loading: {module_name}.{class_name}")

        try:
            module = importlib.import_module(module_name)
            player_class = getattr(module, class_name)
            instance = player_class()

            # Check required methods
            required_methods = ["get_warmup_answer", "get_questions", "get_guess", "on_score_received"]
            missing = [m for m in required_methods if not hasattr(instance, m)]

            if missing:
                fail(f"Missing methods: {', '.join(missing)}")
                self.errors.append(f"PlayerAI missing: {missing}")
                return False

            ok(f"Loaded: {class_name}")
            ok("All required methods present")
            return True

        except ImportError as e:
            fail(f"Cannot import '{module_name}': {e}")
            self.errors.append(f"Cannot import PlayerAI: {e}")
            return False
        except AttributeError:
            fail(f"Class '{class_name}' not found in '{module_name}'")
            self.errors.append(f"PlayerAI class not found")
            return False
        except Exception as e:
            fail(f"Error loading PlayerAI: {e}")
            self.errors.append(f"PlayerAI error: {e}")
            return False

    def run(self) -> bool:
        """Run all verification checks."""
        print("\n" + "=" * 50)
        print("  Q21 Player SDK - Setup Verification")
        print("=" * 50)

        # Load .env first
        self.load_env()

        # Load config
        if Path("js/config.json").exists():
            try:
                with open("js/config.json") as f:
                    self.config = json.load(f)
            except:
                pass

        # Run checks
        self.check_required_files()
        self.check_env_vars()
        self.check_config()
        self.check_gmail()
        self.check_database()
        self.check_player_ai()

        # Summary
        header("Summary")

        if self.errors:
            fail(f"{len(self.errors)} error(s):")
            for error in self.errors:
                print(f"      • {error}")
        else:
            ok("No errors")

        if self.warnings:
            warn(f"{len(self.warnings)} warning(s):")
            for warning in self.warnings:
                print(f"      • {warning}")

        if not self.errors:
            print(f"\n  {Colors.GREEN}{Colors.BOLD}Setup complete!{Colors.RESET}")
            print("\n  You can now run:")
            print("    python run.py --scan --demo   # Test with demo mode")
            print("    python run.py --scan          # Run with your PlayerAI")
        else:
            print(f"\n  {Colors.RED}{Colors.BOLD}Setup incomplete.{Colors.RESET}")
            print("\n  Fix the errors above, then run this script again.")

        print()
        return len(self.errors) == 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify Q21 Player SDK setup")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    args = parser.parse_args()

    verifier = SetupVerifier(verbose=args.verbose)
    return 0 if verifier.run() else 1


if __name__ == "__main__":
    sys.exit(main())
