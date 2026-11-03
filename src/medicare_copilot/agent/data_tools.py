from datetime import date, datetime, time
from typing import Any

from langchain_core.tools import tool
from sqlalchemy import Date, DateTime, and_, func
from sqlalchemy.orm import Session

from medicare_copilot.agent.dtos import (
    PatientCondition,
    PatientSearchInput,
)
from medicare_copilot.backend.models import Patient
from medicare_copilot.utils.db import LocalSession


# One source of truth for supported patient fields.
FIELD_REGISTRY = {
    "patient_id": {
        "column": Patient.patient_id,
        "type": "text",
        "aliases": ["id", "patient identifier"],
    },
    "patient_name": {
        "column": Patient.patient_name,
        "type": "text",
        "aliases": ["name", "full name"],
    },
    "age": {
        "column": Patient.age,
        "type": "number",
        "aliases": ["patient age"],
    },
    "diagnosis": {
        "column": Patient.diagnosis,
        "type": "text",
        "aliases": ["disease", "condition"],
    },
    "medication": {
        "column": Patient.current_medication,
        "type": "text",
        "aliases": ["current medication", "medicine", "drug"],
    },
    "missed_appointment": {
        "column": Patient.missed_last_appointment,
        "type": "boolean",
        "aliases": [
            "missed last appointment",
            "appointment missed",
        ],
    },
    "spo2": {
        "column": Patient.vitals_spo2,
        "type": "number",
        "aliases": ["oxygen saturation", "blood oxygen"],
    },
}

ALIAS_TO_FIELD = {
    alias: field
    for field, config in FIELD_REGISTRY.items()
    for alias in config["aliases"]
}


def normalize_field_name(name: str) -> str:
    """Normalize a supported field name or alias to its canonical name."""
    normalized = " ".join(name.lower().strip().split())

    if normalized in FIELD_REGISTRY:
        return normalized

    if normalized in ALIAS_TO_FIELD:
        return ALIAS_TO_FIELD[normalized]

    raise ValueError(f"Unsupported patient field: {name}")


def convert_obj_to_dict(patients: list[Patient]) -> list[dict[str, Any]]:
    """Convert SQLAlchemy Patient objects into serializable dictionaries."""
    result = []

    for patient in patients:
        record = {}

        for column in Patient.__table__.columns:
            value = getattr(patient, column.name)

            if isinstance(value, (date, datetime)):
                value = value.isoformat()

            record[column.name] = value

        result.append(record)

    return result


def _parse_boolean(value: Any) -> bool:
    """Accept actual booleans or the strings 'true' and 'false'."""
    if isinstance(value, bool):
        return value

    if isinstance(value, str):
        normalized = value.strip().lower()

        if normalized == "true":
            return True

        if normalized == "false":
            return False

    raise ValueError("Boolean fields require true or false.")


def _parse_date(value: Any, field: str) -> date:
    """Parse a YYYY-MM-DD date string."""
    if isinstance(value, datetime):
        return value.date()

    if isinstance(value, date):
        return value

    if not isinstance(value, str):
        raise ValueError(f"{field} requires a YYYY-MM-DD date.")

    try:
        return date.fromisoformat(value.strip())
    except ValueError as exc:
        raise ValueError(f"Invalid date for {field}: {value}. Use YYYY-MM-DD.") from exc


