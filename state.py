"""State schema for the LangGraph agent."""

from typing import Annotated, TypedDict
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages


class AgentState(TypedDict):
    """State for the voice agent conversation.

    This state is passed between all nodes in the graph and maintains
    the complete conversation context.
    """

    # Conversation history - automatically managed by add_messages
    messages: Annotated[list[BaseMessage], add_messages]

    # Supervisor routing decision
    next_worker: str  # Which worker node to call next

    # Customer information gathering
    customer_info: dict  # {company_name, role, industry}
    pain_points: list[str]  # Customer's stated challenges
    info_gathered: bool  # Flag to track if we've done initial discovery

    # Qualification tracking
    qualification_data: dict  # Deeper qualification info
    is_qualified_lead: bool  # Whether this is a good lead

    # Conversation metadata
    discussed_services: list[str]  # Which services we've talked about
    conversation_stage: str  # greeting, discovery, presentation, closing
    should_end: bool  # Signal to end conversation
    turn_count: int  # Number of back-and-forth exchanges

    # Call metadata
    call_sid: str  # Twilio call identifier
