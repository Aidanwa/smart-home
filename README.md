# Smart Home

Agentic Smart Home Assistant

An experimental **agentic smart home automation system** that uses LLMs to orchestrate tool usage for home automation tasks. It supports both **local-first operation (Ollama)** and **cloud-based reasoning (OpenAI)** with optional voice I/O.

---

## Project Overview

**Smart Home** is a modular agent framework that combines natural language interaction with intelligent tool orchestration. Agents can reason about your environment, call specialized tools (weather forecasts, Spotify control, and more), and respond through text or voice.

The system is designed for **privacy** (runs fully offline), **extensibility** (easy to add new agents and tools), and **experimentation** with agentic automation patterns.

---

## Features

- **Agent Framework**: Core `Agent` class with conversation state management and tool execution
- **Tool System**: Base `Tool` class with provider-specific schema generation for extensibility
- **Multiple Agents**: Weather, Spotify, and Home agents with specialized capabilities
- **Voice Integration**: Speech-to-text (Vosk) and text-to-speech (pyttsx3) for hands-free interaction
- **Dual Backends**: OpenAI Responses API (cloud) or Ollama (local) with automatic fallback
- **Streaming Responses**: Real-time token streaming with tool-calling loop support
- **Advanced Weather**: Time-aware forecasting with granular (hourly/daily) control via weather.gov API
- **Spotify Integration**: Playback control, device switching, and volume management

---

## Setup

### 1. Clone and enter the project
```bash
git clone https://github.com/yourusername/smart-home.git
cd smart-home
```

### 2. Install dependencies

This project uses [uv](https://github.com/astral-sh/uv) for dependency management:

```bash
uv sync
```

Alternatively, install with pip:
```bash
pip install -e .
```

### 3. Configure environment

Copy the example environment file:
```bash
cp .env.example .env
```

Edit `.env` with your settings:

```bash
# Backend selection
PROVIDER=ollama              # Options: 'ollama' or 'openai'

# For OpenAI (cloud mode):
OPENAI_API_KEY=sk-...        # Your OpenAI API key
OPENAI_MODEL=gpt-4o-mini     # Model to use

# For Ollama (local mode):
OLLAMA_URL=http://localhost:11434

# Location settings (required for WeatherTool)
HOME_COORDS=38.8977,-77.0365           # Your latitude,longitude
HOME_GRID=LWX/87,68                    # From weather.gov API
TIMEZONE=America/New_York

# Spotify integration (optional)
SPOTIFY_CLIENT_ID=...
SPOTIFY_CLIENT_SECRET=...
SPOTIFY_REFRESH_TOKEN=...              # Get via OAuth flow

# Voice settings (optional)
SPEECH_TO_TEXT=False         # Enable microphone input
TEXT_TO_SPEECH=False         # Enable spoken output
```

**Getting Weather Grid Coordinates:**
1. Visit `https://api.weather.gov/points/{YOUR_LAT},{YOUR_LON}`
2. Extract `gridId` and `gridX,gridY` from the response
3. Format as `HOME_GRID=GRID_ID/GRID_X,GRID_Y`

---

## Running the Application

### Standard mode (text-based interaction)

```bash
uv run python src/smart_home/driver.py
```

The application will prompt you to select an agent:
- **weather**: Weather forecasts and climate queries
- **spotify**: Music playback control (requires Spotify Premium)
- **home**: General-purpose assistant combining weather and Spotify

Example interactions:
```
Select agent (weather/spotify/home): weather
You: What's the forecast for tomorrow afternoon?
Assistant: Tomorrow afternoon will be partly cloudy with temperatures around 72°F...

You: exit
```

---

## Backend Configuration

### Using Ollama (Local/Offline Mode)

Ollama provides fast, private local LLM inference with no API costs.

**Installation:**
```bash
curl -fsSL https://ollama.com/install.sh | sh
ollama pull llama3.1:8b
```

Ollama runs automatically as a background service on `http://localhost:11434`.

**Verify it's running:**
```bash
curl http://localhost:11434/api/tags
```

Set in `.env`:
```bash
PROVIDER=ollama
OLLAMA_URL=http://localhost:11434
```

### Using OpenAI (Cloud Mode)

For improved reasoning and access to larger models:

1. Get an API key from [OpenAI Platform](https://platform.openai.com/)
2. Add to `.env`:
```bash
PROVIDER=openai
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o-mini
```

The agent will stream responses through the **Responses API** with real-time function calling.

---

## Optional: Voice Integration

### Speech-to-Text (Vosk)

Download the English Vosk model from [alphacephei.com/vosk/models](https://alphacephei.com/vosk/models).

Recommended: `vosk-model-small-en-us-0.15` (40MB)

**Setup:**
```bash
# Create models directory
mkdir -p models

# Download and extract (example for small English model)
cd models
wget https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.zip
unzip vosk-model-small-en-us-0.15.zip
cd ..
```

Directory structure:
```
smart-home/
├── models/
│   └── vosk-model-small-en-us-0.15/
└── src/
```

Enable in `.env`:
```bash
SPEECH_TO_TEXT=True
TEXT_TO_SPEECH=True
```

### Text-to-Speech

Uses system TTS engines (pyttsx3):
- Windows: SAPI5
- macOS: NSSpeechSynthesizer
- Linux: espeak

No additional setup required.

---

## Technology Stack

**Core:**
- Python 3.11+
- [uv](https://github.com/astral-sh/uv) - Fast Python package manager
- Ollama (Llama 3.1 8B) - Local LLM inference
- OpenAI Responses API - Cloud-based reasoning

**Integrations:**
- [weather.gov API](https://weather.gov) - National Weather Service forecasts
- [Spotify Web API](https://developer.spotify.com/documentation/web-api) - Music playback control
- [Vosk](https://alphacephei.com/vosk/) - Offline speech recognition
- [pyttsx3](https://pyttsx3.readthedocs.io/) - Text-to-speech synthesis

**Framework:**
- Custom agent framework with tool orchestration
- SSE (Server-Sent Events) streaming for OpenAI
- JSON streaming for Ollama

---

## Project Structure

```
smart-home/
├── src/smart_home/
│   ├── core/
│   │   ├── agent.py          # Core Agent and Tool classes
│   │   └── sse.py            # SSE parser for OpenAI streaming
│   ├── agents/
│   │   ├── weather.py        # Weather-focused agent
│   │   ├── spotify.py        # Spotify control agent
│   │   └── home.py           # General-purpose home agent
│   ├── tools/
│   │   ├── weather/          # Weather.gov API integration
│   │   └── spotify/          # Spotify Web API tools
│   ├── config/
│   │   └── paths.py          # Path configuration
│   └── utils/
│       └── voice_utils.py    # Speech I/O utilities
├── models/                   # Voice models directory
├── data/                     # Logs and cache
└── docs/
    └── ROADMAP.md           # Future plans and ideas
```

---

## Contributing

This is a personal experimental project, but feedback and ideas are welcome!

See [docs/ROADMAP.md](docs/ROADMAP.md) for planned features and development priorities.

---

## License

MIT License - See LICENSE file for details.

---

Developed as part of an ongoing exploration of agentic automation and local-first AI systems.