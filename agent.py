# from typing import TypedDict, Annotated, List, Dict, Optional
# from langgraph.graph import StateGraph, END
# from langchain_openai import ChatOpenAI
# from langchain_core.messages import HumanMessage, AIMessage, ToolMessage
# from langchain_core.prompts import ChatPromptTemplate
# from library_tools import search_books, get_user_info, checkout_book, return_book, get_user_orders,get_total_orders,get_total_users
# from dotenv import load_dotenv
# import os

# # Load environment variables
# load_dotenv()

# # Define the state for the conversation
# class ChatState(TypedDict):
#     messages: Annotated[List[HumanMessage | AIMessage | ToolMessage], "Messages in the conversation"]
#     user_email: Optional[str]  # Store user's email for context (e.g., for checkout or orders)

# # Initialize the LLM
# llm = ChatOpenAI(model="gpt-4o-mini", api_key=os.getenv("OPENAI_API_KEY"))

# # Define the tools
# tools = [
#     search_books,
#     get_user_info,
#     checkout_book,
#     return_book,
#     get_user_orders,
#     get_total_orders,
#     get_total_users
# ]

# # Bind tools to the LLM
# llm_with_tools = llm.bind_tools(tools)

# # Define the prompt template
# prompt = ChatPromptTemplate.from_messages([
#     ("system", """You are a helpful library assistant for a library system. Use the provided tools to answer questions about books, users, checkouts, returns, and orders. If a user's email is mentioned, store it for context in follow-up questions. If a tool is needed, call it with the appropriate inputs. If no tool is needed, respond directly. Be concise and friendly."""),
#     ("placeholder", "{messages}"),
# ])

# # Node to process user input and decide whether to call tools
# def call_model(state: ChatState) -> ChatState:
#     messages = state["messages"]
#     user_email = state.get("user_email")

#     # Extract email from the latest message if provided
#     latest_message = messages[-1].content.lower()
#     if "my email is" in latest_message or "email:" in latest_message:
#         for part in latest_message.split():
#             if "@" in part and "." in part:
#                 state["user_email"] = part.strip(",.")
#                 break

#     # Prepare the prompt
#     chain = prompt | llm_with_tools
#     response = chain.invoke({"messages": messages})

#     # Add the response to the state
#     state["messages"].append(response)
#     return state

# # Node to handle tool calls
# def call_tools(state: ChatState) -> ChatState:
#     messages = state["messages"]
#     last_message = messages[-1]

#     # Check if the last message contains tool calls
#     if hasattr(last_message, "tool_calls") and last_message.tool_calls:
#         for tool_call in last_message.tool_calls:
#             tool_name = tool_call["name"]
#             tool_args = tool_call["args"]

#             # Adjust arguments based on stored user_email if needed
#             if tool_name in ["checkout_book", "get_user_orders"] and "user_email" not in tool_args:
#                 if state.get("user_email"):
#                     tool_args["user_email"] = state["user_email"]

#             # Find and invoke the tool
#             for tool in tools:
#                 if tool.name == tool_name:
#                     try:
#                         result = tool.invoke(tool_args)
#                         state["messages"].append(ToolMessage(
#                             content=str(result),
#                             tool_call_id=tool_call["id"]
#                         ))
#                     except Exception as e:
#                         state["messages"].append(ToolMessage(
#                             content=f"Error calling {tool_name}: {str(e)}",
#                             tool_call_id=tool_call["id"]
#                         ))
#                     break
#     return state

# # Node to generate the final response
# def generate_response(state: ChatState) -> ChatState:
#     messages = state["messages"]
#     tool_results = [msg for msg in messages if isinstance(msg, ToolMessage)]

#     if tool_results:
#         # Summarize tool results for the user
#         last_tool_result = tool_results[-1].content
#         response = llm.invoke([
#             HumanMessage(content=f"Based on the tool result: {last_tool_result}, provide a concise, friendly response to the user.")
#         ])
#         state["messages"].append(AIMessage(content=response.content))
#     else:
#         # If no tool results, the last message is already the response
#         pass
#     return state

# # Define the condition to decide whether to call tools
# def should_call_tools(state: ChatState) -> str:
#     last_message = state["messages"][-1]
#     if hasattr(last_message, "tool_calls") and last_message.tool_calls:
#         return "call_tools"
#     return "generate_response"

# # Build the graph
# workflow = StateGraph(ChatState)

# # Add nodes
# workflow.add_node("call_model", call_model)
# workflow.add_node("call_tools", call_tools)
# workflow.add_node("generate_response", generate_response)

# # Define edges
# workflow.set_entry_point("call_model")
# workflow.add_conditional_edges("call_model", should_call_tools, {
#     "call_tools": "call_tools",
#     "generate_response": "generate_response"
# })
# workflow.add_edge("call_tools", "generate_response")
# workflow.add_edge("generate_response", END)

