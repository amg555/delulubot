<div align="center">

<img src="https://img.shields.io/badge/Version-4.0_(Multi--Provider)-FF6B35?style=for-the-badge&logo=groq&logoColor=white" alt="Version Badge"/>
<img src="https://img.shields.io/badge/Platform-Telegram-26A5E4?style=for-the-badge&logo=telegram&logoColor=white" alt="Telegram Badge"/>
<img src="https://img.shields.io/badge/Language-Python-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python Badge"/>


<h1 align="center">🤖 Delulubot</h1>
<h3 align="center">Your Sassy Manglish AI Companion on Telegram</h3>

<p align="center">
  100% free-tier conversational AI bot — Groq (primary chat) + Jina (embeddings) + Gemini (fallback). Featuring RAG-based personality grounding, voice interactions, and persistent long-term memory.
</p>

<p align="center">
  <a href="#-features">Features</a> •
  <a href="#-tech-stack">Tech Stack</a> •
  <a href="#-installation">Installation</a> •
  <a href="#-configuration">Configuration</a> •
  <a href="#-deployment">Deployment</a> •
  <a href="#-license">License</a>
</p>
</div>

---

## 🌟 Overview

**Delulubot v4.0** is not just another chatbot; it is a digital persona. Designed to mimic "Delulu," a 23-year-old sassy girl, the bot communicates in **Manglish (Malayalam + English)** for a realistic, human-like texting experience.

Built on a **multi-provider free-tier architecture**, it uses **Groq** (via OpenAI-compatible API) as the primary chat provider, **Jina AI** for text embeddings (RAG), and **Google Gemini** as a fallback chat provider. This ensures 100% free operation without requiring any credit card.

## ✨ Features

| Feature | Description |
| :--- | :--- |
| 🧠 **RAG Architecture** | Grounds the bot in custom knowledge bases (Markdown/TXT/JSON) using Jina AI embeddings, ensuring accurate lore and personality consistency. |
| 🗣️ **Voice Interaction** | **STT:** High-speed transcription via `faster-whisper`.<br>**TTS:** Premium neural voices via `edge-tts` (or fallback to `gTTS`). |
| 🧘 **Persistent Memory** | Remembers user preferences, facts, and conversation history (`user_memories.json`) for personalized interactions. |
| 🛡️ **Personality Guard** | Advanced system prompts prevent character breaks, ensuring Delulu never leaves her persona. |
| ⚡ **Multi-Provider Fallbacks** | Groq (primary) → Gemini (fallback) — seamless failover with Jina embedding key rotation across multiple API keys. |

## 🛠️ Tech Stack

-   **Core Logic:** Python 3.9+
-   **Primary Chat:** Groq (llama-3.3-70b-versatile) via OpenAI-compatible SDK
-   **Embeddings:** Jina AI (jina-embeddings-v3) with round-robin key rotation
-   **Fallback Chat:** Google Gemini (gemini-2.0-flash-lite)
-   **Bot Framework:** `python-telegram-bot`
-   **Voice Processing:** `faster-whisper`, `edge-tts`, `gTTS`
-   **Environment Management:** `python-dotenv`
-   **Health Monitoring:** UptimeRobot + built-in HTTP healthcheck endpoint

## 🚀 Installation

Follow these steps to get Delulubot running locally.

### Prerequisites
- Python 3.9 or higher
- A Telegram Bot Token (from [@BotFather](https://t.me/botfather))
- A Groq API Key (from [Groq Console](https://console.groq.com))
- A Jina AI API Key (from [Jina AI](https://jina.ai/)) — 3 keys recommended for rotation
- (Optional) A Google AI Studio API Key for fallback (from [Google AI Studio](https://aistudio.google.com/))

### Step 1: Clone the Repository
```bash
git clone https://github.com/yourusername/delulubot.git
cd delulubot
```

### Step 2: Create a Virtual Environment
```bash
python -m venv venv
# On Windows:
venv\Scripts\activate
# On Linux/macOS:
source venv/bin/activate
```

### Step 3: Install Dependencies
```bash
pip install -r requirements.txt
```

### Step 4: Configuration
Create a `.env` file in the root directory based on the `.env.example`.

## ⚙️ Configuration

Environment variables are crucial for the bot's operation. Create a `.env` file with the following keys:

```env
# Telegram Configuration
TELEGRAM_TOKEN=your_telegram_bot_token_here

# Groq (primary chat provider - free tier, no credit card)
GROQ_API_KEY=your_groq_api_key_here
GROQ_MODEL=llama-3.3-70b-versatile

# Gemini (fallback chat - only used when Groq is down/rate-limited)
GEMINI_API_KEY=your_gemini_api_key_here
GEMINI_MODEL=gemini-2.0-flash-lite

# Jina (embeddings for RAG - add multiple keys comma-separated for rotation)
JINA_API_KEYS=key1,key2,key3
JINA_MODEL=jina-embeddings-v3

# RAG & Personality
RAG_ENABLED=true
RAG_DIR=rag_data
CHARACTER_BIBLE_FILE=rag_data/delulu_character_bible.md

# Voice Settings
VOICE_TTS_ENGINE=auto
VOICE_TRANSCRIBE_MODEL=base
```

## 🏃 Usage

Once configured, start the bot with:

```bash
python delulu_bot.py
```

Interact with the bot on Telegram:
- **Text:** Send a message to receive a Manglish reply.
- **Voice:** Send a voice note; Delulu will transcribe it and reply with voice/audio.
- **Commands:** Use `/start`, `/aboutme`, `/companion`, `/status`, etc.

## 🚢 Deployment

Delulubot is designed to run on **Render's free plan** (512 MB RAM). The bot automatically starts a healthcheck HTTP server on the `$PORT` environment variable. Use **UptimeRobot** to ping the healthcheck endpoint every 5 minutes to prevent the free tier from sleeping.

## 📁 Project Structure

```
delulubot/
├── rag_data/                # Knowledge base & Character lore
├── .env                     # Environment variables (Not committed)
├── .env.example             # Template for configuration
├── delulu_bot.py            # Main application script
├── requirements.txt         # Python dependencies
├── user_memories.json       # Persistent user data
└── README.md                # Documentation
```

## 🤝 Contributing

Contributions are welcome! Whether it's adding new features, improving the personality prompts, or fixing bugs, please feel free to fork the repo and submit a pull request.


---

<div align="center">
  Made with ❤️ and a touch of Delulu ✨
</div>
