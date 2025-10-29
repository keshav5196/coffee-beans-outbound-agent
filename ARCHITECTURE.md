# System Architecture

## Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    Outbound AI Agent                        │
└─────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────┐
│                        Your Application                         │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │                      FastAPI Server                        │ │
│  │  ┌──────────────────────────────────────────────────────┐ │ │
│  │  │  POST /call/initiate                                │ │ │
│  │  │  ├─ Create outbound call via Twilio               │ │ │
│  │  │  └─ Return Call SID                               │ │ │
│  │  └──────────────────────────────────────────────────────┘ │ │
│  │  ┌──────────────────────────────────────────────────────┐ │ │
│  │  │  POST /twiml/initial                               │ │ │
│  │  │  ├─ Say greeting: "Hello, this is an AI..."       │ │ │
│  │  │  └─ Start recording user speech                   │ │ │
│  │  └──────────────────────────────────────────────────────┘ │ │
│  │  ┌──────────────────────────────────────────────────────┐ │ │
│  │  │  POST /handle/recording                            │ │ │
│  │  │  ├─ Receive transcribed user input                │ │ │
│  │  │  ├─ Pass to LangGraph agent                       │ │ │
│  │  │  ├─ Get agent response                            │ │ │
│  │  │  ├─ Say response back to user                     │ │ │
│  │  │  └─ Record next input (loop)                      │ │ │
│  │  └──────────────────────────────────────────────────────┘ │ │
│  │  ┌──────────────────────────────────────────────────────┐ │ │
│  │  │  POST /call/status                                 │ │ │
│  │  │  └─ Track call completion, cleanup                │ │ │
│  │  └──────────────────────────────────────────────────────┘ │ │
│  └────────────────────────────────────────────────────────────┘ │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │                    LangGraph Agent                         │ │
│  │  ┌──────────────────────────────────────────────────────┐ │ │
│  │  │  ConversationState                                  │ │ │
│  │  │  ├─ messages: list of conversation turns          │ │ │
│  │  │  ├─ user_input: latest user message               │ │ │
│  │  │  └─ response: agent response                       │ │ │
│  │  └──────────────────────────────────────────────────────┘ │ │
│  │  ┌──────────────────────────────────────────────────────┐ │ │
│  │  │  process_user_input() node                          │ │ │
│  │  │  └─ Generate dummy response (placeholder for LLM)  │ │ │
│  │  └──────────────────────────────────────────────────────┘ │ │
│  └────────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────┐
│                       Twilio (Cloud)                             │
│  ┌──────────────────────────────────────────────────────────────┐│
│  │ Voice Calling Service                                        ││
│  │  ├─ Makes outbound calls                                    ││
│  │  ├─ Records user speech                                    ││
│  │  ├─ Converts speech to text (STT)                          ││
│  │  ├─ Converts text to speech (TTS)                          ││
│  │  └─ Sends webhooks to your app                             ││
│  └──────────────────────────────────────────────────────────────┘│
└──────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────┐
│                       ngrok (Tunneling)                          │
│  ├─ Exposes localhost:8000 to internet                          │
│  └─ Provides HTTPS URL for Twilio webhooks                      │
└──────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────┐
│                    User (Phone Network)                          │
│  ├─ Receives call from your Twilio number                       │
│  └─ Talks to the AI agent                                       │
└──────────────────────────────────────────────────────────────────┘
```

## Call Flow Sequence

```
1. User calls your API
   POST /call/initiate?phone_number=+1234567890
   │
   └─> FastAPI initiates Twilio call
       │
       └─> Twilio dials the phone

2. User picks up phone
   │
   └─> Twilio calls your /twiml/initial webhook
       │
       └─> Server responds with TwiML:
           - Say greeting ("Hello, this is an AI...")
           - Start recording user speech

3. User speaks
   │
   └─> Twilio records and transcribes speech
       │
       └─> Twilio POSTs to /handle/recording with transcript

4. Server processes user input
   │
   ├─> Passes transcript to LangGraph agent
   │
   ├─> Agent generates response
   │
   └─> Server responds with TwiML:
       - Say agent response
       - Record next user input

5. Loop continues until user hangs up
   │
   └─> Twilio POSTs to /call/status with "completed"
       │
       └─> Server cleans up call record

