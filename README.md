# Smart Home

Agentic Smart Home Assistant

An experimental **agentic smart home automation system** that uses LLMs to orchestrate tool usage for home automation tasks. It supports both **local-first operation (Ollama)** and **cloud-based reasoning (OpenAI)** with optional voice I/O.

---

## Project Overview

**Smart Home** is a modular agent framework that combines natural language interaction with intelligent tool orchestration. Agents can reason about your environment, call specialized tools (weather forecasts, Spotify control, Zigbee device management, and more), and respond through text or voice.

The system is designed for **privacy** (can run fully offline), **extensibility** (easy to add new agents and tools), and **experimentation** with agentic automation patterns.

---

## Features

- **Agent Framework**: Core `Agent` class with conversation state management and tool execution
- **Tool System**: Base `Tool` class with provider-specific schema generation for extensibility
- **Multiple Agents**: Weather, Spotify, Home, Search, and Zigbee agents with specialized capabilities
- **Zigbee Integration**: Control smart home devices (lights, sensors, thermostats) via Zigbee protocol
- **Voice Integration**: Speech-to-text (Vosk) and text-to-speech (pyttsx3) for hands-free interaction
- **Wake-word Filtering**: Text-based wake-word detection for voice-activated control
- **Session Management**: Persistent conversation state with automatic saving and restoration
- **Dual Backends**: OpenAI Responses API (cloud) or Ollama (local) with automatic fallback
- **Streaming Responses**: Real-time token streaming with tool-calling loop support
- **Parallel Execution**: Concurrent device control for faster smart home automation
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
HOME_COORDS=xxx,yyy           # Your latitude,longitude
HOME_GRID=...             # From weather.gov API
TIMEZONE=America/New_York

# Zigbee integration (optional - requires zigbeemcp API server)
ZIGBEE_API_BASE_URL=http://localhost:8000
ZIGBEE_API_KEY=your_api_key_here
PRIMARY_THERMOSTAT_ID=your_thermostat_name

# Spotify integration (optional)
SPOTIFY_CLIENT_ID=...
SPOTIFY_CLIENT_SECRET=...
SPOTIFY_REFRESH_TOKEN=...              # Get via OAuth flow

# Voice settings (optional)
SPEECH_TO_TEXT=False         # Enable microphone input
TEXT_TO_SPEECH=False         # Enable spoken output
WAKEWORD=jarvis              # Text-based wake-word filtering

# Logging (optional)
LOG_LEVEL=INFO               # Options: DEBUG, INFO, WARNING, ERROR
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
- **search**: Web search for current information
- **zigbee**: Smart home device control (requires Zigbee API server)

Example interactions:
```
Enter agent name: weather
You: What's the forecast for tomorrow afternoon?
AI: Tomorrow afternoon will be partly cloudy with temperatures around 72°F...

You: exit
```

### Voice mode example:
```bash
# Enable voice in .env:
SPEECH_TO_TEXT=True
TEXT_TO_SPEECH=True
WAKEWORD=jarvis

# Run the app - speak commands containing "jarvis"
Enter agent name: zigbee

Listening... [CHIME]
You: turn on the lights
(No wakeword 'jarvis' detected, ignoring)

Listening...
You: hey jarvis turn on the bedroom lights
AI: Turning on the bedroom lights.
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
OLLAMA_MODEL=llama3.1:8b  # Or mistral, codellama:13b, etc.
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

## Zigbee Integration

The Zigbee agent provides natural language control of smart home devices using the Zigbee protocol.

### Requirements

The Zigbee agent requires an external API server that bridges Zigbee2MQTT with a REST API. I wrote and locally host the API for this purpose which can be found here: [zigbeemcp](https://github.com/Aidanwa/zigbeemcp).

**Setup zigbeemcp:**

1. Clone and install the zigbeemcp API server:
```bash
git clone https://github.com/Aidanwa/zigbeemcp.git
cd zigbeemcp
# Follow setup instructions in the zigbeemcp README
```

2. Start the API server (typically runs on `http://localhost:8000`)

