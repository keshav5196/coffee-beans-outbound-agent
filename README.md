# Outbound AI Agent

A conversational AI agent for outbound calling using FastAPI, Twilio, and LangGraph.

## Architecture Overview

- **FastAPI**: Web framework for handling webhooks and API endpoints
- **Twilio**: Voice calling and speech-to-text/text-to-speech
- **LangGraph**: Agent framework for managing conversation state
- **Dummy Agent**: Simple rule-based responses (placeholder for real LLM)

## Project Structure

```
outbound_ai_agent/
├── main.py           # FastAPI app, Twilio webhooks, call management
├── agents.py         # LangGraph agent for conversation logic
├── config.py         # Configuration and environment variables
├── requirements.txt  # Python dependencies
├── .env.example      # Example environment variables
└── README.md         # This file
```

## Setup Instructions

### 1. Prerequisites

- Python 3.9+
- Twilio Account (with SMS/Voice capability)
- ngrok (for exposing local server to internet)

### 2. Install Dependencies

```bash
cd outbound_ai_agent
uv sync
```

### 3. Configure Twilio

1. Get your credentials from [Twilio Console](https://console.twilio.com):
   - Account SID
   - Auth Token
   - Verified Phone Number (to call from)

2. Create `.env` file:
```bash
cp .env.example .env
```

3. Fill in your Twilio credentials in `.env`:
```
TWILIO_ACCOUNT_SID=your_account_sid
TWILIO_AUTH_TOKEN=your_auth_token
TWILIO_PHONE_NUMBER=+1234567890
NGROK_URL=https://your-ngrok-url.ngrok.io
```

### 4. Expose Server with ngrok

```bash
# In another terminal
ngrok http 8000
# Copy the https URL provided
```

Update `NGROK_URL` in `.env` with the ngrok URL.

### 5. Run the Application

```bash
uv run python main.py
```

The server will start on `http://localhost:8000`

## API Endpoints

### Start a Call

```bash
curl -X POST "http://localhost:8000/call/initiate?phone_number=%2B1234567890"
```

Response:
```json
{
  "call_sid": "CAxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
  "status": "initiated"
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

1. **Initiate Call** (`/call/initiate`):
   - Creates an outbound call to the specified number
   - Twilio connects and calls the `/twiml/initial` endpoint

2. **Initial TwiML** (`/twiml/initial`):
   - Plays the greeting: "Hello! This is an AI assistant..."
   - Starts recording user speech

3. **Handle User Input** (`/handle/recording`):
   - Receives transcribed speech from Twilio
   - Passes it to the LangGraph agent
   - Agent generates a response
   - Says the response back to the user
   - Records next user input (loop)

4. **Call Status** (`/call/status`):
   - Tracks when call ends
   - Cleans up conversation history

## Agent Configuration

The current agent is a **dummy agent** with simple rule-based responses. To integrate a real LLM:

1. Update `agents.py`:
   - Replace `generate_dummy_response()` with actual LLM call
   - Use OpenAI, Claude, or another LLM API

2. Example integration point in `generate_dummy_response()`:
```python
# from langchain.chat_models import ChatOpenAI
# llm = ChatOpenAI(model="gpt-4", temperature=0.7)
# response = llm.invoke(user_input)
```

## Testing

### Manual Testing via curl

```bash
# 1. Start the server
uv run python main.py

# 2. In another terminal, initiate a call
curl -X POST "http://localhost:8000/call/initiate?phone_number=%2B19876543210"

# 3. When your phone rings and you answer, you'll hear the greeting
# 4. Speak to interact with the agent
```

## Features

✅ Outbound calling via Twilio
✅ Speech-to-text recognition
✅ Text-to-speech responses
✅ Multi-turn conversation handling
✅ Conversation history tracking
✅ Greeting on call pickup
✅ Call status monitoring

## Future Improvements

- [ ] Real LLM integration (OpenAI, Claude, etc.)
- [ ] Conversation memory/context persistence
- [ ] Advanced error handling and retry logic
- [ ] Support for Twilio ConversationRelay (WebSocket for real-time audio)
- [ ] Database for storing conversation logs
- [ ] User authentication and authorization
- [ ] Rate limiting and call queuing
- [ ] Advanced prompt engineering
- [ ] Integration with external APIs/tools
- [ ] Monitoring and analytics

## Troubleshooting

### "Missing Twilio credentials"
- Ensure `.env` file is created and filled with correct values
- Check that environment variables are loaded: `python -c "from config import TWILIO_ACCOUNT_SID; print(TWILIO_ACCOUNT_SID)"`

### "Call not connecting"
- Verify ngrok is running and the URL is updated in `.env`
- Check Twilio Console logs for webhook failures
- Ensure your Twilio account has sufficient balance

### "Speech not being recognized"
- Speak clearly and pause between sentences
- Check Twilio application logs for transcription errors
- Adjust `max_speech_time` and `timeout` in `/twiml/initial`

## License

MIT
