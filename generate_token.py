# generate_token.py
# This script runs only ONCE to create a custom login token for local testing.

import os
import firebase_admin
from firebase_admin import credentials, auth

# --- CONFIGURATION ---
try:
    cred = credentials.Certificate('serviceAccountKey.json')
    firebase_admin.initialize_app(cred)
    print("✅ Firebase Admin SDK initialized successfully.")
except Exception as e:
    print(f"❌ Error initializing Firebase Admin SDK: {e}")
    exit()

# --- TOKEN GENERATION ---
# We will create a token for a specific, predictable user ID.
# This makes testing consistent.
USER_ID = 'local-dev-user'

try:
    # Generate the custom token
    custom_token = auth.create_custom_token(USER_ID)
    print("\n✅ Custom Token Generated Successfully!")
    print("\n--- COPY THE TOKEN BELOW ---")
    print(custom_token)
    print("\n--- PASTE IT INTO YOUR index.html FILE ---")

except Exception as e:
    print(f"❌ Error generating custom token: {e}")