def _build_single_filter(condition: PatientCondition):
    """Validate one structured condition and build its SQLAlchemy filter."""
    field = condition.field
    operator = condition.operator
    value = condition.value

    # Do not silently accept aliases or unknown field names from the LLM.
    if field not in FIELD_REGISTRY:
        raise ValueError(f"Unsupported patient field: {field}")

    spec = FIELD_REGISTRY[field]
    column = spec["column"]
    field_type = spec["type"]

    if value is None:
        raise ValueError(f"Value cannot be null for field '{field}'.")

    if field_type == "text":
        if operator not in {"=", "contains"}:
            raise ValueError(
                f"Operator '{operator}' is not supported for text field '{field}'."
            )

        if not isinstance(value, str):
            raise ValueError(f"Field '{field}' requires a string value.")

        value = value.strip()

        if not value:
            raise ValueError(f"Value cannot be empty for field '{field}'.")

        if operator == "contains":
            return column.ilike(f"%{value}%")

        if field == "patient_id":
            return column == value

        return column.ilike(value)

    if field_type == "boolean":
        if operator != "=":
            raise ValueError(f"Only '=' is supported for Boolean field '{field}'.")

        boolean_value = _parse_boolean(value)
        return column.is_(boolean_value)

    if field_type == "number":
        if operator not in {"=", ">", "<", ">=", "<="}:
            raise ValueError(
                f"Operator '{operator}' is not supported for numeric field '{field}'."
            )

        # bool is a subclass of int in Python, so reject it explicitly.
        if isinstance(value, bool):
            raise ValueError(f"Field '{field}' requires a numeric value.")

        try:
            numeric_value = float(value)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"Field '{field}' requires a numeric value.") from exc

        if operator == "=":
            return column == numeric_value
        if operator == ">":
            return column > numeric_value
        if operator == "<":
            return column < numeric_value
        if operator == ">=":
            return column >= numeric_value
        if operator == "<=":
            return column <= numeric_value

    if field_type == "date":
        if operator not in {"=", ">", "<", ">=", "<="}:
            raise ValueError(
                f"Operator '{operator}' is not supported for date field '{field}'."
            )

        parsed_date = _parse_date(value, field)

        if isinstance(column.type, DateTime):
            date_value = datetime.combine(parsed_date, time.min)
        elif isinstance(column.type, Date):
            date_value = parsed_date
        else:
            raise ValueError(f"Unsupported SQLAlchemy date type for '{field}'.")

        if operator == "=":
            return column == date_value
        if operator == ">":
            return column > date_value
        if operator == "<":
            return column < date_value
        if operator == ">=":
            return column >= date_value
        if operator == "<=":
            return column <= date_value

    raise ValueError(f"Unsupported field type: {field_type}")


def build_patient_filters(
    conditions: list[PatientCondition],
):
    """Build validated SQLAlchemy expressions shared by search and count tools."""
    if not conditions:
        raise ValueError("Provide at least one filter condition.")

    return [_build_single_filter(condition) for condition in conditions]


@tool(args_schema=PatientSearchInput)
def get_data_by_multiple_conditions(
    conditions: list[PatientCondition],
) -> list[dict[str, Any]]:
    """Search patients using structured field conditions.

    All conditions are combined using AND. Use only canonical field names
    and supported operators. Text fields support case-insensitive matching;
    use 'contains' for substring matching. Numeric fields support
    =, >, <, >=, and <=. Boolean fields support '=' with true or false.
    Return matching patient records, limited to 100.
    """
    filters = build_patient_filters(conditions)

    with LocalSession() as db:
        patients = db.query(Patient).filter(and_(*filters)).limit(100).all()

        return convert_obj_to_dict(patients)


@tool(args_schema=PatientSearchInput)
def get_counts_by_multiple_conditions(
    conditions: list[PatientCondition],
) -> dict[str, Any]:
    """Count patients matching structured field conditions.

    All conditions are combined using AND. Use the same canonical fields
    and operators supported by the patient search tool. Returns the count
    and the conditions applied; it does not return patient records.
    """
    filters = build_patient_filters(conditions)

    with LocalSession() as db:
        count = db.query(func.count(Patient.patient_id)).filter(and_(*filters)).scalar()

        return {
            "total_count": count or 0,
            "filters_applied": [condition.model_dump() for condition in conditions],
        }


tools = [
    get_data_by_multiple_conditions,
    get_counts_by_multiple_conditions,
]


if __name__ == "__main__":
    example_conditions = [
        PatientCondition(
            field="diagnosis",
            operator="contains",
            value="kidney",
        ),
        PatientCondition(
            field="missed_appointment",
            operator="=",
            value=True,
        ),
    ]

    print(
        get_data_by_multiple_conditions.invoke(
            {"conditions": [condition.model_dump() for condition in example_conditions]}
        )
    )
