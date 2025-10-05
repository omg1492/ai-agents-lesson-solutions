from typing import Annotated
from dotenv import load_dotenv
from typing_extensions import TypedDict
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph
from langgraph.graph.message import add_messages
from langchain_core.tools import tool
from langchain_community.tools.tavily_search import TavilySearchResults
from langchain_community.tools.arxiv.tool import ArxivQueryRun
from langchain_community.utilities.wolfram_alpha import WolframAlphaAPIWrapper
from langchain_community.tools.wolfram_alpha.tool import WolframAlphaQueryRun
from langchain_core.tools import Tool
from langchain_experimental.utilities import PythonREPL
import json
from langgraph.prebuilt import ToolNode
from typing import Literal
from visualizer import visualize
load_dotenv()


# Model
llm = ChatOpenAI(model="gpt-4.1-nano")

# Tools
search = TavilySearchResults(max_results=2)
arxiv = ArxivQueryRun()
wolfram = WolframAlphaQueryRun(api_wrapper=WolframAlphaAPIWrapper())

@tool
def get_food() -> str:
    """Get a plate of spaghetti."""
    return "Here is your plate of spaghetti 🍝"

python_repl = PythonREPL()
repl_tool = Tool(
    name="python_repl",
    description="A Python shell. Use this to execute python commands. Input should be a valid python command. If you want to see the output of a value, you should print it out with `print(...)`.",
    func=python_repl.run,
)

tools = [search, arxiv, wolfram, get_food, repl_tool]

# functions = [convert_to_openai_function(t) for t in tools]

# test the tool
# print("Testing Tavily tool ...")
# result = search.invoke("What's a 'node' in LangGraph?")
# print(result)

# print("Testing Arxiv tool ...")
# result = arxiv.run("Quantum Computing")
# print(result)

# print("Testing Wolfram tool ...")
# result = wolfram.run("What is 2x+5 = -3x + 7?")
# print(result)


# add tools to the model
llm = llm.bind_tools(tools)

# ---------------------------
# Define the graph
# ---------------------------

# State
class State(TypedDict):
    # Messages have the type "list". The `add_messages` function
    # in the annotation defines how this state key should be updated
    # (in this case, it appends messages to the list, rather than overwriting them)
    messages: Annotated[list, add_messages]

graph_builder = StateGraph(State)

# Node 1 ----------
def chatbot(state: State):
    return {"messages": [llm.invoke(state["messages"])]}

# Node 2 ----------
tool_node = ToolNode(tools)

# Edge 1 -------------------

def route_tools(
    state: State,
) -> Literal["tools", "__end__"]:
    """
    Use in the conditional_edge to route to the ToolNode if the last message
    has tool calls. Otherwise, route to the end.
    """
    if isinstance(state, list):
        ai_message = state[-1]
    elif messages := state.get("messages", []):
        ai_message = messages[-1]
    else:
        raise ValueError(f"No messages found in input state to tool_edge: {state}")
    
    
    if hasattr(ai_message, "tool_calls") and len(ai_message.tool_calls) > 0:
        print("Routing to tools")
        print("Tool calls found:", ai_message.tool_calls)
        return "tools"
    return "__end__"




# The first argument is the unique node name
# The second argument is the function or object that will be called whenever
# the node is used.
graph_builder.add_node("chatbot", chatbot)
graph_builder.add_node("tools", tool_node)


# The `tools_condition` function returns "tools" if the chatbot asks to use a tool, and "__end__" if
# it is fine directly responding. This conditional routing defines the main agent loop.
graph_builder.add_conditional_edges(
    "chatbot",
    route_tools,
    # The following dictionary lets you tell the graph to interpret the condition's outputs as a specific node
    # It defaults to the identity function, but if you
    # want to use a node named something else apart from "tools",
    # You can update the value of the dictionary to something else
    # e.g., "tools": "my_tools"
    {"tools": "tools", "__end__": "__end__"},
)
# Any time a tool is called, we return to the chatbot to decide the next step
graph_builder.add_edge("tools", "chatbot")


# Entry and finish points
graph_builder.set_entry_point("chatbot")


# Graph object
graph = graph_builder.compile()

# Visualize the graph
visualize(graph, "graph.png")

# ---------------------------
# Run the graph 
# MESSAGES are stored ONLY within the graph state !!!!
# EACH USER INPUT IS A NEW STATE !!!!
# =>  NO HISTORY for chat interaction !!!!!!
# ---------------------------
while True:
    user_input = input("User: ")
    if user_input.lower() in ["quit", "exit", "q"]:
        print("Goodbye!")
        break
    for event in graph.stream({"messages": ("user", user_input)}):
        for value in event.values():
            last_msg = value["messages"][-1]
            # Skip printing tool error messages (they're handled internally)
            if hasattr(last_msg, 'type') and last_msg.type == 'tool':
                continue
            # Only print AI messages
            if hasattr(last_msg, 'content') and last_msg.content:
                print("Assistant:", last_msg.content)


