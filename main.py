import json
import logging
from contextlib import asynccontextmanager
from typing import Any, Dict, List

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel
from twilio.rest import Client
import uvicorn

from config import (
    TWILIO_ACCOUNT_SID,
    TWILIO_AUTH_TOKEN,
    TWILIO_PHONE_NUMBER,
    HOST,
    PORT,
    SERVER_BASE_URL,
    AGENT_GREETING,
)
from agents import get_agent_response

# Logging setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# Lifespan context manager for startup and shutdown events
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage app startup and shutdown events."""
    # Startup
    logger.info("Application started")
    logger.info(f"Twilio Phone Number: {TWILIO_PHONE_NUMBER}")
    logger.info(f"Server Base URL: {SERVER_BASE_URL}")

    yield

    # Shutdown
    logger.info("Application shutting down")
    SESSIONS.clear()


# Initialize FastAPI app with lifespan
app = FastAPI(title="Outbound AI Agent - ConversationRelay", lifespan=lifespan)

# Twilio client
twilio_client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)

# In-memory session storage for active calls
# Key: session_id, Value: {"call_sid": str, "phone_number": str, "history": list}
SESSIONS: Dict[str, Dict[str, Any]] = {}


class CallRequest(BaseModel):
    """Request model for initiating a call."""
    to: str  # Phone number in E.164 format


@app.post("/call/initiate")
async def initiate_call(call: CallRequest):
    """Initiate an outbound call to a given phone number.

    This endpoint starts the call and sets up the ConversationRelay voice channel.
    """
    if not twilio_client:
        raise HTTPException(status_code=500, detail="Twilio client not configured (missing env vars)")

    try:
        logger.info(f"Initiating call to {call.to}")

        voice_url = f"{SERVER_BASE_URL}/voice"

        # Create the call with TwiML endpoint
        twilio_call = twilio_client.calls.create(
            to=call.to,
            from_=TWILIO_PHONE_NUMBER,
            url=voice_url,
            method="POST",
        )

        # Store session info
        SESSIONS[twilio_call.sid] = {
            "call_sid": twilio_call.sid,
            "phone_number": call.to,
            "history": [],
        }

        logger.info(f"Call created with SID: {twilio_call.sid}")

        return {
            "call_sid": twilio_call.sid,
            "status": "initiated",
            "phone_number": call.to,
        }

    except Exception as e:
        logger.error(f"Error initiating call: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/voice")
async def voice_webhook(request: Request):
    """TwiML endpoint called when Twilio dials the number.

    Returns TwiML which plays a greeting and hands off to ConversationRelay WebSocket.
    Extracts CallSid from Twilio's form parameters.
    """
    # Twilio sends CallSid as form parameter, not JSON
    form_data = await request.form()
    call_sid = form_data.get("CallSid", "unknown")

    logger.info(f"Received TwiML request for CallSid: {call_sid}")

    # Build WebSocket URL using the actual CallSid
    # Use wss:// for secure WebSocket
    websocket_url = f"{SERVER_BASE_URL}/ws/{call_sid}".replace("http://", "wss://").replace("https://", "wss://")

    logger.info(f"Generating TwiML with websocket URL: {websocket_url}")

    twiml = (
        "<?xml version=\"1.0\" encoding=\"UTF-8\"?>"
        "<Response>"
        "  <Connect>"
        f"    <ConversationRelay url='{websocket_url}' welcomeGreeting='{AGENT_GREETING}'/>"
        "  </Connect>"
        "</Response>"
    )

    logger.info(f"TwiML response:\n{twiml}")
    return Response(content=twiml, media_type="application/xml")


@app.websocket("/ws/{call_sid}")
async def websocket_endpoint(websocket: WebSocket, call_sid: str):
    """WebSocket endpoint for Twilio ConversationRelay.

    Receives real-time speech events from Twilio and sends agent responses.
    """
    logger.info(f"WebSocket connection attempt for call_sid={call_sid}")

    await websocket.accept()
    logger.info(f"WebSocket connection accepted for call_sid={call_sid}")

    # Get or create session
    if call_sid not in SESSIONS:
        logger.warning(f"Session not found for call_sid={call_sid}, creating new session")
        SESSIONS[call_sid] = {
            "call_sid": call_sid,
            "phone_number": "unknown",
            "history": [],
        }
    else:
        logger.info(f"Session found for call_sid={call_sid}")

    session = SESSIONS[call_sid]
    history = session["history"]
    logger.info(f"Using session with phone_number={session.get('phone_number')}, history length={len(history)}")

    try:
        while True:
            # Receive message from Twilio
            raw = await websocket.receive_text()
            try:
                msg = json.loads(raw)
            except json.JSONDecodeError:
                logger.warning(f"Received non-JSON payload: {raw}")
                continue

            logger.info(f"Received WebSocket message: {json.dumps(msg)}")

            # Extract user text from the message
            user_text = None

            # Try common locations for transcribed text
            if "voicePrompt" in msg and isinstance(msg["voicePrompt"], str) and msg["voicePrompt"].strip():
                user_text = msg["voicePrompt"].strip()

            # Check nested structure (result.alternatives)
            if not user_text:
                result = msg.get("result")
                if isinstance(result, dict):
                    alts = result.get("alternatives") or []
                    if isinstance(alts, list) and len(alts) > 0 and isinstance(alts[0], dict):
                        t = alts[0].get("transcript")
                        if isinstance(t, str) and t.strip():
                            user_text = t.strip()

            # Process if we have user text
            if user_text:
                logger.info(f"User text detected: {user_text}")
                history.append({"role": "user", "content": user_text})

                # Get agent response
                agent_response = get_agent_response(user_text, conversation_history=history)
                history.append({"role": "assistant", "content": agent_response})

                logger.info(f"Agent response: {agent_response}")

                
                await websocket.send_text(
                    json.dumps(
                        {
                            "type": "text",
                            "token":agent_response,
                            "last": True
                        }
                    ))
                logger.info(f"Sent response: {agent_response}")
            else:
                logger.debug(f"No user text found in message: {json.dumps(msg)}")

    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for call_sid={call_sid}")
    except Exception as e:
        logger.exception(f"Unexpected error in WebSocket handler for call_sid={call_sid}: {e}")


@app.get("/calls/active")
async def get_active_calls():
    """Get all active sessions."""
    return {
        "active_calls": list(SESSIONS.keys()),
        "count": len(SESSIONS),
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}


if __name__ == "__main__":
    uvicorn.run("main:app", host=HOST, port=PORT, reload=True)
