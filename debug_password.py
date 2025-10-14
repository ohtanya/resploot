#!/usr/bin/env python3
"""
Debug script to check pins viewer password configuration
"""

import os
from dotenv import load_dotenv

print("Pins Viewer Password Debug")
print("=" * 30)

# Load environment variables
load_dotenv()

# Check what the app sees
password_from_env = os.getenv("PINS_VIEWER_PASSWORD", "your_secure_password_here")
flask_secret = os.getenv("FLASK_SECRET_KEY", "change_this_secret_key_for_flask_sessions")

print(f"Current working directory: {os.getcwd()}")
print(f"Looking for .env file at: {os.path.join(os.getcwd(), '.env')}")
print(f".env file exists: {os.path.exists('.env')}")

if os.path.exists('.env'):
    print("\n.env file contents:")
    with open('.env', 'r') as f:
        for i, line in enumerate(f, 1):
            if 'PASSWORD' in line:
                print(f"Line {i}: {line.strip()}")

print(f"\nEnvironment variables:")
print(f"PINS_VIEWER_PASSWORD = '{password_from_env}'")
print(f"FLASK_SECRET_KEY = '{flask_secret[:20]}...' (truncated)")

print(f"\nPassword that would be used by pins viewer: '{password_from_env}'")
print(f"Expected password from your .env: 'NKvFWJs4GjQo1M'")
print(f"Passwords match: {password_from_env == 'NKvFWJs4GjQo1M'}")

# Check for common issues
if password_from_env == "your_secure_password_here":
    print("\n❌ ISSUE: Using default password! .env file not loaded properly.")
elif password_from_env != 'NKvFWJs4GjQo1M':
    print(f"\n❌ ISSUE: Password mismatch!")
    print(f"   Expected: 'NKvFWJs4GjQo1M'")
    print(f"   Got:      '{password_from_env}'")
    print(f"   Length difference: {len('NKvFWJs4GjQo1M')} vs {len(password_from_env)}")
else:
    print("\n✅ Password configuration looks correct!")