```

## File Structure

```
outbound_ai_agent/
├── main.py              # FastAPI app + Twilio webhooks
│                        # - Handles call initiation
│                        # - Manages TwiML responses
│                        # - Tracks call state
│
├── agents.py            # LangGraph agent
│                        # - ConversationState definition
│                        # - Response generation logic
│                        # - Conversation history management
│
├── config.py            # Configuration
│                        # - Twilio credentials (from .env)
│                        # - Server settings
│                        # - Agent greeting
│
├── requirements.txt     # Python dependencies
├── .env                 # Environment variables (local)
├── .env.example         # Example env template
├── setup.sh             # Quick setup script
├── example_usage.py     # Example API usage
├── README.md            # Full documentation
├── QUICKSTART.md        # Quick start guide
└── ARCHITECTURE.md      # This file
```

## Key Components

### 1. FastAPI Server (main.py)

**Responsibilities:**
- Expose REST API for initiating calls
- Handle webhooks from Twilio
- Manage active call state
- Route user input to agent
- Generate TwiML responses

**Key Endpoints:**
- `POST /call/initiate` - Start a call
- `POST /twiml/initial` - Initial greeting TwiML
- `POST /handle/recording` - Handle user input
- `POST /call/status` - Track call status
- `GET /calls/active` - List active calls
- `GET /health` - Health check

### 2. LangGraph Agent (agents.py)

**Responsibilities:**
- Process user input
- Generate appropriate responses
- Maintain conversation state
- Manage message history

**Current Implementation:**
- Dummy/rule-based agent (placeholder)
- Can be replaced with real LLM

**Extensible For:**
- OpenAI GPT-4
- Anthropic Claude
- Open-source models (LLaMA, Mistral, etc.)

### 3. Twilio Integration

**What Twilio Provides:**
- Voice calling infrastructure
- Speech-to-text (STT) transcription
- Text-to-speech (TTS) synthesis
- Webhook delivery mechanism

**What We Configure:**
- Account SID & Auth Token (authentication)
- From Phone Number (your agent's number)
- Webhook URLs (where Twilio sends events)

### 4. In-Memory Call State

```python
active_calls = {
    "CAxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx": {
        "phone_number": "+1234567890",
        "messages": [
            {"role": "user", "content": "Hello?"},
            {"role": "assistant", "content": "Hi there! How can I help?"}
        ],
        "connected": True
    }
}
```

## Data Flow

### Initiating a Call

```
User API Call
    ↓
FastAPI: POST /call/initiate
    ↓
Twilio Client: create call
    ↓
Store in active_calls dict
    ↓
Return Call SID to user
```

### During Active Call

```
User Speaks
    ↓
Twilio STT: Transcribe speech
    ↓
Twilio Webhook: POST /handle/recording
    ↓
Extract transcript and CallSid
    ↓
Get from active_calls dict
    ↓
Pass to LangGraph Agent
    ↓
Agent: generate_dummy_response()
    ↓
Store in conversation history
    ↓
Generate TwiML response
    ├─ Say agent response (TTS)
    ├─ Record next input
    └─ Return XML to Twilio
    ↓
Twilio plays response and records
```

## Integration Points for Future Enhancements

### 1. LLM Integration
Replace `generate_dummy_response()` in agents.py with:
```python
from langchain.llms import OpenAI

llm = OpenAI(model="gpt-4")
response = llm.predict(user_input)
```

### 2. Real-Time Audio (ConversationRelay)
Replace webhook-based recording with WebSocket:
```python
@app.websocket("/ws/call/{call_sid}")
async def websocket_endpoint(websocket: WebSocket, call_sid: str):
    # Real-time audio streaming
    # Lower latency than recording/webhook cycle
```

### 3. Persistent Storage
Add database for conversation logs:
```python
from sqlalchemy import create_engine
db = create_engine("postgresql://...")

# Store conversations for:
# - Analytics
# - Training data
# - Compliance
```

### 4. Advanced Agents
Replace LangGraph with more complex agent patterns:
- ReAct (Reasoning + Acting)
- Tool use / Function calling
- Multi-agent orchestration
- Memory systems

## Current Limitations & Next Steps

| Limitation | Why | Solution |
|-----------|-----|----------|
| Dummy agent | Simple rule-based responses | Integrate real LLM (OpenAI, Claude) |
| No persistent storage | Conversations lost on restart | Add database |
| Webhook-based | Higher latency, sequential | Use Twilio ConversationRelay WebSocket |
| Single conversation style | No personalization | Add user profiles, context |
| No authentication | Anyone can call | Add API key validation |
| No error recovery | Call may fail ungracefully | Add retry logic, better error handling |

## Performance Considerations

### Current (MVP)
- Max ~10-20 concurrent calls (limited by response latency)
- ~1-2 second latency between speech and response

### Optimizations for Production
- Implement connection pooling
- Use async/await for all I/O
- Add caching for common responses
- Implement ConversationRelay for real-time audio
- Use message queues (Redis/RabbitMQ)
- Horizontal scaling with load balancer
