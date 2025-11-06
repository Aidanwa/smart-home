# Smart Home

Agentic Smart Home Assistant

An experimental local-first smart-home automation system that combines natural language interaction, Zigbee/MQTT device control, and agentic reasoning.  
It can run fully offline using **Ollama (Llama 3.1 8B)** or use **OpenAI’s Responses API** for cloud-based reasoning and streaming function calls.

---

## Project Overview

**Smart Home** is a modular system that integrates local device control with intelligent decision-making.  
It is designed for privacy, extensibility, and experimentation with agentic automation.  
Agents can reason about your environment, call tools such as weather or light controllers, and respond through text or voice.

---

## Features

- Agent framework with modular `Agent` and `Tool` classes  
- Automatic tool-calling loop compatible with OpenAI’s Responses API  
- MQTT/Zigbee integration for local device control  
- Example `WeatherTool` for live API queries  
- Streaming text generation with OpenAI or Ollama  
- Optional voice I/O using Vosk speech models

---

## Setup

### 1. Clone and enter the project
'''
git clone https://github.com/yourusername/smart-home.git
cd smart-home
'''

### 2. Environment setup
Install dependencies using either `uv` or pip:

'''
uv sync
# or
pip install -r requirements.txt
'''

Create a `.env` file at the project root:

'''
# --- choose one backend ---

# For OpenAI:
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4.1-mini

# Optional (used by WeatherTool)
COORDS=37.77,-122.42
'''

If `OPENAI_API_KEY` is set, the agent uses the OpenAI **Responses API**.  
If not, it automatically falls back to **Ollama** running locally.

---

## Running with Ollama (Offline Mode)

Ollama provides fast, private local LLM inference.

Install and pull the lightweight tool-calling model:

'''
curl -fsSL https://ollama.com/install.sh | sh
ollama pull llama3.1:8b
'''

Ollama runs a background service on:
```
http://localhost:11434
```

Test it with:
'''
curl http://localhost:11434/api/tags
'''

---

## Running with OpenAI (Cloud Mode)

For improved reasoning and access to larger models:

1. Get an API key from https://platform.openai.com/  
2. Add it to your `.env` file  
3. The agent will automatically stream responses through the **Responses API**, including function calls and real-time output.

---

## Voice Integration (Vosk)

Download the English Vosk model:

https://alphacephei.com/vosk/models

Model name:
`vosk-model-small-en-us-0.15`

Place it in a top-level directory:

'''
smart-home/
├── models/
│   └── vosk-model-small-en-us-0.15/
└── src/
'''

---

## Example Usage

'''
uv run python src/smart_home/driver.py
'''

Example commands inside the app:
'''
Prompt: turn on the bedroom light
Prompt: what's the weather like?
Prompt: exit
'''

---

## Technology Stack

- Python 3.11+
- Ollama (Llama 3.1 8B)
- OpenAI Responses API
- MQTT / Zigbee2MQTT
- Vosk Speech Recognition

---

Developed as part of an ongoing personal agentic home automation project.
