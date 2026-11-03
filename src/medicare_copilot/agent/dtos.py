from pydantic import BaseModel, Field

from typing import Annotated, Any, Literal
from typing_extensions import TypedDict
from langchain_core.messages import AnyMessage
from langgraph.graph.message import add_messages


class PlanningState(TypedDict, total=False):
    messages: Annotated[list[AnyMessage], add_messages]
    goal: str
    tasks: list[str]
    current_task: int
    results: list[Any]
    final_answer: str


class Plan(BaseModel):
    tasks: list[str]


class PatientCondition(BaseModel):
    field: Literal[
        "patient_id",
        "patient_name",
        "age",
        "diagnosis",
        "medication",
        "missed_appointment",
        "spo2",
    ] = Field(description="Canonical patient field to filter")

    operator: Literal["=", ">", "<", ">=", "<=", "contains"] = Field(
        description="Comparison operator appropriate for the field type"
    )

    value: str | int | float | bool = Field(description="Value to compare against")


class PatientSearchInput(BaseModel):
    conditions: list[PatientCondition] = Field(
        min_length=1,
        description="All conditions are combined using AND",
    )