3. Configure in `.env`:
```bash
ZIGBEE_API_BASE_URL=http://localhost:8000
ZIGBEE_API_KEY=your_api_key_from_zigbeemcp
PRIMARY_THERMOSTAT_ID=YourThermostatName  # For temperature display
```

### Supported Devices

The Zigbee agent can control:
- **Lights**: ON/OFF, brightness (0-254), color temperature (153-500 mireds)
- **Sensors**: Read temperature, humidity, battery level
- **Smart Plugs**: Power control, energy monitoring
- **Thermostats**: Temperature reading and control

### Features

- **Parallel device control**: Control multiple devices simultaneously
- **State querying**: Check current device status (power, brightness, temperature, etc.)
- **Automatic conversion**: Celsius ↔ Fahrenheit temperature conversion
- **Dynamic device list**: Agent automatically discovers connected devices at startup
- **Batch operations**: Control multiple devices with a single command

### Example Usage

```
Enter agent name: zigbee

You: turn on the bedroom lights
AI: Turning on the bedroom lights.

You: set all living room lights to 50% brightness
AI: Setting brightness to 50%... Done.

You: what's the current temperature?
AI: The bedroom temperature is 72.5°F.
```

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
WAKEWORD=jarvis  # Optional: require wake-word in speech
```

### Wake-word Filtering

Set a wake-word to filter voice commands:

```bash
WAKEWORD=jarvis
```

Only speech containing the wake-word will be processed. Leave empty to process all speech input.

**Chime behavior:**
- Plays audio chime only on first interaction of a new session
- Subsequent listening cycles are silent
- No chime on wake-word rejections

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
- [zigbeemcp](https://github.com/Aidanwa/zigbeemcp) - Zigbee device control API
- [Vosk](https://alphacephei.com/vosk/) - Offline speech recognition
- [pyttsx3](https://pyttsx3.readthedocs.io/) - Text-to-speech synthesis

**Framework:**
- Custom agent framework with tool orchestration
- Session management with persistent state
- Parallel execution using ThreadPoolExecutor
- SSE (Server-Sent Events) streaming for OpenAI
- JSON streaming for Ollama

---

## Project Structure

```
smart-home/
├── src/smart_home/
│   ├── core/
│   │   ├── agent.py          # Core Agent and Tool classes
│   │   ├── session.py        # Session management
│   │   └── sse.py            # SSE parser for OpenAI streaming
│   ├── agents/
│   │   ├── weather.py        # Weather-focused agent
│   │   ├── spotify.py        # Spotify control agent
│   │   ├── home.py           # General-purpose home agent
│   │   ├── search.py         # Web search agent
│   │   └── zigbee.py         # Zigbee device control agent
│   ├── tools/
│   │   ├── weather/          # Weather.gov API integration
│   │   ├── spotify/          # Spotify Web API tools
│   │   └── zigbee/           # Zigbee device control tools
│   │       ├── get_devices.py    # Parallel device state querying
│   │       └── set_devices.py    # Parallel device control
│   ├── utils/
│   │   ├── voice_utils.py    # Speech I/O utilities
│   │   └── home_utils.py     # Zigbee API utilities
│   ├── config/
│   │   ├── paths.py          # Path configuration
│   │   └── logging.py        # Logging setup
│   └── driver.py             # Main entry point
├── models/                   # Voice models directory
├── data/
│   ├── logs/                 # Application logs
│   └── sessions/             # Saved conversation sessions
├── docs/
│   ├── ROADMAP.md           # Future plans and ideas
│   └── WAKEWORD_INVESTIGATION.md
```

---

## Contributing

This is a personal experimental project, but feedback and ideas are welcome!

See [docs/ROADMAP.md](docs/ROADMAP.md) for planned features and development priorities.

---

## License

MIT License - See LICENSE file for details.

---

Developed as part of an ongoing exploration of agentic automation and local-first AI systems
