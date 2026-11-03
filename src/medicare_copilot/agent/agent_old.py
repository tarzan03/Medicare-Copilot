from langchain_openai import ChatOpenAI
from openai import OpenAI
from medicare_copilot.utils.settings import settings
from src.medicare_copilot.agent.data_tools import tools
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, ToolMessage
from langgraph.graph import StateGraph, MessagesState, START, END
from langgraph.prebuilt import ToolNode, tools_condition
from src.medicare_copilot.agent.dtos import Plan, PlanningState


llm = ChatOpenAI(
    model="qwen/qwen3.8-27b",
    api_key=settings.GROQ_API_KEY,
    base_url="https://api.groq.com/openai/v1",
)

llm_with_tools = llm.bind_tools(tools=tools)
planner_llm = llm.with_structured_output(Plan)


def planner(state: PlanningState):
    system = SystemMessage(
        content="""you are a planner agent, " \
        "please break the task into smaller executable tasks"""
    )
    response = planner_llm.invoke([system] + state["messages"])

    return {"messages": [response]}


def executor(state: PlanningState):
    system = SystemMessage(
        content="""You are a executor agent, execute the task briefly"""
    )


Builder = StateGraph(MessagesState)

tool_node = ToolNode(tools)

Builder.add_node("agent", agent_node)
Builder.add_node("tools", tool_node)

Builder.add_edge(START, "agent")
Builder.add_conditional_edges("agent", tools_condition)
Builder.add_edge("tools", "agent")

Simple_agent = Builder.compile()


if __name__ == "__main__":
    resp = Simple_agent.invoke(
        {"messages": [HumanMessage("how many patients have missed appointemnts.")]}
    )
    print(resp["messages"])
