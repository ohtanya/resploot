#!/usr/bin/env python3
"""
Quick test to see what password PM2 environment actually has
"""

import os
from dotenv import load_dotenv

# Load .env file manually (like the app does)
load_dotenv()

# Get password exactly like the app does
PASSWORD = os.getenv("PINS_VIEWER_PASSWORD", "your_secure_password_here")

print("=== PM2 Environment Test ===")
print(f"Working directory: {os.getcwd()}")
print(f"Password from env: '{PASSWORD}'")
print(f"Expected password: 'NKvFWJs4GjQo1M'")
print(f"Match: {PASSWORD == 'NKvFWJs4GjQo1M'}")

if PASSWORD == "your_secure_password_here":
    print("\n❌ PROBLEM: Still using default password!")
    print("PM2 is not loading the .env file properly.")
    print("\nSolutions:")
    print("1. Set environment variable directly in PM2 config")
    print("2. Use pm2 env command to set variables")
    print("3. Load .env manually in the app")
else:
    print(f"\n✅ Password loaded correctly: '{PASSWORD}'")
    print("The issue must be elsewhere.")