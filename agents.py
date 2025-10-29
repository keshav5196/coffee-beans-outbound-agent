from typing import Optional
from langgraph.graph import StateGraph, START, END
from langgraph.types import Command
from typing_extensions import TypedDict


class ConversationState(TypedDict):
    """State for the conversation agent."""
    messages: list[dict]  # List of {"role": "user" or "assistant", "content": str}
    user_input: str
    response: str


def process_user_input(state: ConversationState) -> Command[ConversationState]:
    """Process user input and generate a response."""
    user_message = state["user_input"]

    # Dummy agent logic - in production, replace with actual LLM call
    # For now, we'll create simple rule-based responses
    response = generate_dummy_response(user_message)

    # Update state
    messages = state.get("messages", [])
    messages.append({"role": "user", "content": user_message})
    messages.append({"role": "assistant", "content": response})

    return Command(
        update={
            "messages": messages,
            "response": response,
        },
        goto=END,
    )


def generate_dummy_response(user_input: str) -> str:
    """Generate a dummy response based on user input.

    This is a placeholder for a real LLM. Replace with actual LLM integration.
    """
    user_input_lower = user_input.lower()

    # Simple rule-based responses
    if any(word in user_input_lower for word in ["hello", "hi", "hey"]):
        return "Hello! I'm an AI assistant. How can I help you today?"

    if any(word in user_input_lower for word in ["name", "who are you"]):
        return "I'm an AI assistant created to help you through outbound calls. What can I do for you?"

    if any(word in user_input_lower for word in ["help", "what can you do"]):
        return "I can assist you with information, answer questions, or just have a conversation. What would you like to talk about?"

    if any(word in user_input_lower for word in ["thanks", "thank you", "appreciate"]):
        return "You're welcome! Is there anything else I can help you with?"

    if any(word in user_input_lower for word in ["goodbye", "bye", "thanks bye"]):
        return "Goodbye! Thanks for chatting with me. Have a great day!"

    # Default response
    return f"Thanks for saying that. Could you tell me more about what you meant by '{user_input}'?"


def create_agent() -> StateGraph:
    """Create and compile the conversation agent."""
    # Create the state graph
    graph = StateGraph(ConversationState)

    # Add nodes
    graph.add_node("process_input", process_user_input)

    # Set entry point
    graph.add_edge(START, "process_input")

    # Compile the graph
    agent = graph.compile()
    return agent


# Create the agent instance
agent = create_agent()


def get_agent_response(user_message: str, conversation_history: Optional[list[dict]] = None) -> str:
    """Get a response from the agent.

    Args:
        user_message: The user's input message
        conversation_history: Optional list of previous messages

    Returns:
        The agent's response as a string
    """
    state = ConversationState(
        messages=conversation_history or [],
        user_input=user_message,
        response="",
    )

    result = agent.invoke(state)
    return result.get("response", "I didn't understand that. Could you please repeat?")
