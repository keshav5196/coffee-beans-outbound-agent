# Quick Start Guide

Get the Outbound AI Agent running in 5 minutes.

## Prerequisites

- Python 3.9+
- Twilio Account with Voice capability
- ngrok

## Setup

```bash
# Navigate to project
cd outbound_ai_agent

# Run setup script
chmod +x setup.sh
./setup.sh
```

## Configure Credentials

1. Go to [Twilio Console](https://console.twilio.com)
2. Copy your **Account SID** and **Auth Token**
3. Get a verified phone number

Edit `.env`:
```
TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TWILIO_AUTH_TOKEN=your_auth_token_here
TWILIO_PHONE_NUMBER=+1234567890
SERVER_BASE_URL=https://your-ngrok-url.ngrok.io
```

## Expose to Internet (ngrok)

In a new terminal:
```bash
ngrok http 8000
```

Copy the HTTPS URL and update `.env`:
```
SERVER_BASE_URL=https://abc123.ngrok.io
```

## Run the Server

```bash
uv run python main.py
```

You should see:
```
INFO:     Uvicorn running on http://0.0.0.0:8000
```

## Make a Test Call

In another terminal:
```bash
uv run python example_usage.py
```

Or use curl:
```bash
curl -X POST "http://localhost:8000/call/initiate" \
  -H "Content-Type: application/json" \
  -d '{"to": "+1234567890"}'
```

## Answer the Call!

Your phone will ring. When you pick up:
- You'll hear: "Hello! This is an AI assistant. How can I help you today?"
- Speak your response
- The agent will reply
- Continue the conversation!

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

### Data Flow

```
User Speaks
    ↓
Twilio STT (real-time)
    ↓
WebSocket JSON message
    ↓
Extract transcribed text & add to history
    ↓
Supervisor Node (routes to appropriate worker)
    ↓
Worker Node (gather_info, service_info, qualify, schedule, or end)
    ↓
LLM generates contextual response
    ↓
Response added to conversation history
    ↓
WebSocket message: {"type": "text", "token": "...", "last": true}
    ↓
Twilio TTS + Audio Playback
    ↓
Listen for next input (loop)
```

## Quick Troubleshooting

| Issue | Solution |
|-------|----------|
| Connection refused | Ensure server is running: `uv run python main.py` |
| Twilio credentials error | Double-check `.env` file, verify phone number |
| Call not connecting | Verify ngrok is running and URL matches `.env` |
| Speech not recognized | Speak clearly, check Twilio Console logs |

## Next Steps

- **Customize Greeting**: Edit `AGENT_GREETING` in `config.py`
- **Switch LLM**: See README.md for provider options
- **Learn Architecture**: Check README.md for detailed system design

---

**See [README.md](README.md)** for comprehensive documentation, API reference, architecture details, and production guidelines.
