from fastapi import File, UploadFile, HTTPException, status
from sqlalchemy.orm import Session
from datetime import date, datetime
from src.medicare_copilot.backend.models import Patient
from sqlalchemy.exc import IntegrityError

import csv
import io
from datetime import date


MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB

REQUIRED_COLUMNS = {"patient_id", "patient_name"}

OPTIONAL_COLUMNS = {
    "age",
    "gender",
    "email",
    "phone_number",
    "diagnosis",
    "current_medication",
    "lab_test",
    "lab_value",
    "lab_unit",
    "last_visit_date",
    "next_scheduled_visit",
    "days_since_last_visit",
    "missed_last_appointment",
    "vitals_bp_systolic",
    "vitals_bp_diastolic",
    "vitals_heart_rate",
    "vitals_spo2",
    "notes",
}

DATE_COLUMNS = {
    "last_visit_date",
    "next_scheduled_visit",
}

INTEGER_COLUMNS = {
    "age",
    "days_since_last_visit",
    "vitals_bp_systolic",
    "vitals_bp_diastolic",
    "vitals_heart_rate",
}

FLOAT_COLUMNS = {
    "lab_value",
    "vitals_spo2",
}

BOOLEAN_COLUMNS = {"missed_last_appointment"}

ALLOWED_COLUMNS = REQUIRED_COLUMNS | OPTIONAL_COLUMNS


def parse_value(column: str, value: str):
    """Convert a CSV value into the corresponding Python type."""
    value = value.strip()

    if value == "":
        return None

    if column in DATE_COLUMNS:
        return date.fromisoformat(value)

    if column in INTEGER_COLUMNS:
        return int(value)

    if column in FLOAT_COLUMNS:
        return float(value)

    if column in BOOLEAN_COLUMNS:
        normalized = value.lower()

        if normalized in {"true", "1", "yes"}:
            return True

        if normalized in {"false", "0", "no"}:
            return False

        raise ValueError("Expected true/false, yes/no, or 1/0")

    return value


async def ingest_patients_csv(
    file: UploadFile,
    db: Session,
):
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(
            status_code=400,
            detail="Please upload a .csv file.",
        )

    # Read at most 10 MB plus one byte to detect oversized uploads.
    content = await file.read(MAX_FILE_SIZE + 1)

    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=413,
            detail="CSV file exceeds the 10 MB limit.",
        )

    if not content:
        raise HTTPException(
            status_code=400,
            detail="The uploaded CSV file is empty.",
        )

    try:
        text = content.decode("utf-8-sig")
        reader = csv.DictReader(io.StringIO(text))

        if not reader.fieldnames:
            raise HTTPException(
                status_code=422,
                detail="CSV header row is missing.",
            )

        headers = [h.strip() for h in reader.fieldnames]

        if len(headers) != len(set(headers)):
            raise HTTPException(
                status_code=422,
                detail="CSV contains duplicate column names.",
            )

        missing = REQUIRED_COLUMNS - set(headers)
        unknown = set(headers) - ALLOWED_COLUMNS

        if missing:
            raise HTTPException(
                status_code=422,
                detail=f"Missing required columns: {sorted(missing)}",
            )

        if unknown:
            raise HTTPException(
                status_code=422,
                detail=f"Unknown columns: {sorted(unknown)}",
            )

        # Normalize header whitespace.
        reader.fieldnames = headers

        patients = []
        seen_ids = set()
        errors = []

        for line_number, row in enumerate(reader, start=2):
            if None in row:
                errors.append(f"Row {line_number}: too many CSV values.")
                continue

            if all(value is None or not value.strip() for value in row.values()):
                continue  # Ignore blank lines.

            try:
                data = {}

                for column, raw_value in row.items():
                    if raw_value is None:
                        raise ValueError(f"Missing value for column '{column}'")

                    data[column] = parse_value(column, raw_value)

                for column in REQUIRED_COLUMNS:
                    if not data.get(column):
                        raise ValueError(f"'{column}' cannot be empty")

                patient_id = data["patient_id"]

                if patient_id in seen_ids:
                    raise ValueError(f"Duplicate patient_id '{patient_id}' in CSV")

                seen_ids.add(patient_id)
                patients.append(Patient(**data))

            except (ValueError, TypeError, OverflowError) as exc:
                errors.append(f"Row {line_number}: {exc}")

        if errors:
            raise HTTPException(
                status_code=422,
                detail={
                    "message": "CSV validation failed; nothing was inserted.",
                    "errors": errors[:50],
                    "total_errors": len(errors),
                },
            )

        if not patients:
            raise HTTPException(
                status_code=422,
                detail="No patient records found in the CSV.",
            )

        # One transaction: either all records are inserted or none are.
        try:
            db.add_all(patients)
            db.commit()

        except IntegrityError as exc:
            db.rollback()
            raise HTTPException(
                status_code=409,
                detail=(
                    "Database constraint violation. Check for existing "
                    "patient IDs or duplicate email addresses."
                ),
            ) from exc

        except Exception:
            db.rollback()
            raise

        return {
            "message": "CSV ingestion completed successfully.",
            "filename": file.filename,
            "inserted_count": len(patients),
        }

    except UnicodeDecodeError as exc:
        raise HTTPException(
            status_code=422,
            detail="CSV must use UTF-8 encoding.",
        ) from exc

    except csv.Error as exc:
        raise HTTPException(
            status_code=422,
            detail="Malformed CSV file.",
        ) from exc