# # Compile the graph
# graph = workflow.compile()

# # Command-line interface for testing
# def run_chatbot():
#     print("Welcome to the Library Chatbot! Type 'exit' to quit.")
#     state = {"messages": [], "user_email": None}
    
#     while True:
#         user_input = input("\nYou: ")
#         if user_input.lower() == "exit":
#             print("Goodbye!")
#             break
        
#         # Add user message to state
#         state["messages"].append(HumanMessage(content=user_input))
        
#         # Run the graph
#         final_state = graph.invoke(state)
        
#         # Get the latest response
#         response = final_state["messages"][-1].content
#         print(f"Bot: {response}")
        
#         # Update state for the next iteration
#         state = final_state

# if __name__ == "__main__":
#     run_chatbot()

from typing import List, Optional
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage
from langchain_core.prompts import ChatPromptTemplate
from library_tools import search_books, get_user_info, checkout_book, return_book, get_user_orders, get_total_orders, get_total_users
from dotenv import load_dotenv
import os
import json

# Load environment variables
load_dotenv()

# Initialize the LLM
llm = ChatOpenAI(model="gpt-4o-mini", api_key=os.getenv("OPENAI_API_KEY"))

# Define the tools
tools = {
    "search_books": search_books,
    "get_user_info": get_user_info,
    "checkout_book": checkout_book,
    "return_book": return_book,
    "get_user_orders": get_user_orders,
    "get_total_orders": get_total_orders,
    "get_total_users": get_total_users
}

# Define the prompt template for intent analysis and task execution
prompt = ChatPromptTemplate.from_messages([
    ("system", """You are a helpful library assistant. Analyze the user's input to determine their intent and respond appropriately. You have access to the following tools:

{tool_descriptions}

Steps:
1. Identify the user's intent (e.g., search for books, checkout, return, get orders, etc.).
2. If a tool is needed, select the appropriate tool and specify the arguments in JSON format (e.g., {{"tool": "search_books", "args": {{"query": "Tolkien"}}}}).
3. If no tool is needed, provide a direct response in JSON format (e.g., {{"response": "Your email is not set. Please provide it."}}).
4. If the user mentions an email (e.g., "my email is user@example.com"), store it for context and include it in tool arguments when needed (e.g., for checkout_book, get_user_orders).
5. Be concise, friendly, and clear in your responses.

Conversation history:
{messages}
"""),
])

# Generate tool descriptions for the prompt
tool_descriptions = "\n".join(
    f"- {name}: {tool.__doc__ or 'No description available'}" for name, tool in tools.items()
)

# State to track conversation and context
class ChatState:
    def __init__(self):
        self.messages: List[HumanMessage | AIMessage] = []
        self.user_email: Optional[str] = None

# Function to process user input and execute tasks
def process_input(state: ChatState, user_input: str) -> str:
    # Add user input to messages
    state.messages.append(HumanMessage(content=user_input))

    # Prepare the prompt with tool descriptions and conversation history
    chain = prompt | llm
    response = chain.invoke({
        "tool_descriptions": tool_descriptions,
        "messages": [msg for msg in state.messages]
    })

    # Parse the LLM's response (expected to be JSON)
    try:
        action = json.loads(response.content)
    except json.JSONDecodeError:
        return "Error: Could not parse AI response. Please try again."

    # Handle email extraction if mentioned
    if "email" in user_input.lower():
        for part in user_input.split():
            if "@" in part and "." in part:
                state.user_email = part.strip(",.")
                break

    # Execute the action
    if "tool" in action:
        tool_name = action["tool"]
        tool_args = action.get("args", {})

        # Inject user_email for tools that need it
        if tool_name in ["checkout_book", "get_user_orders"] and "user_email" not in tool_args and state.user_email:
            tool_args["user_email"] = state.user_email

        # Call the tool
        try:
            tool = tools[tool_name]
            result = tool.invoke(tool_args)
            state.messages.append(AIMessage(content=str(result)))
            return f"Tool result: {result}"
        except Exception as e:
            state.messages.append(AIMessage(content=f"Error calling {tool_name}: {str(e)}"))
            return f"Error: {str(e)}"
    elif "response" in action:
        state.messages.append(AIMessage(content=action["response"]))
        return action["response"]
    else:
        state.messages.append(AIMessage(content="Error: Invalid AI response format."))
        return "Error: Invalid AI response format."

# Command-line interface for testing
def run_chatbot():
    print("Welcome to the Dynamic Library Chatbot! Type 'exit' to quit.")
    state = ChatState()

    while True:
        user_input = input("\nYou: ")
        if user_input.lower() == "exit":
            print("Goodbye!")
            break

        # Process the input and get the response
        response = process_input(state, user_input)
        print(f"Bot: {response}")

if __name__ == "__main__":
    run_chatbot()