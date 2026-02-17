#!/usr/bin/env python3
"""Database initialization script for Q21 Player SDK.

Creates all required database tables.

Usage:
    python init_db.py           # Initialize schema
    python init_db.py --reset   # Reset schema (WARNING: deletes all data)
    python init_db.py --test    # Test connection only
"""
import argparse
import sys


def main():
    parser = argparse.ArgumentParser(description="Initialize Q21 Player database")
    parser.add_argument("--reset", "-r", action="store_true",
                        help="Reset schema (WARNING: deletes all data)")
    parser.add_argument("--test", "-t", action="store_true",
                        help="Test connection only")
    args = parser.parse_args()

    print("=" * 50)
    print("  Q21 Player SDK - Database Initialization")
    print("=" * 50)

    try:
        from q21_player._infra.database.pool import ConnectionPool
        from q21_player._infra.database.manager import DatabaseManager
    except ImportError:
        print("\nError: q21_player package not installed.")
        print("Run: pip install dist/q21_player-1.0.0-py3-none-any.whl")
        return 1

    # Test connection
    print("\n1. Testing database connection...")
    try:
        pool = ConnectionPool()
        if pool.test_connection():
            print("   ✓ Connection successful")
        else:
            print("   ✗ Connection failed")
            return 1
    except Exception as e:
        print(f"   ✗ Connection error: {e}")
        return 1

    if args.test:
        print("\n" + "=" * 50)
        print("  Connection test completed")
        print("=" * 50)
        return 0

    # Initialize or reset schema
    manager = DatabaseManager(pool)

    if args.reset:
        print("\n2. Resetting database schema...")
        confirm = input("   This will DELETE all data. Type 'yes' to confirm: ")
        if confirm.lower() != "yes":
            print("   Reset cancelled")
            return 0
        try:
            manager.reset_schema()
            print("   ✓ Schema reset complete")
        except Exception as e:
            print(f"   ✗ Reset failed: {e}")
            return 1
    else:
        print("\n2. Initializing database schema...")
        try:
            manager.init_schema()
            print("   ✓ Schema initialized")
        except Exception as e:
            print(f"   ✗ Initialization failed: {e}")
            return 1

    # Show results
    version = manager.get_schema_version()
    tables = manager.get_table_names()

    print(f"\n   Schema version: {version}")
    print(f"   Tables created: {len(tables)}")

    if tables:
        print("\n   Tables:")
        for t in sorted(tables):
            print(f"     • {t}")

    print("\n" + "=" * 50)
    print("  Database initialization successful!")
    print("=" * 50)
    return 0


if __name__ == "__main__":
    sys.exit(main())
