# Smart Home Roadmap

This document outlines the planned features, improvements, and ongoing development for the Smart Home agentic automation system.

---

## Current Issues & Active Work

### Highest Priority - MCP Integration

- **MCP (Model Context Protocol) Support**: Add plug-and-play MCP integration as core framework capability
  - Implement MCP client in the Agent framework
  - Support dynamic MCP server discovery and connection
  - Enable runtime loading of MCP tools/resources
  - Handle MCP server lifecycle (connect, disconnect, reconnect)
  - Expose MCP tools to agents automatically
  - Add MCP configuration to `.env` and settings
  - Design plugin architecture for future MCP servers

**Why this is critical**: MCP will enable both Zigbee/MQTT control for lights and web fetch capabilities for search. Making it plug-and-play now enables future extensibility without core framework changes.

### High Priority - Capability Expansion

- **Web Search Agent**: Enable the system to retrieve information from the internet to answer any question
  - Use MCP fetch tool for content retrieval
  - Implement web search tool (DuckDuckGo API as fallback)
  - Add content extraction and summarization capabilities
  - Handle multi-step research queries
  - Cache search results for performance

- **Light Agent**: Complete Zigbee MQTT integration for smart lighting control
  - Finish Zigbee MQTT MCP server implementation on separate server
  - Connect to MCP server from smart home system
  - Create Light Agent using MCP-exposed Zigbee tools
  - Implement tools for on/off, brightness, color control
  - Implement scene management
  - Add state query capabilities
  - Test with actual Zigbee devices via MQTT broker

### Medium Priority - User Interface

- **Frontend Development**: Build web-based interface for the smart home system
  - Design and implement web dashboard
  - Real-time conversation view
  - Device status monitoring
  - Agent configuration interface
  - Consider tech stack: FastAPI backend + React/Vue frontend

### Low Priority

- **Fix Wake-Word Detection**: OpenWakeWord integration is not functioning correctly. Issues to investigate:
  - Model loading and initialization
  - Audio stream configuration
  - Threshold tuning
  - Integration with main conversation loop

- **Fix Spotify Tool Implementation**: The Spotify integration is currently broken (as of commit 300fe40). Need to debug and restore functionality for:
  - Play/Pause commands
  - Device switching
  - Volume control
  - Search and URI playback

- **Configuration Validation**: Add startup validation for:
  - Required environment variables based on selected provider
  - Model file existence (Vosk, OpenWakeWord)
  - API credential verification
  - Network connectivity checks

- **Implement Testing Infrastructure**: The `tests/` directory exists but is currently empty. Need to add:
  - Unit tests for core Agent and Tool classes
  - Integration tests for each agent (Weather, Spotify, Home)
  - Mock API responses for weather.gov and Spotify
  - Voice I/O testing utilities
  - CI/CD pipeline configuration

---

## Future Agents

### Web Search Agent *(In Active Development)*
**Description**: Retrieve information from the internet to answer questions beyond the LLM's knowledge base.

**Tools:**
- `WebSearchTool`: Search the internet using DuckDuckGo, SearXNG, or similar
- `ExtractContentTool`: Extract and parse content from web pages
- `SummarizeTool`: Condense long articles or search results
- `FactCheckTool`: Cross-reference information across multiple sources

**Integration:**
- DuckDuckGo API (no authentication required)
- SearXNG self-hosted instance (privacy-focused)
- BeautifulSoup/Playwright for content extraction
- Result caching to reduce API calls

**Example queries:**
- "What's the latest news about AI developments?"
- "Look up the recipe for chocolate chip cookies"
- "Find information about the history of the Roman Empire"
- "What are the current gas prices in my area?"

---

### Smart Lighting Agent *(In Active Development)*
**Description**: Control smart lights (Zigbee via MQTT) with natural language.

**Tools:**
- `SetLightStateTool`: Turn lights on/off, set brightness, change color
- `SetSceneTool`: Apply predefined lighting scenes (movie, dinner, reading, etc.)
- `ScheduleLightTool`: Set timers and schedules for automatic control
- `QueryLightStateTool`: Get current state of lights

**Integration:**
- MQTT/Zigbee2MQTT for local control
- MCP (Model Context Protocol) server for Zigbee MQTT bridge

**Example queries:**
- "Turn on the bedroom lights"
- "Set living room to 50% brightness"
- "Make the kitchen lights warm white"
- "Turn off all lights in 30 minutes"

**Status**: Requires completion of Zigbee MQTT MCP implementation on server

---

### Calendar & Scheduling Agent
**Description**: Manage calendar events, reminders, and time-based automation.

**Tools:**
- `GetEventsTool`: Query upcoming calendar events
- `CreateEventTool`: Add new calendar entries
- `SetReminderTool`: Create one-time or recurring reminders
- `QueryAvailabilityTool`: Check free/busy times

**Integration:**
- Google Calendar API
- Local CalDAV server (Radicale, etc.)
- iCal file parsing

**Example queries:**
- "What's on my calendar tomorrow?"
- "Add a dentist appointment for Tuesday at 2pm"
- "Remind me to water the plants every Sunday"
- "Am I free Friday afternoon?"

