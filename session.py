"""Session management for maintaining conversation state across Twilio webhooks."""

from datetime import datetime, timedelta
from typing import Optional
from state import AgentState


class SessionManager:
    """Manages conversation sessions for Twilio calls.

    Since Twilio webhooks are stateless, we need to maintain conversation
    state between calls. This simple in-memory store handles that.

    For production, replace with Redis or database.
    """

    def __init__(self, timeout_minutes: int = 5):
        """Initialize session manager.

        Args:
            timeout_minutes: How long to keep sessions in memory
        """
        self._sessions: dict[str, dict] = {}
        self._timeout = timedelta(minutes=timeout_minutes)

    def create_session(self, call_sid: str) -> AgentState:
        """Create a new conversation session.

        Args:
            call_sid: Twilio call identifier

        Returns:
            Initial agent state
        """
        initial_state: AgentState = {
            "messages": [],
            "next_worker": "gather_information",
            "customer_info": {},
            "pain_points": [],
            "info_gathered": False,
            "qualification_data": {},
            "is_qualified_lead": False,
            "discussed_services": [],
            "conversation_stage": "greeting",
            "should_end": False,
            "turn_count": 0,
            "call_sid": call_sid,
        }

        self._sessions[call_sid] = {
            "state": initial_state,
            "created_at": datetime.now(),
            "last_accessed": datetime.now(),
        }

        return initial_state

    def get_session(self, call_sid: str) -> Optional[AgentState]:
        """Retrieve session state.

        Args:
            call_sid: Twilio call identifier

        Returns:
            Agent state if session exists and not expired, None otherwise
        """
        if call_sid not in self._sessions:
            return None

        session = self._sessions[call_sid]

        # Check if session expired
        if datetime.now() - session["last_accessed"] > self._timeout:
            self.delete_session(call_sid)
            return None

        # Update last accessed time
        session["last_accessed"] = datetime.now()

        return session["state"]

    def update_session(self, call_sid: str, state: AgentState) -> None:
        """Update session state.

        Args:
            call_sid: Twilio call identifier
            state: Updated agent state
        """
        if call_sid in self._sessions:
            self._sessions[call_sid]["state"] = state
            self._sessions[call_sid]["last_accessed"] = datetime.now()

    def delete_session(self, call_sid: str) -> None:
        """Delete a session.

        Args:
            call_sid: Twilio call identifier
        """
        if call_sid in self._sessions:
            del self._sessions[call_sid]

    def cleanup_expired_sessions(self) -> int:
        """Remove all expired sessions.

        Returns:
            Number of sessions cleaned up
        """
        now = datetime.now()
        expired = [
            call_sid
            for call_sid, session in self._sessions.items()
            if now - session["last_accessed"] > self._timeout
        ]

        for call_sid in expired:
            del self._sessions[call_sid]

        return len(expired)

    def get_active_session_count(self) -> int:
        """Get count of active sessions.

        Returns:
            Number of active sessions
        """
        return len(self._sessions)


# Global session manager instance
session_manager = SessionManager()
