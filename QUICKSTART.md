# Quick Start Guide

Get the Outbound AI Agent running in 5 minutes.

## 1. Prerequisites

- Python 3.9+
- Twilio Account
- ngrok

## 2. Install & Setup

```bash
# Clone/navigate to project
cd outbound_ai_agent

# Run setup script
chmod +x setup.sh
./setup.sh
```

## 3. Configure Credentials

Get your Twilio credentials from https://console.twilio.com:
- Account SID
- Auth Token
- Phone Number (must be verified)

Edit `.env`:
```
TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TWILIO_AUTH_TOKEN=your_auth_token_here
TWILIO_PHONE_NUMBER=+1234567890
SERVER_BASE_URL=https://your-ngrok-url.ngrok.io
```

## 4. Expose to Internet (ngrok)

In a new terminal:
```bash
ngrok http 8000
```

Copy the HTTPS URL (e.g., `https://abc123.ngrok.io`) and update `.env`:
```
SERVER_BASE_URL=https://abc123.ngrok.io
```

This enables Twilio to reach your WebSocket endpoint for real-time conversations.

## 5. Run the Server

```bash
uv run python main.py
```

You should see:
```
INFO:     Uvicorn running on http://0.0.0.0:8000
```

## 6. Make a Test Call

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

Replace `1234567890` with your phone number (must be in E.164 format).

## 7. Answer the Call!

Your phone will ring. When you pick up:
- You'll hear: "Hello! This is an AI assistant. How can I help you today?"
- Speak your response
- The agent will reply
- Continue the conversation!

## Troubleshooting

### "Connection refused"
```bash
# Make sure server is running
python main.py
```

### "Twilio credentials error"
- Double-check credentials in `.env`
- Make sure Phone Number is verified
- Check account has SMS/Voice enabled

### "Call not connecting"
- Verify ngrok is running
- Check ngrok URL matches `NGROK_URL` in `.env`
- Review Twilio Console logs

### "Speech not recognized"
- Speak clearly after the beep
- Check Twilio Console → Logs → Voice Calls

## Next Steps

- **Customize Greeting**: Edit `AGENT_GREETING` in `config.py`
- **Improve Agent**: Replace dummy responses in `agents.py` with real LLM
- **Add Features**: Check README.md for future improvements

## API Reference

### Initiate Call
```bash
POST /call/initiate?phone_number=+1234567890
```

### Check Active Calls
```bash
GET /calls/active
```

### Health Check
```bash
GET /health
```

## Documentation

See `README.md` for full documentation.
