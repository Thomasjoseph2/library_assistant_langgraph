from typing import TypedDict, Annotated, List, Dict, Optional
from langgraph.graph import StateGraph, START,END
# from langchain_openai import ChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI 
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage
from langchain_core.prompts import ChatPromptTemplate
from library_tools import search_books, get_user_info, get_user_orders,get_total_orders,get_total_users
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

# Define the state for the conversation
class ChatState(TypedDict):
    messages: Annotated[List[HumanMessage | AIMessage | ToolMessage], "Messages in the conversation"]
    user_email: Optional[str]  


llm = ChatGoogleGenerativeAI(
    model="gemini-1.5-flash",  
    google_api_key=os.getenv("GOOGLE_API_KEY"),
    temperature=0.7  
)
# Define the tools
tools = [
    search_books,
    get_user_info,
    get_user_orders,
    get_total_orders,
    get_total_users
]

# Bind tools to the LLM
llm_with_tools = llm.bind_tools(tools)

# Define the prompt template
prompt = ChatPromptTemplate.from_messages([
    ("system", """You are a helpful library assistant for a library system. Use the provided tools to answer questions about books, users, checkouts, returns, and orders. If a user's email is mentioned, store it for context in follow-up questions. If a tool is needed, call it with the appropriate inputs. If no tool is needed, respond directly. Be concise and friendly."""),
    ("placeholder", "{messages}"),
])

# Node to process user input and decide whether to call tools
def call_model(state: ChatState) -> ChatState:
    messages = state["messages"]
    user_email = state.get("user_email")

    # Extract email from the latest message if provided
    latest_message = messages[-1].content.lower()
    if "my email is" in latest_message or "email:" in latest_message:
        for part in latest_message.split():
            if "@" in part and "." in part:
                state["user_email"] = part.strip(",.")
                break

    # Prepare the prompt
    chain = prompt | llm_with_tools
    response = chain.invoke({"messages": messages})

    # Add the response to the state
    state["messages"].append(response)
    return state

# Node to handle tool calls
def call_tools(state: ChatState) -> ChatState:
    messages = state["messages"]
    last_message = messages[-1]

    # Check if the last message contains tool calls
    if hasattr(last_message, "tool_calls") and last_message.tool_calls:
        for tool_call in last_message.tool_calls:
            tool_name = tool_call["name"]
            tool_args = tool_call["args"]

            # Adjust arguments based on stored user_email if needed
            if tool_name in ["checkout_book", "get_user_orders"] and "user_email" not in tool_args:
                if state.get("user_email"):
                    tool_args["user_email"] = state["user_email"]

            # Find and invoke the tool
            for tool in tools:
                if tool.name == tool_name:
                    try:
                        result = tool.invoke(tool_args)
                        state["messages"].append(ToolMessage(
                            content=str(result),
                            tool_call_id=tool_call["id"]
                        ))
                    except Exception as e:
                        state["messages"].append(ToolMessage(
                            content=f"Error calling {tool_name}: {str(e)}",
                            tool_call_id=tool_call["id"]
                        ))
                    break
    return state

# Node to generate the final response
def generate_response(state: ChatState) -> ChatState:
    messages = state["messages"]
    tool_results = [msg for msg in messages if isinstance(msg, ToolMessage)]

    if tool_results:
        # Summarize tool results for the user
        last_tool_result = tool_results[-1].content
        response = llm.invoke([
            HumanMessage(content=f"Based on the tool result: {last_tool_result}, provide a concise, friendly response to the user.")
        ])
        state["messages"].append(AIMessage(content=response.content))
    else:
        # If no tool results, the last message is already the response
        pass
    return state

# Define the condition to decide whether to call tools
def should_call_tools(state: ChatState) -> str:
    last_message = state["messages"][-1]
    if hasattr(last_message, "tool_calls") and last_message.tool_calls:
        return "call_tools"
    return "generate_response"

# Build the graph
workflow = StateGraph(ChatState)

# Add nodes
workflow.add_node("call_model", call_model)
workflow.add_node("call_tools", call_tools)
workflow.add_node("generate_response", generate_response)

# Define edges
workflow.set_entry_point("call_model")
workflow.add_conditional_edges("call_model", should_call_tools, {
    "call_tools": "call_tools",
    "generate_response": "generate_response"
})
workflow.add_edge("call_tools", "generate_response")
workflow.add_edge("generate_response", END)

# Compile the graph
graph = workflow.compile()

# Command-line interface for testing
def run_chatbot():
    print("Welcome to the Library Chatbot! Type 'exit' to quit.")
    state = {"messages": [], "user_email": None}
    
    while True:
        user_input = input("\nYou: ")
        if user_input.lower() == "exit":
            print("Goodbye!")
            break
        
        # Add user message to state
        state["messages"].append(HumanMessage(content=user_input))
        
        # Run the graph
        final_state = graph.invoke(state)
        
        # Get the latest response
        response = final_state["messages"][-1].content
        print(f"Bot: {response}")
        
        # Update state for the next iteration
        state = final_state

if __name__ == "__main__":
    run_chatbot()

