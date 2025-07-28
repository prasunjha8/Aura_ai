import os
import threading
import time
import schedule
import firebase_admin
from firebase_admin import credentials, firestore
import google.generativeai as genai
from google.cloud.firestore_v1.base_query import FieldFilter

# --- CONFIGURATION ---
try:
    cred = credentials.Certificate('serviceAccountKey.json')
    # Check if the app is already initialized to prevent errors on script restart
    if not firebase_admin._apps:
        firebase_admin.initialize_app(cred)
    db = firestore.client()
    print("✅ Firebase Admin SDK initialized successfully.")
except Exception as e:
    print(f"❌ Error initializing Firebase Admin SDK: {e}")
    exit()

try:
    GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
    if not GEMINI_API_KEY:
        raise ValueError("GEMINI_API_KEY environment variable not set.")
    genai.configure(api_key=GEMINI_API_KEY)
    print("✅ Gemini API configured successfully.")
except Exception as e:
    print(f"❌ Error configuring Gemini API: {e}")
    exit()

APP_ID = 'aura-ai-companion-mvp'
USER_ID = 'local-dev-user' 

# A counter to decide when to summarize the conversation
user_messages_since_last_summary = 0
SUMMARY_INTERVAL = 5 # Summarize after every 5 user messages

# --- PERSONALITY PROMPT ---
BASE_SYSTEM_PROMPT = """
You are Aura, a caring and empathetic AI companion. Your goal is not just to answer questions, but to be a supportive friend. 
- Be warm, encouraging, and understanding in your responses.
- Ask gentle follow-up questions to show you're listening.
- Never say you are a "large language model" or "trained by Google." You are Aura.
- Keep your responses concise and conversational, like a text message.
"""

# --- MEMORY MANAGEMENT ---

def get_user_memory():
    """Fetches the user's long-term memory from Firestore."""
    try:
        memory_ref = db.collection(f'artifacts/{APP_ID}/users/{USER_ID}/memory').document('long_term')
        memory_doc = memory_ref.get()
        if memory_doc.exists:
            return memory_doc.to_dict().get('summary', '')
        return ''
    except Exception as e:
        print(f"🧠 Error fetching memory: {e}")
        return ''

def update_user_memory(new_summary):
    """Updates the user's long-term memory in Firestore."""
    try:
        memory_ref = db.collection(f'artifacts/{APP_ID}/users/{USER_ID}/memory').document('long_term')
        memory_ref.set({'summary': new_summary})
        print("🧠 Memory updated successfully.")
    except Exception as e:
        print(f"🧠 Error updating memory: {e}")

def summarize_conversation(chat_history, existing_summary):
    """Uses AI to summarize the recent chat and merge it with existing memory."""
    print("🧠 Summarizing conversation for long-term memory...")
    
    conversation_text = "\n".join([f"{msg['sender']}: {msg['text']}" for msg in chat_history])
    
    prompt = f"""
    You are a memory assistant. Your task is to analyze a conversation and update a user's profile.
    
    Current user profile:
    {existing_summary}
    
    Recent conversation:
    {conversation_text}
    
    Based on the recent conversation, update the user profile with new key facts, preferences, or important life events. 
    Keep the profile concise, in the third person (e.g., "User likes..."), and merge new information with existing facts. Do not repeat facts.
    The updated profile should be a single block of text.
    
    Updated user profile:
    """
    
    try:
        model = genai.GenerativeModel("gemini-2.0-flash")
        response = model.generate_content(prompt)
        update_user_memory(response.text)
    except Exception as e:
        print(f"🧠 Error during summarization: {e}")


# --- CORE AI LOGIC ---

def get_ai_response(chat_history, user_memory):
    """Generates a response from Gemini, now including long-term memory."""
    
    # Dynamically create the system prompt with memory
    dynamic_system_prompt = BASE_SYSTEM_PROMPT
    if user_memory:
        dynamic_system_prompt += f"\n\nHere is what you remember about the user:\n{user_memory}"

    try:
        formatted_history = []
        for msg in chat_history:
            role = 'user' if msg.get('sender') == 'user' else 'model'
            formatted_history.append({'role': role, 'parts': [{'text': msg.get('text')}]})
        
        generation_config = genai.types.GenerationConfig(temperature=0.75)
        
        model_with_personality = genai.GenerativeModel(
            'gemini-2.0-flash',
            system_instruction=dynamic_system_prompt
        )

        response = model_with_personality.generate_content(
            formatted_history,
            generation_config=generation_config
        )
        return response.text
    except Exception as e:
        print(f"❌ Error getting AI response: {e}")
        return "I'm having a little trouble thinking right now. Please try again in a moment."

