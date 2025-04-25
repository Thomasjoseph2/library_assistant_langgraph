from typing import Annotated,Optional
from typing_extensions import TypedDict
from library_tools import search_books, get_user_info, place_order,get_user_orders, get_total_orders, get_total_users
from langgraph.graph.message import add_messages
from langgraph.graph import StateGraph, START, END
from langchain_google_genai import ChatGoogleGenerativeAI
from dotenv import load_dotenv
import os
from langgraph.prebuilt import ToolNode, tools_condition

# Load environment variables
load_dotenv()

# Define tools
tools = [
    search_books,
    get_user_info,
    get_user_orders,
    get_total_orders,
    get_total_users,
    place_order
]

# Define state
class State(TypedDict):
    messages: Annotated[list, add_messages]


# Initialize graph
graph_builder = StateGraph(State)

# Initialize LLM
llm = ChatGoogleGenerativeAI(
    model="gemini-1.5-flash",  
    google_api_key=os.getenv("GOOGLE_API_KEY"),
    temperature=0.7
)
llm_with_tools = llm.bind_tools(tools=tools)

# Define chatbot node
def chatbot(state: State):
    return {"messages": [llm_with_tools.invoke(state["messages"])]}

# Add nodes and edges
graph_builder.add_node("chatbot", chatbot)
tool_node = ToolNode(tools=tools)
graph_builder.add_node("tools", tool_node)
graph_builder.add_conditional_edges("chatbot", tools_condition)
graph_builder.add_edge("tools", "chatbot")
graph_builder.add_edge(START, "chatbot")

# Compile graph
graph = graph_builder.compile()

def test_chatbot():
    """
    Runs an interactive console-based chatbot session with persistent memory.
    """
    print("Chatbot: Hello! How can I assist you today? (Type 'exit' to quit)")
    # Initialize persistent state
    state = {"messages": []}
    
    while True:
        user_input = input("You: ")
        if user_input.lower() == "exit":
            print("Chatbot: Goodbye!")
            break
        
        # Add user input to the existing state
        state["messages"].append(("user", user_input))
        print(f"You: {user_input}")
        
        # Stream responses with the current state
        events = graph.stream(state, stream_mode="values")
        
        # Update state with the latest event
        for event in events:
            state = event
            latest_message = event["messages"][-1]
            latest_message.pretty_print()

if __name__ == "__main__":
    test_chatbot()