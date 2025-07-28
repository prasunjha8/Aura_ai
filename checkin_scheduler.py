# checkin_scheduler.py
# This script runs in the background on a server to send proactive messages to all users.

import os
import time
import schedule
import firebase_admin
from firebase_admin import credentials, firestore
import google.generativeai as genai

# --- CONFIGURATION ---

# IMPORTANT: Firebase Admin SDK Setup
# 1. Go to your Firebase project settings -> Service accounts.
# 2. Click "Generate new private key" and download the JSON file.
# 3. Save this file as 'serviceAccountKey.json' in the same directory as this script.
# 4. For production, it's better to set the path as an environment variable.
try:
    cred = credentials.Certificate('serviceAccountKey.json')
    firebase_admin.initialize_app(cred)
    db = firestore.client()
    print("Firebase Admin SDK initialized successfully.")
except Exception as e:
    print(f"Error initializing Firebase Admin SDK: {e}")
    print("Please ensure 'serviceAccountKey.json' is in the correct directory.")
    # Exit if we can't connect to Firebase
    exit()


# IMPORTANT: Gemini API Key Setup
# Set your Gemini API key as an environment variable for security.
# On your terminal (Linux/macOS): export GEMINI_API_KEY='your_api_key_here'
# On Windows (Command Prompt): set GEMINI_API_KEY=your_api_key_here
# On Windows (PowerShell): $env:GEMINI_API_KEY="your_api_key_here"
try:
    GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
    if not GEMINI_API_KEY:
        raise ValueError("GEMINI_API_KEY environment variable not set.")
    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel("gemini-pro")
    print("Gemini API configured successfully.")
except Exception as e:
    print(f"Error configuring Gemini API: {e}")
    # Exit if we can't configure the AI model
    exit()

# The App ID should match the one used in your frontend code.
APP_ID = 'aura-ai-companion-mvp'


def get_all_user_ids():
    """
    Fetches all unique user IDs from the 'users' collection within the app's artifact.
    """
    try:
        users_ref = db.collection(f'artifacts/{APP_ID}/users')
        users = users_ref.stream()
        user_ids = [user.id for user in users]
        print(f"Found {len(user_ids)} users: {user_ids}")
        return user_ids
    except Exception as e:
        print(f"An error occurred while fetching user IDs: {e}")
        return []

def generate_proactive_message(prompt):
    """
    Uses the Gemini API to generate a thoughtful, proactive message.
    """
    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        print(f"Error generating message from Gemini: {e}")
        return "Just checking in on you. Hope you're having a good day."


def send_checkin_message_to_user(user_id, prompt):
    """
    Generates a proactive message and adds it to a specific user's chat in Firestore.
    """
    if not user_id:
        return

    print(f"Generating message for user: {user_id}...")
    message_text = generate_proactive_message(prompt)

    try:
        messages_collection_ref = db.collection(f'artifacts/{APP_ID}/users/{user_id}/messages')
        messages_collection_ref.add({
            'sender': 'ai',
            'text': message_text,
            'timestamp': firestore.SERVER_TIMESTAMP
        })
        print(f"Successfully sent message to {user_id}: '{message_text}'")
    except Exception as e:
        print(f"Failed to send message to {user_id}: {e}")


def morning_checkin_job():
    """
    Job to send a morning check-in to all users.
    """
    print("\n--- Running Morning Check-in Job ---")
    user_ids = get_all_user_ids()
    prompt = "Write a short, kind, and gentle good morning message. It should feel warm and encouraging, like it's from a close friend who genuinely cares. Ask a soft question about the day ahead."
    for user_id in user_ids:
        send_checkin_message_to_user(user_id, prompt)
    print("--- Morning Check-in Job Finished ---\n")


def evening_checkin_job():
    """
    Job to send an evening check-in to all users.
    """
    print("\n--- Running Evening Check-in Job ---")
    user_ids = get_all_user_ids()
    prompt = "Write a short, calming, and empathetic good evening message. It should be a gentle prompt for reflection, asking how the day went without being intrusive. The tone should be like a safe space to unwind."
    for user_id in user_ids:
        send_checkin_message_to_user(user_id, prompt)
    print("--- Evening Check-in Job Finished ---\n")


# --- SCHEDULING ---
# The times are set in the server's local time.
# Since you're in India (IST), these times will correspond to IST if the server is also in that timezone.
# For a production server, you might want to use UTC and convert.

# Schedule the morning job for 9:00 AM
schedule.every().day.at("09:00").do(morning_checkin_job)

# Schedule the evening job for 10:00 PM (22:00)
schedule.every().day.at("22:00").do(evening_checkin_job)

print("Scheduler started. Waiting for scheduled jobs...")
print(f"Morning check-in scheduled for 09:00.")
print(f"Evening check-in scheduled for 22:00.")


# --- MAIN LOOP ---
# This loop runs forever, checking every second if a scheduled job is due to run.
while True:
    schedule.run_pending()
    time.sleep(1)