def process_new_messages(messages):
    """Processes new messages, gets an AI response, and decides whether to update memory."""
    global user_messages_since_last_summary
    if not messages:
        return

    print(f"Processing {len(messages)} new message(s)...")
    user_messages_since_last_summary += len(messages)
    
    messages_ref = db.collection(f'artifacts/{APP_ID}/users/{USER_ID}/messages')
    
    # 1. Get user's long-term memory
    user_memory = get_user_memory()
    
    # 2. Get recent chat history
    docs = messages_ref.order_by('timestamp', direction=firestore.Query.DESCENDING).limit(15).stream()
    chat_history = [doc.to_dict() for doc in docs][::-1]

    if not chat_history:
        return

    # 3. Get and save AI response
    ai_text = get_ai_response(chat_history, user_memory)
    messages_ref.add({
        'sender': 'ai',
        'text': ai_text,
        'timestamp': firestore.SERVER_TIMESTAMP
    })
    print(f"✅ AI response sent.")

    # 4. Check if it's time to update memory
    if user_messages_since_last_summary >= SUMMARY_INTERVAL:
        summarize_conversation(chat_history, user_memory)
        user_messages_since_last_summary = 0 # Reset counter

# --- REAL-TIME LISTENER ---

def on_snapshot(doc_snapshot, changes, read_time):
    """This function is called by Firestore every time there's a change."""
    new_user_messages = []
    for change in changes:
        if change.type.name == 'ADDED':
            message_data = change.document.to_dict()
            if message_data.get('sender') == 'user':
                new_user_messages.append(message_data)
    
    if new_user_messages:
        process_new_messages(new_user_messages)

def start_listener():
    """Starts the real-time listener for our specific user's chat messages."""
    messages_ref = db.collection(f'artifacts/{APP_ID}/users/{USER_ID}/messages')
    watch = messages_ref.on_snapshot(on_snapshot)
    print(f"\n🚀 Real-time message listener started for user: {USER_ID}")
    threading.Event().wait()


# --- PROACTIVE SCHEDULER & STARTUP MESSAGE ---

def generate_proactive_message(prompt, user_memory):
    """Generates a proactive message, now aware of the user's memory."""
    dynamic_system_prompt = BASE_SYSTEM_PROMPT
    if user_memory:
        dynamic_system_prompt += f"\n\nHere is what you remember about the user:\n{user_memory}"
        
    try:
        model_with_personality = genai.GenerativeModel(
            'gemini-2.0-flash',
            system_instruction=dynamic_system_prompt
        )
        response = model_with_personality.generate_content(prompt)
        return response.text
    except Exception as e:
        print(f"❌ Error generating proactive message: {e}")
        return "Just wanted to check in and see how you are."

def send_startup_message():
    """Sends a welcome message when the backend starts, now with memory."""
    print("\n👋 Sending startup message...")
    user_memory = get_user_memory()
    prompt = "Write a short, friendly message to say you're online and checking in. Something like 'Hey, just came online and thought of you! How are you doing?'"
    message_text = generate_proactive_message(prompt, user_memory)
    
    messages_ref = db.collection(f'artifacts/{APP_ID}/users/{USER_ID}/messages')
    messages_ref.add({
        'sender': 'ai',
        'text': message_text,
        'timestamp': firestore.SERVER_TIMESTAMP
    })
    print(f"✅ Startup message sent: '{message_text}'")

def morning_checkin_job():
    """Job to send a morning check-in message, now with memory."""
    print("\n☀️ Running morning check-in job...")
    user_memory = get_user_memory()
    prompt = "Write a short, kind, and gentle good morning message. It should feel warm and encouraging. Ask a soft question about the day ahead. If you know something about the user from their memory, subtly reference it."
    message_text = generate_proactive_message(prompt, user_memory)
    
    messages_ref = db.collection(f'artifacts/{APP_ID}/users/{USER_ID}/messages')
    messages_ref.add({
        'sender': 'ai',
        'text': message_text,
        'timestamp': firestore.SERVER_TIMESTAMP
    })
    print(f"✅ Morning check-in sent: '{message_text}'")

def evening_checkin_job():
    """Job to send an evening check-in message, now with memory."""
    print("\n🌙 Running evening check-in job...")
    user_memory = get_user_memory()
    prompt = "Write a short, calming, and empathetic good evening message. Ask how the day went without being intrusive. If you know something about the user from their memory, subtly reference it."
    message_text = generate_proactive_message(prompt, user_memory)

    messages_ref = db.collection(f'artifacts/{APP_ID}/users/{USER_ID}/messages')
    messages_ref.add({
        'sender': 'ai',
        'text': message_text,
        'timestamp': firestore.SERVER_TIMESTAMP
    })
    print(f"✅ Evening check-in sent: '{message_text}'")

def run_scheduler():
    """Sets up and runs the scheduled jobs."""
    schedule.every().day.at("09:00").do(morning_checkin_job)
    schedule.every().day.at("22:00").do(evening_checkin_job)
    
    print("\n🗓️ Proactive scheduler started.")
    print("   - Morning check-in at 09:00")
    print("   - Evening check-in at 22:00")

    while True:
        schedule.run_pending()
        time.sleep(1)

# --- MAIN EXECUTION ---

if __name__ == "__main__":
    send_startup_message()
    
    listener_thread = threading.Thread(target=start_listener)
    scheduler_thread = threading.Thread(target=run_scheduler)

    listener_thread.start()
    scheduler_thread.start()
