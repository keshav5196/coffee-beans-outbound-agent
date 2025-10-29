import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Twilio Configuration
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_PHONE_NUMBER = os.getenv("TWILIO_PHONE_NUMBER")

# Server Configuration
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", 8000))
NGROK_URL = os.getenv("NGROK_URL", "http://localhost:8000")

# Agent Configuration
AGENT_GREETING = "Hello! This is an AI assistant. How can I help you today?"
AGENT_MODEL = "gpt-4"  # Placeholder - not used directly since we're using dummy agent

# Validate required configs
if not all([TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_PHONE_NUMBER]):
    print("Warning: Missing Twilio credentials. Please set environment variables.")
