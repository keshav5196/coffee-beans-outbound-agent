"""LangGraph agent with supervisor pattern for voice conversations."""

from typing import Literal, Optional
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, BaseMessage
from langchain_groq import ChatGroq
from langgraph.graph import StateGraph, END
import logging

from config import settings
from state import AgentState
from prompts import (
    SUPERVISOR_PROMPT,
    INFORMATION_GATHERING_PROMPT,
    SERVICE_INFO_PROMPT,
    QUALIFICATION_PROMPT,
    SCHEDULING_PROMPT,
    COFFEEBEANS_SERVICES,
    get_service_info_for_prompt,
)

# Setup logging
logger = logging.getLogger(__name__)


# =============================================================================
# LLM SETUP
# =============================================================================

llm = ChatGroq(
    model=settings.groq_model,
    api_key=settings.groq_api_key,
    temperature=0.7,
)


# =============================================================================
# SUPERVISOR TOOLS DEFINITION
# =============================================================================

supervisor_tools = [
    {
        "type": "function",
        "function": {
            "name": "gather_information",
            "description": "Ask customer about their company, role, industry, and challenges. Use this FIRST when customer agrees to chat. Only call once per conversation.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "provide_service_info",
            "description": "Provide information about CoffeeBeans services, tailored to customer's industry and needs if known.",
            "parameters": {
                "type": "object",
                "properties": {
                    "service_type": {
                        "type": "string",
                        "enum": ["AI", "Blockchain", "DevOps", "QaaS", "BigData", "General"],
                        "description": "The type of service to discuss"
                    }
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "qualify_customer",
            "description": "Ask deeper qualifying questions about budget, timeline, and decision process. Use after customer shows strong interest.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "schedule_callback",
            "description": "Schedule a follow-up call or consultation. Use when customer is busy or wants to continue later.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "end_call",
            "description": "End the conversation politely. Use when customer wants to disconnect or conversation is complete.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    }
]


# =============================================================================
# SUPERVISOR NODE
# =============================================================================

def supervisor_node(state: AgentState) -> AgentState:
    """Supervisor that decides which worker node to call next.

    Uses function calling to intelligently route to appropriate worker.
    """
    # Build context for supervisor
    context_parts = [
        f"Turn count: {state.get('turn_count', 0)}",
        f"Conversation stage: {state.get('conversation_stage', 'greeting')}",
        f"Info gathered: {state.get('info_gathered', False)}",
    ]

    if state.get('customer_info'):
        context_parts.append(f"Customer info: {state['customer_info']}")

    if state.get('pain_points'):
        context_parts.append(f"Pain points: {state['pain_points']}")

    if state.get('discussed_services'):
        context_parts.append(f"Discussed services: {state['discussed_services']}")

    context = "\n".join(context_parts)

    # Create messages for supervisor
    messages = [
        SystemMessage(content=SUPERVISOR_PROMPT),
        SystemMessage(content=f"Current context:\n{context}"),
    ]
    messages.extend(state["messages"])

    # Call LLM with function calling
    response = llm.bind_tools(supervisor_tools).invoke(messages)

    # Extract function call if present
    next_worker = "provide_service_info"  # Default

    if response.tool_calls:
        tool_call = response.tool_calls[0]
        next_worker = tool_call["name"]

        # Store any parameters (like service_type)
        if "service_type" in tool_call.get("args", {}):
            state["service_type"] = tool_call["args"]["service_type"]

    # Update state
    state["next_worker"] = next_worker

    return state


# =============================================================================
# WORKER NODES
# =============================================================================

def information_gathering_node(state: AgentState) -> AgentState:
    """Gather initial information about the customer."""
    # Don't ask again if we already gathered info
    if state.get("info_gathered"):
        state["next_worker"] = "provide_service_info"
        return state

    # Create prompt for information gathering
    messages = [
        SystemMessage(content=INFORMATION_GATHERING_PROMPT),
    ]

    # Get the last user message for context
    user_messages = [m for m in state["messages"] if isinstance(m, HumanMessage)]
    if user_messages:
        messages.append(user_messages[-1])

    # Generate response
    response = llm.invoke(messages)

    # Add AI response to messages
    state["messages"].append(AIMessage(content=response.content))

    # Try to extract info from conversation
    # In a real system, you'd use NER or structured extraction here
    # For now, we'll just mark it as attempted
    state["info_gathered"] = True
    state["conversation_stage"] = "discovery"

    return state


def service_info_node(state: AgentState) -> AgentState:
    """Provide information about CoffeeBeans services."""
    # Build personalized context
    context_parts = [get_service_info_for_prompt()]

    if state.get("customer_info"):
        customer_info = state["customer_info"]
        context_parts.append(f"\nCustomer context:")
        context_parts.append(f"- Company: {customer_info.get('company_name', 'Unknown')}")
        context_parts.append(f"- Role: {customer_info.get('role', 'Unknown')}")
        context_parts.append(f"- Industry: {customer_info.get('industry', 'Unknown')}")

    if state.get("pain_points"):
        context_parts.append(f"- Pain points: {', '.join(state['pain_points'])}")

    service_type = state.get("service_type", "General")
    context_parts.append(f"\nFocus on: {service_type}")

    context = "\n".join(context_parts)

    # Create prompt
    prompt = SERVICE_INFO_PROMPT.format(services_data=context)
    messages = [
        SystemMessage(content=prompt),
    ]

    # Get last user message
    user_messages = [m for m in state["messages"] if isinstance(m, HumanMessage)]
    if user_messages:
        messages.append(user_messages[-1])

    # Generate response
    response = llm.invoke(messages)

    # Add to discussed services
    if service_type not in state.get("discussed_services", []):
        if "discussed_services" not in state:
            state["discussed_services"] = []
        state["discussed_services"].append(service_type)

    # Add AI response
    state["messages"].append(AIMessage(content=response.content))
    state["conversation_stage"] = "presentation"

    return state


def qualification_node(state: AgentState) -> AgentState:
    """Ask qualifying questions to assess lead quality."""
    messages = [
        SystemMessage(content=QUALIFICATION_PROMPT),
    ]

    # Add context about what we know
    if state.get("customer_info") or state.get("pain_points"):
        context = "What we know: "
        if state.get("customer_info"):
            context += f"Company: {state['customer_info']}, "
        if state.get("pain_points"):
            context += f"Challenges: {state['pain_points']}"
        messages.append(SystemMessage(content=context))

    # Get last user message
    user_messages = [m for m in state["messages"] if isinstance(m, HumanMessage)]
    if user_messages:
        messages.append(user_messages[-1])

    # Generate response
    response = llm.invoke(messages)

    # Add AI response
    state["messages"].append(AIMessage(content=response.content))
    state["conversation_stage"] = "qualification"

    return state


def scheduling_node(state: AgentState) -> AgentState:
    """Schedule a callback or next meeting."""
    messages = [
        SystemMessage(content=SCHEDULING_PROMPT),
    ]

    # Get last user message
    user_messages = [m for m in state["messages"] if isinstance(m, HumanMessage)]
    if user_messages:
        messages.append(user_messages[-1])

    # Generate response
    response = llm.invoke(messages)

    # Add AI response
    state["messages"].append(AIMessage(content=response.content))
    state["conversation_stage"] = "closing"
    state["should_end"] = True  # After scheduling, prepare to end

    return state


def end_node(state: AgentState) -> AgentState:
    """End the conversation politely."""
    messages = [
        SystemMessage(content="You are ending the call. Provide a brief, polite closing statement.")
    ]

    # Get last user message
    user_messages = [m for m in state["messages"] if isinstance(m, HumanMessage)]
    if user_messages:
        messages.append(user_messages[-1])

    # Generate closing response
    response = llm.invoke(messages)

    # Add AI response
    state["messages"].append(AIMessage(content=response.content))
    state["should_end"] = True

    return state


# =============================================================================
# ROUTING FUNCTIONS
# =============================================================================

def route_supervisor(
    state: AgentState,
) -> Literal["gather_information", "service_info", "qualification", "scheduling", "end"]:
    """Route from supervisor to appropriate worker node."""
    next_worker = state.get("next_worker", "service_info")

    # Map supervisor decisions to node names
    routing_map = {
        "gather_information": "gather_information",
        "provide_service_info": "service_info",
        "qualify_customer": "qualification",
        "schedule_callback": "scheduling",
        "end_call": "end",
    }

    return routing_map.get(next_worker, "service_info")


def should_continue(state: AgentState) -> Literal["supervisor", "end"]:
    """Decide if conversation should continue after worker node.

    In request-response mode (notebook/HTTP), we end after each worker completes
    so the user can provide the next message. Each user message triggers a new
    invoke cycle: supervisor -> worker -> end.
    """
    # Always end after worker completes - wait for next user message
    # This prevents infinite loops in request-response patterns
    return "end"


# =============================================================================
# GRAPH CONSTRUCTION
# =============================================================================

def create_agent() -> StateGraph:
    """Create and compile the LangGraph agent with supervisor pattern."""
    # Initialize graph
    workflow = StateGraph(AgentState)

    # Add nodes
    workflow.add_node("supervisor", supervisor_node)
    workflow.add_node("gather_information", information_gathering_node)
    workflow.add_node("service_info", service_info_node)
    workflow.add_node("qualification", qualification_node)
    workflow.add_node("scheduling", scheduling_node)
    workflow.add_node("end", end_node)

    # Set entry point
    workflow.set_entry_point("supervisor")

    # Add conditional edges from supervisor to workers
    workflow.add_conditional_edges(
        "supervisor",
        route_supervisor,
        {
            "gather_information": "gather_information",
            "service_info": "service_info",
            "qualification": "qualification",
            "scheduling": "scheduling",
            "end": "end",
        }
    )

    # All worker nodes return to end (for request-response pattern)
    workflow.add_conditional_edges(
        "gather_information",
        should_continue,
        {"supervisor": "supervisor", "end": END}
    )
    workflow.add_conditional_edges(
        "service_info",
        should_continue,
        {"supervisor": "supervisor", "end": END}
    )
    workflow.add_conditional_edges(
        "qualification",
        should_continue,
        {"supervisor": "supervisor", "end": END}
    )
    workflow.add_conditional_edges(
        "scheduling",
        should_continue,
        {"supervisor": "supervisor", "end": END}
    )

    # End node goes to END
    workflow.add_edge("end", END)

    # Compile the graph
    return workflow.compile()


# Create the agent instance
agent = create_agent()


# =============================================================================
# MAIN ENTRY POINT FOR MAIN.PY COMPATIBILITY
# =============================================================================

def get_agent_response(user_message: str, conversation_history: Optional[list[dict]] = None, call_sid: str = "unknown") -> str:
    """Get a response from the agent.

    This function maintains compatibility with main.py while using the new
    supervisor pattern agent.

    Args:
        user_message: The user's input message
        conversation_history: Optional list of previous messages in legacy format
        call_sid: Twilio call identifier

    Returns:
        The agent's response as a string
    """
    try:
        # Convert legacy conversation history to LangChain messages if provided
        messages = []
        if conversation_history:
            for msg in conversation_history:
                if isinstance(msg, dict):
                    if msg.get("role") == "user":
                        messages.append(HumanMessage(content=msg.get("content", "")))
                    elif msg.get("role") == "assistant":
                        messages.append(AIMessage(content=msg.get("content", "")))

        # Add the current user message
        messages.append(HumanMessage(content=user_message))

        # Create initial state
        state: AgentState = {
            "messages": messages,
            "next_worker": "gather_information",
            "customer_info": {},
            "pain_points": [],
            "info_gathered": False,
            "qualification_data": {},
            "is_qualified_lead": False,
            "discussed_services": [],
            "conversation_stage": "greeting" if not messages else "ongoing",
            "should_end": False,
            "turn_count": len([m for m in messages if isinstance(m, HumanMessage)]),
            "call_sid": call_sid,
        }

        # Invoke the agent
        result = agent.invoke(state)

        # Extract the last AI message as the response
        ai_messages = [m for m in result["messages"] if isinstance(m, AIMessage)]
        if ai_messages:
            response = ai_messages[-1].content
            logger.info(f"Agent response for {call_sid}: {response[:100]}...")
            return response
        else:
            logger.warning(f"No AI message found in result for {call_sid}")
            return "I didn't understand that. Could you please repeat?"

    except Exception as e:
        logger.error(f"Error in get_agent_response for {call_sid}: {str(e)}")
        return f"I apologize, but I encountered an error. Could you please repeat that?"
