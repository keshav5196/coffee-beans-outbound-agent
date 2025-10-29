import json
import logging
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

# Initialize FastAPI app
app = FastAPI(title="Outbound AI Agent - ConversationRelay")

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
    """
    twiml = (
        "<?xml version=\"1.0\" encoding=\"UTF-8\"?>"
        "<Response>"
        f"  <Say voice=\"alice\">{AGENT_GREETING}</Say>"
        "  <Connect>"
        "    <ConversationRelay />"
        "  </Connect>"
        "</Response>"
    )

    return Response(content=twiml, media_type="application/xml")


@app.websocket("/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    """WebSocket endpoint for Twilio ConversationRelay.

    Receives real-time speech events from Twilio and sends agent responses.
    """
    await websocket.accept()
    logger.info(f"WebSocket connection established for session_id={session_id}")

    # Get or create session
    if session_id not in SESSIONS:
        SESSIONS[session_id] = {
            "call_sid": session_id,
            "phone_number": "unknown",
            "history": [],
        }

    session = SESSIONS[session_id]
    history = session["history"]

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
            for key in ("transcript", "text", "speech", "utterance", "transcription"):
                if key in msg and isinstance(msg[key], str) and msg[key].strip():
                    user_text = msg[key].strip()
                    break

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

                # Send response back to Twilio
                spi_msg = {
                    "type": "response.create",
                    "response": {
                        "speech": agent_response,
                    },
                }

                await websocket.send_text(json.dumps(spi_msg))
                logger.info(f"Sent response: {agent_response}")

    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for session_id={session_id}")
    except Exception as e:
        logger.exception(f"Unexpected error in WebSocket handler: {e}")


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


@app.on_event("startup")
async def startup_event():
    """Run on application startup."""
    logger.info("Application started")
    logger.info(f"Twilio Phone Number: {TWILIO_PHONE_NUMBER}")
    logger.info(f"Server Base URL: {SERVER_BASE_URL}")


@app.on_event("shutdown")
async def shutdown_event():
    """Run on application shutdown."""
    logger.info("Application shutting down")
    SESSIONS.clear()


if __name__ == "__main__":
    uvicorn.run(app, host=HOST, port=PORT)
