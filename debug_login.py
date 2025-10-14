#!/usr/bin/env python3
"""
Advanced debug script to check login process
"""

import os
from dotenv import load_dotenv

print("Advanced Pins Viewer Login Debug")
print("=" * 40)

# Load environment variables
load_dotenv()

# Get the password the app would use
app_password = os.getenv("PINS_VIEWER_PASSWORD", "your_secure_password_here")

print(f"App password: '{app_password}'")
print(f"App password length: {len(app_password)}")
print(f"App password bytes: {app_password.encode('utf-8')}")

# Test different variations you might be typing
test_passwords = [
    "NKvFWJs4GjQo1M",  # Expected
    "NKvFWJs4GjQo1M ",  # With trailing space
    " NKvFWJs4GjQo1M",  # With leading space
    "nkvfwjs4gjqo1m",   # Lowercase
    "NKVFWJS4GJQO1M",   # Uppercase
]

print(f"\nTesting different password variations:")
for i, test_pw in enumerate(test_passwords, 1):
    match = test_pw == app_password
    print(f"{i}. '{test_pw}' -> {match}")
    if match:
        print(f"   ✅ This password works!")

# Check for invisible characters
print(f"\nChecking for invisible characters:")
for i, char in enumerate(app_password):
    print(f"Position {i}: '{char}' (ASCII: {ord(char)})")

print(f"\nPassword analysis:")
print(f"- Contains only printable chars: {app_password.isprintable()}")
print(f"- Starts/ends with whitespace: {app_password != app_password.strip()}")

# Simulate the Flask comparison
print(f"\nSimulating Flask login comparison:")
user_input = "NKvFWJs4GjQo1M"  # What you're typing
comparison_result = user_input == app_password
print(f"'{user_input}' == '{app_password}' -> {comparison_result}")

if not comparison_result:
    print("\n❌ PROBLEM FOUND!")
    print("The passwords don't match. Possible causes:")
    print("1. Hidden characters in .env file")
    print("2. Copy/paste introduced special characters")
    print("3. Different encoding")
    
    print(f"\nDetailed comparison:")
    print(f"Expected: {repr(user_input)}")
    print(f"Got:      {repr(app_password)}")
else:
    print("\n✅ Password comparison should work!")
    print("The issue might be:")
    print("1. Browser caching")
    print("2. PM2 not restarted after .env changes")
    print("3. Typing the wrong password")