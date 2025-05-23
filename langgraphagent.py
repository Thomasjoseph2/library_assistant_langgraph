from typing import Annotated, Dict
from typing_extensions import TypedDict
from library_tools import search_books, get_user_info, place_order,get_user_orders, get_total_orders, get_total_users
from langgraph.graph.message import add_messages
from langgraph.graph import StateGraph, START, END
from langchain_google_genai import ChatGoogleGenerativeAI
from dotenv import load_dotenv
import os
from langgraph.prebuilt import ToolNode, tools_condition
from langchain_core.tools import tool

# Load environment variables
load_dotenv()

# Define state
class State(TypedDict):
    messages: Annotated[list, add_messages]
    mode: str
    order_data: Dict[str, str]
    current_field: str

# Define start_order_placement tool
@tool
def start_order_placement():
    """Initiates the order placement process."""
    return {"mode": "order_placement", "order_data": {}, "current_field": "title"}

# Define tools including place_order (assuming it's imported from another file)
tools = [
    search_books,
    get_user_info,
    get_user_orders,
    get_total_orders,
    get_total_users,
    start_order_placement,
    place_order  
]

# Initialize LLM
llm = ChatGoogleGenerativeAI(
    model="gemini-2.0-flash",
    google_api_key=os.getenv("GOOGLE_API_KEY"),
    temperature=0.7
)
llm_with_tools = llm.bind_tools(tools=tools)

# Define chatbot node
def chatbot(state: State):
    return {"messages": [llm_with_tools.invoke(state["messages"])]}

# Define order placement node
def order_placement(state: State):
    order_data = state.get("order_data", {})
    current_field = state.get("current_field")
    messages = state["messages"]
    
    # Get the latest user message
    user_input = messages[-1][1] if messages and messages[-1][0] == "user" else None
    
    # List of required fields
    required_fields = ["title", "author", "phone_number", "email"]
    
    if current_field and user_input:
        # Store the user's response
        order_data[current_field] = user_input
        state["order_data"] = order_data
        state["current_field"] = None
    
    # Check for missing fields
    missing_fields = [field for field in required_fields if field not in order_data]
    
    if missing_fields:
        # Ask for the next missing field
        next_field = missing_fields[0]
        question = f"Please provide the {next_field.replace('_', ' ')}."
        state["current_field"] = next_field
        return {"messages": [("assistant", question)]}
    else:
        # All fields collected, place the order
        result = place_order(
            title=order_data["title"],
            author=order_data["author"],
            phone_number=order_data["phone_number"],
            email=order_data["email"]
        )
        # Reset state
        state["mode"] = "normal"
        state["order_data"] = {}
        state["current_field"] = None
        return {"messages": [("assistant", result.get("message", result.get("error", "Order processing failed.")))]}

# Initialize graph
graph_builder = StateGraph(State)

# Add nodes
graph_builder.add_node("chatbot", chatbot)
graph_builder.add_node("tools", ToolNode(tools=tools))
graph_builder.add_node("order_placement", order_placement)

# Define routing function
def route_based_on_mode(state: State):
    return "order_placement" if state.get("mode") == "order_placement" else "chatbot"

# Add edges
graph_builder.add_conditional_edges(START, route_based_on_mode)
graph_builder.add_conditional_edges("chatbot", tools_condition)
graph_builder.add_edge("tools", "chatbot")
graph_builder.add_edge("order_placement", END)

# Compile graph
graph = graph_builder.compile()

def test_chatbot():
    """Runs an interactive console-based chatbot session for testing."""
    print("Chatbot: Hello! How can I assist you today? (Type 'exit' to quit)")
    # Initialize persistent state
    state = {"messages": [], "mode": "normal", "order_data": {}, "current_field": None}
    while True:
        user_input = input("You: ")
        if user_input.lower() == "exit":
            print("Chatbot: Goodbye!")
            break
        # Add user message to state
        state["messages"].append(("user", user_input))
        print(f"You: {user_input}")
        # Stream the graph with the current state
        events = graph.stream(state, stream_mode="values")
        for event in events:
            # Update state with the latest event
            state = event
            latest_message = event["messages"][-1]
            if isinstance(latest_message, tuple) and latest_message[0] == "assistant":
                print(f"Chatbot: {latest_message[1]}")
            else:
                latest_message.pretty_print()

if __name__ == "__main__":
    test_chatbot()