from typing import Annotated
import os
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
from langgraph.prebuilt import ToolNode
from typing import Literal
from visualizer import visualize
load_dotenv()


# Wolfram Alpha API is returning correct content type "text/xml; charset=utf-8"
# but there's a space inside. Fixed by removing spaces before assertion.
class FixedWolframAlphaAPIWrapper(WolframAlphaAPIWrapper):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        async def patched_aquery(input, params=(), **kwargs):
            import httpx
            import multidict
            import xmltodict
            from wolframalpha import Document

            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    self.wolfram_client.url,
                    params=multidict.MultiDict(
                        params, appid=self.wolfram_client.app_id, input=input, **kwargs
                    ),
                )
            # Fixed: normalize content-type by removing spaces
            content_type = resp.headers.get('Content-Type', '').replace(' ', '')
            assert content_type == 'text/xml;charset=utf-8', f"Expected 'text/xml;charset=utf-8', got '{content_type}'"
            doc = xmltodict.parse(resp.content, postprocessor=Document.make)
            return doc['queryresult']

        self.wolfram_client.aquery = patched_aquery


def prepare_tools():
    """Prepare and configure all tools for the agent."""
    # Web search and research tools
    search = TavilySearchResults(max_results=2)
    arxiv = ArxivQueryRun()

    # Wolfram Alpha (optional, requires API key)
    wolfram_tool = None
    wolfram_app_id = os.getenv("WOLFRAM_ALPHA_APPID")
    if wolfram_app_id:
        wolfram_tool = WolframAlphaQueryRun(
            api_wrapper=FixedWolframAlphaAPIWrapper(wolfram_alpha_appid=wolfram_app_id)
        )
    else:
        print(
            "Warning: WOLFRAM_ALPHA_APPID is not set. "
            "Wolfram Alpha tool will be disabled."
        )

    # Custom tool
    @tool
    def get_food() -> str:
        """Get a plate of spaghetti."""
        return "Here is your plate of spaghetti 🍝"

    # Python REPL tool
    python_repl = PythonREPL()
    repl_tool = Tool(
        name="python_repl",
        description="A Python shell. Use this to execute python commands. Input should be a valid python command. If you want to see the output of a value, you should print it out with `print(...)`.",
        func=python_repl.run,
    )

    # Combine all tools
    tools = [search, arxiv, get_food, repl_tool]
    if wolfram_tool:
        tools.append(wolfram_tool)

    print(f"Prepared {len(tools)} tools: {[tool.name for tool in tools]}")
    return tools

# Model
llm = ChatOpenAI(model="gpt-4.1-nano")

# Tools
tools = prepare_tools()
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

graph_builder.add_node("chatbot", chatbot)
graph_builder.add_node("tools", tool_node)

# Define edges: start -> chatbot, and tools -> chatbot (creating the agent loop)
graph_builder.add_edge("__start__", "chatbot")
graph_builder.add_conditional_edges("chatbot", route_tools)
graph_builder.add_edge("tools", "chatbot")

# Graph object
graph = graph_builder.compile()

# Visualize the graph
visualize(graph, "graph.png")

# ---------------------------
# Run the graph
# Persistent conversation history across all user inputs
# ---------------------------
conversation_state = {"messages": []}

while True:
    user_input = input("User: ")
    if user_input.lower() in ["bye", "quit", "exit", "q"]:
        print("Goodbye!")
        break

    # Add user message to conversation state
    conversation_state["messages"].append(("user", user_input))

    # Stream graph execution with persistent state
    for event in graph.stream(conversation_state, {"recursion_limit": 50}):
        for value in event.values():
            last_msg = value["messages"][-1]
            # Print tool responses for debugging
            if hasattr(last_msg, 'type') and last_msg.type == 'tool':
                print(f"Tool response: {last_msg.content}")
                continue
            # Only print AI messages
            if hasattr(last_msg, 'content') and last_msg.content:
                print("Assistant:", last_msg.content)

    # Update conversation state with all messages from graph execution
    conversation_state = {"messages": list(event[list(event.keys())[-1]]["messages"])}

