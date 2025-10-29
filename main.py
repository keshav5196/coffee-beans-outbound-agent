import json
import asyncio
from typing import Optional
import logging

from fastapi import FastAPI, WebSocket, BackgroundTasks, HTTPException
from fastapi.responses import JSONResponse
from twilio.rest import Client
from twilio.twiml.voice_response import VoiceResponse
import uvicorn

from config import (
    TWILIO_ACCOUNT_SID,
    TWILIO_AUTH_TOKEN,
    TWILIO_PHONE_NUMBER,
    HOST,
    PORT,
    NGROK_URL,
    AGENT_GREETING,
)
from agents import get_agent_response

# Logging setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(title="Outbound AI Agent")

# Twilio client
twilio_client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)

# In-memory storage for active calls
# Key: CallSid, Value: {"phone_number": str, "messages": list, "connected": bool}
active_calls = {}


@app.post("/call/initiate")
async def initiate_call(phone_number: str, background_tasks: BackgroundTasks):
    """Initiate an outbound call to a given phone number.

    This endpoint starts the call and sets up the voice response webhook.
    """
    try:
        logger.info(f"Initiating call to {phone_number}")

        # Create the call with webhook
        call = twilio_client.calls.create(
            to=phone_number,
            from_=TWILIO_PHONE_NUMBER,
            url=f"{NGROK_URL}/twiml/initial",
            method="POST",
        )

        # Store call info
        active_calls[call.sid] = {
            "phone_number": phone_number,
            "messages": [],
            "connected": False,
        }

        logger.info(f"Call created with SID: {call.sid}")

        return JSONResponse(
            status_code=200,
            content={"call_sid": call.sid, "status": "initiated"},
        )

    except Exception as e:
        logger.error(f"Error initiating call: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/twiml/initial")
async def handle_initial_twiml():
    """Handle the initial TwiML response for the call.

    This is the first webhook called when the call is initiated.
    We set up the voice channel and start gathering input.
    """
    response = VoiceResponse()

    # Use Say to play the greeting
    response.say(
        AGENT_GREETING,
        voice="alice",
    )

    # Start recording
    response.record(
        action="/handle/recording",
        method="POST",
        timeout=10,
        max_speech_time=30,
    )

    return response.to_xml()


@app.post("/handle/recording")
async def handle_recording(
    CallSid: str = None,
    RecordingUrl: str = None,
    SpeechResult: str = None,
):
    """Handle user's spoken input from Twilio Speech Recognition.

    When user speaks, Twilio captures their speech and sends it here.
    """
    try:
        logger.info(f"Recording received for call {CallSid}: {SpeechResult}")

        if CallSid not in active_calls:
            logger.warning(f"Call SID {CallSid} not found in active calls")
            return handle_end_call()

        call_info = active_calls[CallSid]

        # Get agent response
        agent_response = get_agent_response(
            SpeechResult,
            conversation_history=call_info["messages"],
        )

        # Store in conversation history
        call_info["messages"].append({"role": "user", "content": SpeechResult})
        call_info["messages"].append({"role": "assistant", "content": agent_response})

        logger.info(f"Agent response: {agent_response}")

        # Prepare response
        response = VoiceResponse()

        # Say the agent's response
        response.say(agent_response, voice="alice")

        # Record next user input
        response.record(
            action="/handle/recording",
            method="POST",
            timeout=10,
            max_speech_time=30,
        )

        return response.to_xml()

    except Exception as e:
        logger.error(f"Error handling recording: {str(e)}")
        return handle_end_call()


def handle_end_call():
    """Generate TwiML to end the call."""
    response = VoiceResponse()
    response.say("Thank you for calling. Goodbye!", voice="alice")
    response.hangup()
    return response.to_xml()


@app.post("/call/status")
async def call_status(CallSid: str = None, CallStatus: str = None):
    """Webhook to track call status changes."""
    logger.info(f"Call {CallSid} status: {CallStatus}")

    if CallStatus == "completed" or CallStatus == "failed":
        # Clean up
        if CallSid in active_calls:
            call_info = active_calls.pop(CallSid)
            logger.info(f"Call {CallSid} ended. Conversation history: {call_info['messages']}")

    return JSONResponse(status_code=200, content={"status": "ok"})


@app.get("/calls/active")
async def get_active_calls():
    """Get all active calls."""
    return JSONResponse(
        status_code=200,
        content={
            "active_calls": list(active_calls.keys()),
            "count": len(active_calls),
        },
    )


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return JSONResponse(status_code=200, content={"status": "healthy"})


@app.on_event("startup")
async def startup_event():
    """Run on application startup."""
    logger.info("Application started")
    logger.info(f"Twilio Phone Number: {TWILIO_PHONE_NUMBER}")


@app.on_event("shutdown")
async def shutdown_event():
    """Run on application shutdown."""
    logger.info("Application shutting down")
    active_calls.clear()


if __name__ == "__main__":
    uvicorn.run(app, host=HOST, port=PORT)