---

### Entertainment Agent
**Description**: Control media playback across multiple platforms (TV, streaming, local media).

**Tools:**
- `ControlTVTool`: Power, input switching, volume for smart TVs
- `StreamingSearchTool`: Find content across Netflix, Plex, YouTube, etc.
- `PlayLocalMediaTool`: Browse and play from local media library
- `PodcastTool`: Subscribe to and play podcasts

**Integration:**
- Plex Media Server API
- Kodi/XBMC JSON-RPC
- YouTube API
- TV control via HDMI-CEC or IR blaster

**Example queries:**
- "Play Stranger Things on Netflix"
- "Find movies with Tom Hanks in my Plex library"
- "Turn on the TV and switch to HDMI 2"
- "Play the latest episode of my favorite podcast"

---

### Home Security Agent
**Description**: Monitor security cameras, sensors, and access control.

**Tools:**
- `GetCameraFeedTool`: Access live or recorded camera footage
- `QuerySensorsTool`: Check door/window sensors, motion detectors
- `SetAlarmModeTool`: Arm/disarm security system
- `ReviewEventsTool`: View recent security events/alerts

**Integration:**
- Frigate NVR for camera management
- Home Assistant security components
- Z-Wave/Zigbee sensors
- Ring/Nest API integration

**Example queries:**
- "Show me the front door camera"
- "Are all windows closed?"
- "Arm the alarm system"
- "Any motion detected while I was gone?"

---

### Home Assistant Integration Agent
**Description**: Generic bridge to Home Assistant for controlling any entity.

**Tools:**
- `CallServiceTool`: Execute any Home Assistant service
- `GetStateTool`: Query entity states
- `SetStateTool`: Modify entity attributes
- `ListEntitiesTool`: Discover available entities

**Integration:**
- Home Assistant REST API
- WebSocket API for real-time updates
- Long-lived access tokens

**Benefits:**
- Single integration point for dozens of smart home platforms
- Access to Home Assistant's extensive automation logic
- Unified interface for heterogeneous devices

**Example queries:**
- "What's the temperature on the thermostat?"
- "Start the robot vacuum"
- "Is the garage door open?"
- "Set the thermostat to 72 degrees"

---

## Future Tools

### Spotify Tools (Enhancements)
- **`SpotifyRecommendationTool`**: Get recommendations based on current mood/activity
- **`PlaylistManagementTool`**: Create, modify, delete playlists
- **`SaveTrackTool`**: Add current track to library or playlist
- **`QueueManagementTool`**: View and modify playback queue

---

### System Monitoring Tools
- **`SystemStatusTool`**: CPU, memory, disk usage of smart home server
- **`NetworkStatusTool`**: Check connectivity, bandwidth, device presence
- **`ServiceHealthTool`**: Monitor status of Docker containers, services
- **`LogQueryTool`**: Search application logs for debugging

---

### Communication Tools
- **`SendNotificationTool`**: Push notifications to phone (Pushbullet, ntfy)
- **`SendEmailTool`**: Automated email sending
- **`SendSMSTool`**: SMS alerts via Twilio or similar
- **`IntercomTool`**: Broadcast TTS messages to smart speakers

---

### Automation & Scripting Tools
- **`CreateAutomationTool`**: Define new automation rules via natural language
- **`RunScriptTool`**: Execute custom Python/Bash scripts
- **`ScheduleTaskTool`**: Cron-like scheduling for recurring actions
- **`WebhookTool`**: Trigger external services via HTTP requests

---

### Knowledge & Context Tools
- **`WikipediaTool`**: Query Wikipedia for factual information
- **`CalculatorTool`**: Perform mathematical calculations
- **`UnitConversionTool`**: Convert between units (temperature, distance, etc.)
- **`TimerTool`**: Set countdowns and timers with TTS alerts

---

### Local Media Library Tools
- **`MusicLibraryTool`**: Browse and play local music files
- **`PhotoGalleryTool`**: Access and display photos from NAS
- **`BookLibraryTool`**: Manage and read ebooks
- **`AudiobookTool`**: Resume audiobook playback

---

## Future Framework Improvements

### MCP Ecosystem *(Foundation for Extensibility)*
**Goal**: Build a robust MCP integration layer for plug-and-play capabilities.

**Features:**
- **MCP Client Library**: Core client for connecting to MCP servers
- **Auto-discovery**: Detect and connect to MCP servers on network or via stdio
- **Tool Registry**: Dynamically register MCP-provided tools into agent framework
- **Resource Access**: Support MCP resources (files, data, configs)
- **Prompts/Templates**: Leverage MCP prompt templates from servers
- **Multi-server Support**: Connect to multiple MCP servers simultaneously
- **Error Handling**: Graceful degradation when MCP servers are unavailable
- **Configuration**: Simple `.env` or YAML config for MCP server endpoints

**Example MCP Servers to Support:**
- **Zigbee/MQTT Server**: Smart home device control (lights, sensors, switches)
- **Web Fetch Server**: HTTP requests and content extraction
- **Database Server**: Query local databases (SQLite, PostgreSQL)
- **File System Server**: Read/write files on remote systems
- **API Gateway Server**: Unified access to multiple third-party APIs

