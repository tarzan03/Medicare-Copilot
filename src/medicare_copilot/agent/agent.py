from typing import Literal

from langchain_openai import ChatOpenAI
from langchain_core.messages import (
    AIMessage,
    HumanMessage,
    SystemMessage,
)
from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode

from medicare_copilot.utils.settings import settings
from medicare_copilot.agent.data_tools import tools
from medicare_copilot.agent.dtos import Plan, PlanningState

from dotenv import load_dotenv

load_dotenv()
# --------------------------------------------------
# 1. Initialize the LLM
# --------------------------------------------------

llm = ChatOpenAI(
    model="openai/gpt-oss-120b",
    api_key=settings.GROQ_API_KEY,
    base_url="https://api.groq.com/openai/v1",
)

llm_with_tools = llm.bind_tools(tools)
planner_llm = llm.with_structured_output(Plan)


# --------------------------------------------------
# 2. Planner node
# --------------------------------------------------


def planner(state: PlanningState):
    messages = state["messages"]

    goal = state.get("goal")
    if not goal:
        goal = next(
            (
                message.content
                for message in reversed(messages)
                if isinstance(message, HumanMessage)
                and isinstance(message.content, str)
            ),
            "",
        )

    system = SystemMessage(
        content=(
            "You are a planning agent. Break the user's goal into "
            "3 tasks. Each task should be specific, "
            "ordered, and achievable using the available tools when needed. "
            "Avoid unnecessary tasks."
        )
    )

    plan = planner_llm.invoke([system, *messages])

    return {
        "goal": goal,
        "tasks": plan.tasks,
        "current_task": 0,
        "results": [],
    }


# --------------------------------------------------
# 3. Executor node
# --------------------------------------------------


def executor(state: PlanningState):
    index = state["current_task"]
    task = state["tasks"][index]

    system = SystemMessage(
        content=(
            "You are a patient-data execution agent. Use the available tools "
            "to answer the current task. Follow each tool's argument schema "
            "exactly; never invent field names or operators. Use canonical "
            "field names and supported comparison operators. For count-only "
            "questions, prefer the dedicated patient-count tool and do not "
            "retrieve all patient records. Do not invent database results.\n\n"
            f"Original goal: {state['goal']}\n"
            f"Current task ({index + 1}/{len(state['tasks'])}): {task}\n"
            f"Previous results: {state['results']}"
        )
    )

    # for index, message in enumerate(state["messages"]):
    #     print(f"\n--- Message {index}: {type(message).__name__} ---")
    #     print(message.model_dump())

    response = llm_with_tools.invoke([system, *state["messages"]])

    # A tool call is only a request until ToolNode executes it.
    # Keep the same task index while tools are being called.
    if response.tool_calls:
        return {"messages": [response]}

    # The current task is complete.
    return {
        "messages": [response],
        "results": state["results"] + [response.content],
        "current_task": index + 1,
    }


# --------------------------------------------------
# 4. Conditional routing
# --------------------------------------------------


def route_after_executor(
    state: PlanningState,
) -> Literal["tools", "executor", "synthesizer"]:

    last_message = state["messages"][-1]

    # Execute requested tools before advancing the task.
    if isinstance(last_message, AIMessage) and last_message.tool_calls:
        return "tools"

    # Continue with the next planned task.
    if state["current_task"] < len(state["tasks"]):
        return "executor"

    # All tasks have been completed.
    return "synthesizer"


# --------------------------------------------------
# 5. Synthesizer node
# --------------------------------------------------


def synthesizer(state: PlanningState):
    response = llm.invoke(
        [
            SystemMessage(
                content=(
                    "You are a synthesis agent. Answer the user's original "
                    "goal using the execution results. Be concise, accurate, "
                    "and explicit when information is unavailable. "
                    "Do not invent facts."
                )
            ),
            HumanMessage(
                content=(
                    f"Original goal: {state['goal']}\n\n"
                    f"Execution results:\n{state['results']}"
                )
            ),
        ]
    )

    return {"final_answer": response.content}


# --------------------------------------------------
# 6. Build the graph
# --------------------------------------------------

builder = StateGraph(PlanningState)

builder.add_node("planner", planner)
builder.add_node("executor", executor)
builder.add_node("tools", ToolNode(tools))
builder.add_node("synthesizer", synthesizer)

builder.add_edge(START, "planner")
builder.add_edge("planner", "executor")

builder.add_conditional_edges(
    "executor",
    route_after_executor,
    {
        "tools": "tools",
        "executor": "executor",
        "synthesizer": "synthesizer",
    },
)

# After a tool runs, resume the same task.
builder.add_edge("tools", "executor")
builder.add_edge("synthesizer", END)

planning_agent = builder.compile()


# --------------------------------------------------
# 7. Run the graph
# --------------------------------------------------

if __name__ == "__main__":
    question = (
        "show me patients with age more than 40 with diabetes who are on insuline?"
    )

    response = planning_agent.invoke(
        {
            "messages": [HumanMessage(content=question)],
            "goal": question,
            "tasks": [],
            "current_task": 0,
            "results": [],
            "final_answer": "",
        },
        config={
            "run_name": "Medicare-copilotV2",
            "tags": ["medicare-copilot", "planner-executor"],
            "metadata": {
                "application": "medicare-copilot",
                "workflow": "planning-agent",
            },
        },
    )

    print("Plan:", response["tasks"])
    print("Execution results:", response["results"])
    print("Final answer:", response["final_answer"])
