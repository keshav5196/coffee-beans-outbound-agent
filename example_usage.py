"""
Example usage of the Outbound AI Agent API.

This script demonstrates how to:
1. Initiate an outbound call
2. Check active calls
3. Monitor call status
"""

import requests
import time
from typing import Optional

# Base URL of the API
BASE_URL = "http://localhost:8000"


def initiate_call(phone_number: str) -> Optional[str]:
    """Initiate an outbound call to a given phone number.

    Args:
        phone_number: Phone number to call (e.g., "+1234567890")

    Returns:
        Call SID if successful, None otherwise
    """
    try:
        response = requests.post(
            f"{BASE_URL}/call/initiate",
            json={"to": phone_number},
        )
        response.raise_for_status()

        data = response.json()
        call_sid = data.get("call_sid")
        print(f"✓ Call initiated: {call_sid}")
        print(f"  Phone: {phone_number}")
        print(f"  Status: {data.get('status')}")

        return call_sid

    except requests.exceptions.RequestException as e:
        print(f"✗ Error initiating call: {e}")
        return None


def get_active_calls() -> dict:
    """Get all active calls.

    Returns:
        Dictionary with active calls information
    """
    try:
        response = requests.get(f"{BASE_URL}/calls/active")
        response.raise_for_status()

        data = response.json()
        print(f"✓ Active calls: {data.get('count')}")
        for call_sid in data.get("active_calls", []):
            print(f"  - {call_sid}")

        return data

    except requests.exceptions.RequestException as e:
        print(f"✗ Error getting active calls: {e}")
        return {}


def health_check() -> bool:
    """Check if the API is healthy.

    Returns:
        True if healthy, False otherwise
    """
    try:
        response = requests.get(f"{BASE_URL}/health")
        response.raise_for_status()

        data = response.json()
        print(f"✓ API Status: {data.get('status')}")
        return True

    except requests.exceptions.RequestException as e:
        print(f"✗ API is not responding: {e}")
        return False


def main():
    """Run example usage."""
    print("=" * 50)
    print("Outbound AI Agent - Example Usage")
    print("=" * 50)
    print()

    # Step 1: Check API health
    print("Step 1: Checking API health...")
    if not health_check():
        print("Make sure the API is running: python main.py")
        return
    print()

    # Step 2: Check active calls
    print("Step 2: Checking active calls...")
    get_active_calls()
    print()

    # Step 3: Initiate a call
    print("Step 3: Initiating a call...")
    print("(Replace with your phone number)")
    phone_number = input("Enter phone number to call (e.g., +1234567890): ").strip()

    if not phone_number:
        print("No phone number provided")
        return

    call_sid = initiate_call(phone_number)

    if call_sid:
        print()
        print("📞 Call initiated! The agent will call the provided number.")
        print("When they pick up, they'll hear a greeting and can talk to the agent.")
        print()

        # Monitor call
        print("Monitoring call for 30 seconds...")
        for i in range(6):
            time.sleep(5)
            print(f"  Check {i+1}/6...")
            get_active_calls()

        print()
        print("Example complete!")


if __name__ == "__main__":
    main()
