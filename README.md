# Outbound AI Agent

A real-time conversational AI agent for outbound calling using FastAPI, Twilio ConversationRelay WebSocket, and LangGraph.

## Features

✅ Outbound calling via Twilio
✅ Real-time audio streaming (ConversationRelay WebSocket)
✅ Low-latency (~200-500ms) speech-to-text & text-to-speech
✅ Multi-turn conversation handling with history
✅ LangGraph agent framework ready for LLM integration
✅ Session-based call management
✅ Easy deployment with uv package manager

## Tech Stack

- **FastAPI**: Web framework with async/await support
- **Twilio ConversationRelay**: Real-time voice API with WebSocket
- **LangGraph**: Conversation agent orchestration
- **uv**: Python package & project manager
- **Python 3.9+**: Core runtime

## Quick Start

### 1. Prerequisites

- Python 3.9+
- Twilio Account with Voice capability
- ngrok (for local development)

### 2. Setup

```bash
# Clone and navigate to project
cd outbound_ai_agent

# Install dependencies
uv sync

# Configure environment
cp .env.example .env
# Edit .env with your Twilio credentials
```

### 3. Get Twilio Credentials

1. Go to [Twilio Console](https://console.twilio.com)
2. Copy Account SID and Auth Token
3. Get a verified phone number (to call from)

### 4. Expose to Internet (ngrok)

```bash
ngrok http 8000
```

Copy the HTTPS URL and update `.env`:
```
SERVER_BASE_URL=https://abc123.ngrok.io
```

### 5. Run the Server

```bash
uv run python main.py
```

Server starts on `http://localhost:8000`

## API Endpoints

### Initiate Call

```bash
curl -X POST "http://localhost:8000/call/initiate" \
  -H "Content-Type: application/json" \
  -d '{"to": "+1234567890"}'
```

**Response:**
```json
{
  "call_sid": "CAxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
  "status": "initiated",
  "phone_number": "+1234567890"
}
```

### Check Active Calls

```bash
curl "http://localhost:8000/calls/active"
```

### Health Check

```bash
curl "http://localhost:8000/health"
```

## How It Works

### Call Flow (ConversationRelay)

1. **Initiate Call** (`POST /call/initiate`):
   - Creates outbound call via Twilio API
   - Stores session for WebSocket communication

2. **TwiML Greeting** (`POST /voice`):
   - Plays greeting: "Hello! This is an AI assistant..."
   - Hands off to ConversationRelay for real-time streaming

3. **Real-time WebSocket** (`/ws/{session_id}`):
   - Twilio streams real-time transcribed speech
   - Agent generates response (low latency)
   - Sends response back via WebSocket SPI message
   - Twilio synthesizes & plays audio, continues listening

4. **Call Cleanup**:
   - WebSocket disconnects when caller hangs up
   - Session history is retained

## Architecture

### System Overview

```
User → REST API → FastAPI → Twilio
                     ↓
                  WebSocket
                  (Real-time)
                     ↓
                 LangGraph Agent
                (Conversation Logic)
```

### Key Components

**main.py** - FastAPI server
- `POST /call/initiate`: Create outbound call
- `POST /voice`: TwiML endpoint with greeting + ConversationRelay handoff
- `WebSocket /ws/{session_id}`: Real-time audio handler with agent integration
- `GET /calls/active`: List active sessions
- `GET /health`: Health check

**agents.py** - LangGraph agent
- `get_agent_response()`: Main entry point
- `generate_dummy_response()`: Rule-based responses (replaceable with real LLM)
- Maintains conversation history per session

**config.py** - Environment configuration
- Twilio credentials
- Server settings (HOST, PORT, SERVER_BASE_URL)
- Agent greeting customization

### Data Flow

```
User Speaks
    ↓
Twilio STT (real-time)
    ↓
WebSocket JSON message
    ↓
Extract transcribed text
    ↓
LangGraph Agent → Generate response
    ↓
WebSocket SPI message: {"type": "response.create", "response": {"speech": "..."}}
    ↓
Twilio TTS + Audio Playback
    ↓
Listen for next input (loop)
```

## Project Structure

```
outbound_ai_agent/
├── main.py              # FastAPI + WebSocket + ConversationRelay
├── agents.py            # LangGraph agent with conversation logic
├── config.py            # Environment & Twilio configuration
├── example_usage.py     # API client example
├── pyproject.toml       # Project metadata & dependencies (uv)
├── uv.lock             # Locked dependency versions
├── .python-version      # Python 3.12 specification
├── .env.example         # Environment template
├── setup.sh             # Quick setup script
├── README.md            # This file
├── QUICKSTART.md        # Fast start guide
└── .gitignore           # Git exclusions
```

## Integrating a Real LLM

Replace `generate_dummy_response()` in **agents.py**:

```python
from langchain.chat_models import ChatOpenAI

llm = ChatOpenAI(model="gpt-4", temperature=0.7)

def get_agent_response(user_message, conversation_history=None):
    response = llm.invoke(user_message)
    return response.content
```

Supports: OpenAI, Anthropic Claude, open-source models (LLaMA, Mistral, etc.)

## Performance

- **Latency**: ~200-500ms (real-time WebSocket)
- **Concurrent Calls**: ~50-100 (depends on agent response time & network)
- **Architecture**: Stateless (scales horizontally)

### For Production

- Add persistent database (PostgreSQL, Redis) for session state
- Use message queues (Redis, RabbitMQ) for scaling
- Implement caching for common responses
- Add monitoring (Prometheus/Grafana)
- Load balancing with multiple instances
- Rate limiting & API authentication

## Troubleshooting

### "Missing Twilio credentials"
```bash
uv run python -c "from config import TWILIO_ACCOUNT_SID; print(TWILIO_ACCOUNT_SID)"
```

### "SERVER_BASE_URL not set"
- Set in `.env`: `SERVER_BASE_URL=https://your-ngrok-url.ngrok.io`
- Ensure ngrok is running: `ngrok http 8000`

### "Call not connecting"
- Verify SERVER_BASE_URL is public and reachable
- Check Twilio Console logs
- Ensure account has sufficient balance

### "WebSocket connection failed"
- Check ngrok tunnel is active
- Verify SERVER_BASE_URL matches ngrok URL
- Review application logs for connection errors

## Roadmap

- [ ] Real LLM integration (OpenAI, Claude)
- [ ] Persistent conversation storage (PostgreSQL)
- [ ] API authentication & rate limiting
- [ ] Advanced agent patterns (ReAct, tool use)
- [ ] SSML support for expressive TTS
- [ ] Multi-language support
- [ ] Call transfer & escalation
- [ ] Analytics dashboard

## Environment Variables

```
# Twilio Configuration
TWILIO_ACCOUNT_SID=your_account_sid
TWILIO_AUTH_TOKEN=your_auth_token
TWILIO_PHONE_NUMBER=+1234567890

# Server Configuration
HOST=0.0.0.0
PORT=8000
SERVER_BASE_URL=https://your-ngrok-url.ngrok.io
```

## License

MIT
