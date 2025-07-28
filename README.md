# Aura - Your Proactive AI Wellness Companion

Aura is a proof-of-concept AI chat application built to explore the idea of a proactive, emotionally aware digital companion. Born from the insight that most AI assistants are reactive, Aura is designed to take the initiative—checking in, remembering conversations, and fostering a genuine sense of connection.

This project is more than just a chatbot; it's an exploration into creating an AI that provides a sense of being cared for, aiming to combat loneliness and provide accessible, 24/7 emotional support.

## Core Features (Current Version)

- **Real-time Chat Interface:** A sleek, self-contained web interface (`index.html`) for seamless conversation.
- **Persistent Conversations:** All chat history is securely stored in Google Firestore, so conversations are never lost on refresh.
- **AI with a Personality:** Aura's persona is defined by a robust `SYSTEM_PROMPT`, making her an empathetic and supportive friend, not just a generic language model.
- **Proactive Check-ins:** The backend automatically sends a friendly "good morning" and "good evening" message every day, fulfilling the core mission of the project.
- **Long-Term Memory:** Aura summarizes conversations every 5 user messages, building a long-term memory of key facts about the user. This memory is used in future conversations to make them more personal and context-aware.

## How It Works: The Architecture

Aura uses a decoupled frontend/backend architecture connected by a real-time database.

1.  **Frontend (`index.html`):** A single HTML file with embedded CSS and JavaScript.
    -   **Responsibilities:** Displaying the chat history and sending user messages to the database.
    -   It has no direct knowledge of the AI. It only communicates with Firestore.

2.  **Backend (`backend_listener.py`):** A persistent Python script that runs on a server or locally.
    -   **Responsibilities:**
        -   Listens in real-time for new user messages in the database.
        -   Gathers chat history and long-term memory.
        -   Injects the `SYSTEM_PROMPT` to define Aura's personality.
        -   Sends the context to the Google Gemini API to generate a response.
        -   Saves the AI's response back to the database.
        -   Runs a scheduler for proactive daily check-ins.
        -   Periodically summarizes the conversation to update Aura's long-term memory.

3.  **Google Firestore (The Database):** Acts as the central message bus and memory storage.
    -   **Responsibilities:**
        -   Stores all chat messages in real-time.
        -   Stores Aura's long-term memory summary for the user.
        -   Instantly syncs data between the frontend and backend.

## How to Set Up and Run

### Prerequisites

-   Python 3.10+
-   A Google Firebase project
-   A Google Gemini API Key

### 1. Firebase Setup

1.  Create a new project in the [Firebase Console](https://console.firebase.google.com/).
2.  **Add a Web App:** In your project dashboard, add a new Web App. Copy the `firebaseConfig` object provided.
3.  **Enable Firestore:** Go to the "Firestore Database" section, create a database in "Production mode," and choose a location.
4.  **Update Firestore Rules:** In the "Rules" tab of Firestore, paste the following and publish:
    ```
    rules_version = '2';
    service cloud.firestore {
      match /databases/{database}/documents {
        match /artifacts/{appId}/users/local-dev-user/{document=**} {
          allow read, write: if true;
        }
      }
    }
    ```
5.  **Download Service Account Key:** In Project Settings > Service Accounts, generate a new private key and save the downloaded file as `serviceAccountKey.json` in your project's root directory.

### 2. Google Cloud & Gemini Setup

1.  **Enable APIs:** Ensure the **Generative Language API** and **Identity Toolkit API** are enabled for your project in the Google Cloud Console.
2.  **Get Gemini API Key:** Create an API key in the [Google AI Studio](https://aistudio.google.com/app/apikey).

### 3. Local Setup

1.  **Clone the Repository:**
    ```bash
    git clone [your-repo-url]
    cd [your-repo-name]
    ```
2.  **Update Frontend Config:** Open `index.html` and replace the placeholder `firebaseConfig` object with the one you copied from your Firebase project.
3.  **Create `requirements.txt`:** Create a file named `requirements.txt` and add the following:
    ```text
    firebase-admin==6.5.0
    google-generativeai==0.5.4
    protobuf==4.25.3
    schedule
    ```
4.  **Install Python Dependencies:**
    ```bash
    pip install -r requirements.txt
    ```
5.  **Set Environment Variable:** In your terminal, set your Gemini API key (this is required for each new terminal session):
    ```bash
    export GEMINI_API_KEY='YOUR_GEMINI_API_KEY_HERE'
    ```

### 4. Running the App

You need to have two things running simultaneously:

1.  **Run the Backend:** Open a terminal and start the listener.
    ```bash
    python backend_listener.py
    ```
2.  **Run the Frontend:** Open the `index.html` file in your web browser.

You can now start chatting with your own personal, proactive AI companion!