**Architecture Benefits:**
- No need to modify core Agent code for new integrations
- Community can build and share MCP servers
- Separation of concerns: integration logic lives in MCP servers
- Hot-swappable capabilities without restarting system

---

### Multi-Agent Coordination
**Goal**: Enable agents to collaborate on complex tasks.

**Features:**
- Agent-to-agent communication protocol
- Task delegation and result aggregation
- Shared context/memory between agents
- Parallel execution for independent subtasks

**Example:**
- User: "Prepare for movie night"
- HomeAgent delegates to:
  - LightingAgent: Dim lights to 20%
  - EntertainmentAgent: Load movie queue
  - SpotifyAgent: Pause music

---

### Memory & Context Management
**Goal**: Enable agents to remember past interactions and learn preferences.

**Features:**
- Vector database for semantic memory (ChromaDB, Qdrant)
- User preference learning (favorite music genres, typical wake times, etc.)
- Context retrieval from past conversations
- Long-term memory persistence across sessions

**Example:**
- Agent remembers you prefer jazz in the evening
- Automatically suggests relevant music without explicit request

---

### Natural Language Automation Builder
**Goal**: Create automations through conversation without code.

**Features:**
- Parse natural language into automation rules
- Generate Python/YAML automation definitions
- Visual confirmation before saving
- Edit existing automations via conversation

**Example:**
- User: "Every weekday at 7am, turn on the coffee maker and read the weather"
- Agent generates automation and adds to system

---

### Multi-Room Audio Synchronization
**Goal**: Coordinate audio playback across multiple rooms.

**Features:**
- Snapcast integration for synchronized speakers
- Room grouping and zone control
- Follow-me audio (music follows you room-to-room)
- Independent volume control per zone

---

### Vision & Image Analysis
**Goal**: Enable agents to process visual information.

**Features:**
- Camera image analysis (detect packages, people, etc.)
- OCR for reading text from images
- QR code scanning
- Plant/object identification

**Tools:**
- `AnalyzeImageTool`: Describe image contents
- `ReadTextTool`: Extract text via OCR
- `DetectObjectsTool`: Identify specific objects
- `FaceRecognitionTool`: Identify household members

---

### Voice Profile Management
**Goal**: Multi-user voice recognition and personalization.

**Features:**
- Speaker identification (who is speaking?)
- Per-user preferences and permissions
- Voice enrollment and training
- Accent/dialect adaptation

---

### Proactive Suggestions
**Goal**: Agent initiates helpful suggestions without prompting.

**Features:**
- Contextual awareness (time of day, weather, calendar)
- Pattern recognition (usual routines)
- Anomaly detection (unusual energy usage, open doors)
- Gentle notifications without being intrusive

**Example:**
- "It's going to rain this afternoon. Would you like me to close the skylights?"
- "You usually leave for work at 8am. Should I start your morning routine?"

---

### Offline-First Capabilities
**Goal**: Full functionality without internet connectivity.

**Features:**
- Local LLM optimization (smaller models, quantization)
- Local API fallbacks (cache weather, offline maps)
- Peer-to-peer device communication
- Graceful degradation when cloud services unavailable

---

### Web Dashboard
**Goal**: Browser-based interface for monitoring and control.

**Features:**
- Real-time conversation view
- Device status dashboard
- Agent configuration UI
- Automation builder interface
- Log viewer and debugging tools

**Tech Stack:**
- FastAPI backend
- WebSocket for real-time updates
- React/Vue frontend
- D3.js for visualizations

---

### Mobile App
**Goal**: Native mobile interface for on-the-go control.

**Features:**
- Push notifications for alerts
- Voice input via phone microphone
- Quick action buttons (common commands)
- Location-based triggers (arrive/leave home)

---

### Plugin Architecture
**Goal**: Make it easy for users to add custom agents and tools.

**Features:**
- Hot-reload for plugin code changes
- Standardized plugin manifest format
- Dependency management per plugin
- Plugin marketplace/repository

**Note**: MCP servers will serve as the primary plugin mechanism for external integrations. This native plugin architecture focuses on Python-based agents and tools that run in-process.

---

## Technical Debt & Refactoring

### Code Quality
- Refactor large functions into smaller units
- Extract magic numbers/strings into constants

### Architecture
- Separate concerns: move API clients out of tools
- Create shared utilities module for common operations

### Performance
- Cache API responses with TTL expiration
- Optimize message history truncation strategy

---

## Long-Term Vision

The goal is to build a **truly intelligent home assistant** that:

1. **Understands context** beyond individual commands
2. **Learns preferences** without explicit programming
3. **Operates locally** for privacy and reliability
4. **Extends easily** through modular tools and agents
5. **Respects users** with transparent reasoning and control

This system should feel less like issuing commands to a machine and more like collaborating with a thoughtful assistant that anticipates needs, suggests improvements, and handles complexity behind the scenes.

---

*Last updated: 2025-11-13*
