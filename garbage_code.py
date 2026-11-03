# ------------This code is from agent/agents.py---------------------------------------------
# def get_patient_table_colunms():
#     columns = Patient.__table__.columns

#     return columns


# # Only allow fields that the LLM is permitted to filter.
# FILTERABLE_FIELDS = {
#     "patient_id": Patient.patient_id,
#     "patient_name": Patient.patient_name,
#     "patient_age": Patient.age,
#     "diagnosis": Patient.diagnosis,
#     "missed_last_appointment": Patient.missed_last_appointment,
#     "current_medication": Patient.current_medication,
#     "lab_test": Patient.lab_test,
#     "lab_unit": Patient.lab_unit,
#     "gender": Patient.gender,
#     "lab_value": Patient.lab_value,
#     "last_visit_date": Patient.last_visit_date,
#     "next_scheduled_visit": Patient.next_scheduled_visit,
#     "days_since_last_visit": Patient.days_since_last_visit,
#     "vitals_bp_diastolic": Patient.vitals_bp_diastolic,
#     "vitals_bp_systolic": Patient.vitals_bp_systolic,
#     "vitals_heart_rate": Patient.vitals_heart_rate,
#     "vitals_spo2": Patient.vitals_spo2,
#     "notes": Patient.notes,
# }


# @tool
# def get_data_by_multiple_conditions(conditions: dict[str, Any]):
#     """Search patients using diagnosis, current medication, and
#     missed_last_appointment filters. Combine supplied filters with AND.
#     Text filters use case-insensitive partial matching.
#     "Use only filters relevant to the user's request."""
#     if not conditions:
#         return []

#     filters = []

#     for field, value in conditions.items():
#         if field not in FILTERABLE_FIELDS:
#             raise ValueError(f"filtering by {field} is not permitted")

#         if value is None:
#             continue

#         column = FILTERABLE_FIELDS[field]
#         if field == "missed_last_appointment":
#             if isinstance(value, bool):
#                 filters.append(column.is_(value))
#             elif isinstance(value, str) or value.lower() in {"true", "false"}:
#                 filters.append(column.is_(value.lower() == "true"))

#             else:
#                 raise ValueError("missed_last_appointment must be true or false")

#         elif field == "last_visit_date" or field == "next_scheduled_visit":
#             if isinstance(value, datetime):
#                 filters.append(column == value)
#             elif isinstance(value, str):
#                 date_value = datetime.strptime(value, "%Y-%m-%d").date()
#                 filters.append(column == value)

#         elif isinstance(value, int):
#             filters.append(column == value)

#         elif ">" in value:
#             extracted_value = int(re.findall(r"-?\d+\.?\d*", value)[0])
#             filters.append(column > extracted_value)

#         elif "<" in value:
#             extracted_value = int(re.findall(r"-?\d+\.?\d*", value)[0])
#             filters.append(column < extracted_value)

#         elif ">=" in value:
#             extracted_value = int(re.findall(r"-?\d+\.?\d*", value)[0])
#             filters.append(column >= extracted_value)

#         elif "<=" in value:
#             extracted_value = int(re.findall(r"-?\d+\.?\d*", value)[0])
#             filters.append(column <= extracted_value)

#         else:
#             if not isinstance(value, str):
#                 raise ValueError(f"{column} must be a string value")

#             filters.append(column.ilike(f"%{value}%"))

#     if not filters:
#         return []

#     with LocalSession() as db:
#         patients = db.query(Patient).filter(and_(*filters)).all()

#         return [
#             {
#                 column.name: getattr(patient, column.name)
#                 for column in Patient.__table__.columns
#             }
#             for patient in patients
#         ]


# -------------------------This is from agent/data_tools.py---------------------------
# from src.medicare_copilot.backend.models import Patient
# from src.medicare_copilot.agent.dtos import PatientSearchInput
# from src.medicare_copilot.utils.db import LocalSession
# from sqlalchemy.orm import Session
# from sqlalchemy import func
# from sqlalchemy import or_, and_
# from typing import Any
# from datetime import datetime
# from langchain_core.tools import tool
# import re


# FIELD_REGISTRY = {
#     "patient_id": {
#         "column": Patient.patient_id,
#         "aliases": ["patient id", "id", "patient identifier"],
#         "type": "text",
#     },
#     "patient_name": {
#         "column": Patient.patient_name,
#         "aliases": ["name", "patient name", "full name"],
#         "type": "text",
#     },
#     "age": {
#         "column": Patient.age,
#         "aliases": ["patient age", "age"],
#         "type": "number",
#     },
#     "diagnosis": {
#         "column": Patient.diagnosis,
#         "aliases": ["disease", "condition", "medical diagnosis"],
#         "type": "text",
#     },
#     "medication": {
#         "column": Patient.current_medication,
#         "aliases": ["current medication", "medicine", "drug"],
#         "type": "text",
#     },
#     "missed_appointment": {
#         "column": Patient.missed_last_appointment,
#         "aliases": [
#             "missed appointment",
#             "missed last appointment",
#             "appointment missed",
#         ],
#         "type": "boolean",
#     },
#     "spo2": {
#         "column": Patient.vitals_spo2,
#         "aliases": ["oxygen saturation", "spo2", "blood oxygen"],
#         "type": "number",
#     },
# }


# ALIAS_TO_FIELD = {
#     alias: field
#     for field, config in FIELD_REGISTRY.items()
#     for alias in config["aliases"]
# }


# def normalize_field_name(name: str) -> str:
#     normalized = " ".join(name.lower().strip().split())

#     if normalized in FIELD_REGISTRY:
#         return normalized

#     if normalized in ALIAS_TO_FIELD:
#         return ALIAS_TO_FIELD[normalized]

#     raise ValueError(f"Unsupported patient field: {name}")


# def convert_obj_to_dict(data):

#     data = [
#         {
#             "patient_id": p.patient_id,
#             "patient_name": p.patient_name,
#             "age": p.age,
#             "gender": p.gender,
#             "diagnosis": p.diagnosis,
#             "current_medication": p.current_medication,
#             "lab_test": p.lab_test,
#             "lab_value": p.lab_value,
#             "lab_unit": p.lab_unit,
#             "last_visit_date": (
#                 p.last_visit_date.isoformat() if p.last_visit_date else None
#             ),
#             "next_scheduled_visit": (
#                 p.next_scheduled_visit.isoformat() if p.next_scheduled_visit else None
#             ),
#             "missed_last_appointment": p.missed_last_appointment,
#             "vitals_bp_systolic": p.vitals_bp_systolic,
#             "vitals_bp_diastolic": p.vitals_bp_diastolic,
#             "vitals_heart_rate": p.vitals_heart_rate,
#             "vitals_spo2": p.vitals_spo2,
#             "notes": p.notes,
#             "email": p.email,
#             "phone_number": p.phone_number,
#         }
#         for p in data
#     ]

#     return data


# # @tool
# # def fetch_all_patients():
# #     """this tools fetches all patient data"""
# #     with LocalSession() as db:
# #         patients = db.query(Patient).all()

# #         patient_data = convert_obj_to_dict(patients)

# #         return patient_data


# # @tool
# # def fetch_patient_by_missed_appointment():
# #     """this tool fetches patient who have missed their appointments"""
# #     with LocalSession() as db:
# #         missed_appointments = (
# #             db.query(Patient).filter(Patient.missed_last_appointment == True).all()
# #         )

# #         return convert_obj_to_dict(missed_appointments)


# # @tool
# # def get_patient_by_id(id: str):
# #     """this tool fetches patient data by patient_id."""
# #     with LocalSession() as db:
# #         patient = db.query(Patient).filter(Patient.patient_id == id).all()

# #         patient = convert_obj_to_dict(patient)

# #         return patient


# # @tool
# # def get_patient_by_name(name: str):
# #     """this tool fetches patient date by name"""
# #     with LocalSession() as db:
# #         patient = (
# #             db.query(Patient)
# #             .filter(func.lower(Patient.patient_name) == name.lower())
# #             .all()
# #         )

# #         patient = convert_obj_to_dict(patient)

# #         return patient


# # @tool
# # def get_patient_by_diagnosis(diagnosis: str):
# #     """this tool fethes data by diagnosis"""
# #     diagnosis = diagnosis.strip()
# #     pattern = f"%{diagnosis}%"
# #     with LocalSession() as db:
# #         patient = db.query(Patient).filter(Patient.diagnosis.ilike(pattern))
# #         patient = convert_obj_to_dict(patient)

# #         return patient


# # @tool
# # def get_patient_by_keyword(keyword: str):
# #     """this tool fetches data by given keyword."""
# #     keyword = keyword.strip()
# #     pattern = f"%{keyword}%"
# #     with LocalSession() as db:
# #         patient = (
# #             db.query(Patient)
# #             .filter(
# #                 or_(
# #                     Patient.diagnosis.ilike(pattern),
# #                     Patient.notes.ilike(pattern),
# #                     Patient.current_medication.ilike(pattern),
# #                     Patient.lab_test.ilike(pattern),
# #                 )
# #             )
# #             .all()
# #         )

# #         patient = convert_obj_to_dict(patient)

# #         return patient


# FILTERABLE_FIELDS = {
#     "patient_id": Patient.patient_id,
#     "patient_name": Patient.patient_name,
#     "patient_age": Patient.age,
#     "diagnosis": Patient.diagnosis,
#     "missed_last_appointment": Patient.missed_last_appointment,
#     "current_medication": Patient.current_medication,
#     "lab_test": Patient.lab_test,
#     "lab_unit": Patient.lab_unit,
#     "gender": Patient.gender,
#     "lab_value": Patient.lab_value,
#     "last_visit_date": Patient.last_visit_date,
#     "next_scheduled_visit": Patient.next_scheduled_visit,
#     "days_since_last_visit": Patient.days_since_last_visit,
#     "vitals_bp_diastolic": Patient.vitals_bp_diastolic,
#     "vitals_bp_systolic": Patient.vitals_bp_systolic,
#     "vitals_heart_rate": Patient.vitals_heart_rate,
#     "vitals_spo2": Patient.vitals_spo2,
#     "notes": Patient.notes,
# }

# NUMERIC_FIELDS = {
#     "patient_age",
#     "lab_value",
#     "days_since_last_visit",
#     "vitals_bp_diastolic",
#     "vitals_bp_systolic",
#     "vitals_heart_rate",
#     "vitals_spo2",
# }

# BOOLEAN_FIELDS = {"missed_last_appointment"}

# DATE_FIELDS = {"last_visit_date", "next_scheduled_visit"}

# COMPARISON_PATTERN = re.compile(r"^\s*(>=|<=|>|<|==|=)\s*(-?\d+(?:\.\d+)?)\s*$")

# DATE_PATTERN = re.compile(r"^\s*(>=|<=|>|<|==|=)?\s*(\d{4}-\d{2}-\d{2})\s*$")


# def build_filter(field: str, value: Any):
#     column = FILTERABLE_FIELDS[field]

#     if field in BOOLEAN_FIELDS:
#         if isinstance(value, bool):
#             boolean_value = value
#         elif isinstance(value, str) and value.lower() in {"true", "false"}:
#             boolean_value = value.lower() == "true"
#         else:
#             raise ValueError(f"{field} must be true or false")

#         return column.is_(boolean_value)

#     if field in NUMERIC_FIELDS:
#         operator = "="
#         numeric_value = value

#         if isinstance(value, bool):
#             raise ValueError(f"{field} requires a numeric value")

#         if isinstance(value, str):
#             match = COMPARISON_PATTERN.fullmatch(value)

#             if match:
#                 operator, raw_value = match.groups()
#                 numeric_value = float(raw_value)
#             else:
#                 try:
#                     numeric_value = float(value.strip())
#                 except ValueError as exc:
#                     raise ValueError(
#                         f"Invalid numeric condition for {field}: {value}"
#                     ) from exc

#         if not isinstance(numeric_value, (int, float)):
#             raise ValueError(f"{field} requires a numeric value")

#         if operator in {"=", "=="}:
#             return column == numeric_value
#         if operator == ">":
#             return column > numeric_value
#         if operator == "<":
#             return column < numeric_value
#         if operator == ">=":
#             return column >= numeric_value
#         if operator == "<=":
#             return column <= numeric_value

#     if field in DATE_FIELDS:
#         if not isinstance(value, str):
#             raise ValueError(f"{field} must use an ISO date string (YYYY-MM-DD)")

#         match = DATE_PATTERN.fullmatch(value)
#         if not match:
#             raise ValueError(f"Invalid date condition for {field}: {value}")

#         operator, raw_date = match.groups()
#         operator = operator or "="
#         date_value = date.fromisoformat(raw_date)

#         # Adapt the value to the SQLAlchemy column's actual type.
#         if isinstance(column.type, DateTime):
#             date_value = datetime.combine(date_value, time.min)
#         elif not isinstance(column.type, Date):
#             raise ValueError(f"Unsupported date column type: {field}")

#         if operator in {"=", "=="}:
#             return column == date_value
#         if operator == ">":
#             return column > date_value
#         if operator == "<":
#             return column < date_value
#         if operator == ">=":
#             return column >= date_value
#         if operator == "<=":
#             return column <= date_value

#     if field in FILTERABLE_FIELDS:
#         if not isinstance(value, str):
#             raise ValueError(f"{field} requires a string value")

#         value = value.strip()
#         if not value:
#             raise ValueError(f"{field} cannot be empty")

#         # IDs are exact matches; other text fields use substring matching.
#         if field == "patient_id":
#             return column == value

#         return column.ilike(f"%{value}%")

#     raise ValueError(f"Unsupported field: {field}")


# @tool(args_schema=PatientSearchInput)
# def get_data_by_multiple_conditions(
#     conditions: dict[str, Any],
# ) -> list[dict[str, Any]]:
#     """Search patients using multiple field conditions. Combine all
#     conditions with AND. Text fields support case-insensitive partial
#     matching; patient IDs use exact matching. Numeric and date fields
#     support equality, >, <, >=, and <=. The missed appointment field
#     accepts true or false. Use only supported fields and do not invent
#     filters. Return matching patient records."""

#     if not conditions:
#         raise ValueError("Provide at least one filter condition.")

#     filters = []

#     for field, value in conditions.items():
#         if field not in FILTERABLE_FIELDS:
#             raise ValueError(f"Filtering by '{field}' is not permitted")

#         if value is None:
#             continue

#         filters.append(build_filter(field, value))

#     if not filters:
#         raise ValueError("Provide at least one non-null filter condition.")

#     with LocalSession() as db:
#         patients = db.query(Patient).filter(and_(*filters)).limit(100).all()

#         return [
#             {
#                 column.name: getattr(patient, column.name)
#                 for column in Patient.__table__.columns
#             }
#             for patient in patients
#         ]


# @tool(args_schema=PatientSearchInput)
# def get_counts_by_multiple_conditions(conditions: dict[str, Any]):
#     """get count of patients using multiple field conditions. Combine all
#     conditions with AND. Text fields support case-insensitive partial
#     matching; patient IDs use exact matching. Numeric and date fields
#     support equality, >, <, >=, and <=. The missed appointment field
#     accepts true or false. Use only supported fields and do not invent
#     filters. Return matching patient records."""

#     if not conditions:
#         raise ValueError("Provide at least one filter condition.")

#     filters = []

#     for field, value in conditions.items():
#         if field not in FILTERABLE_FIELDS:
#             raise ValueError(f"Filtering by '{field}' is not permitted")

#         if value is None:
#             continue

#         filters.append(build_filter(field, value))

#     if not filters:
#         raise ValueError("Provide at least one non-null filter condition.")

#     with LocalSession() as db:
#         patients = db.query(Patient).filter(and_(*filters))
#         count = patients.scalar()

#         return {
#             "total count": count,
#             "filters_applied": {
#                 field: value for field, value in conditions.items() if value is not None
#             },
#         }


# # tools = [
# #     fetch_all_patients,
# #     fetch_patient_by_missed_appointment,
# #     get_patient_by_id,
# #     get_patient_by_name,
# #     get_patient_by_diagnosis,
# #     get_patient_by_keyword,
# #     get_data_by_multiple_conditions,
# #     get_counts_by_multiple_conditions,
# # ]

# tools = [
#     get_data_by_multiple_conditions,
#     get_counts_by_multiple_conditions,
# ]


# if __name__ == "__main__":
#     # condition = {
#     #     "missed_last_appointment": True,
#     #     "diagnosis": "kidney disease",
#     #     "current_medication": "losartan",
#     # }
#     # print(get_data_by_multiple_conditions(condition))
#     print(get_patient_by_name("Akash Jain"))


# ------------------code from rag/pdf_extractor.py===========================================


# # ---------------------------------------------------------
# # Configuration
# # ---------------------------------------------------------

# IMAGE_DIR = Path("data/rag/images")

# MIN_IMAGE_WIDTH = 250
# MIN_IMAGE_HEIGHT = 180
# MIN_IMAGE_PIXELS = 80_000

# # Render vector-based page content at higher resolution.
# PAGE_RENDER_SCALE = 2.0


# # ---------------------------------------------------------
# # 1. IMAGE FILTERING
# # ---------------------------------------------------------


# def is_meaningful_image(
#     image_bytes: bytes,
# ) -> bool:
#     """
#     Reject tiny embedded images such as icons and fragments.

#     This checks pixel dimensions, not semantic importance.
#     """
#     try:
#         with Image.open(BytesIO(image_bytes)) as image:
#             width, height = image.size

#             return (
#                 width >= MIN_IMAGE_WIDTH
#                 and height >= MIN_IMAGE_HEIGHT
#                 and width * height >= MIN_IMAGE_PIXELS
#             )

#     except Exception:
#         return False


# # ---------------------------------------------------------
# # 2. TABLE EXTRACTION
# # ---------------------------------------------------------


# def extract_tables(
#     page: fitz.Page,
#     page_number: int,
#     source_name: str,
# ) -> list[Document]:
#     """
#     Extract detectable tables and convert them to Markdown.

#     Table extraction quality depends on the PDF layout.
#     """
#     documents = []

#     try:
#         tables = page.find_tables().tables

#         for table_number, table in enumerate(tables, start=1):
#             dataframe = table.to_pandas()

#             if dataframe.empty:
#                 continue

#             # Remove completely empty rows and columns.
#             dataframe = dataframe.dropna(how="all")
#             dataframe = dataframe.dropna(axis=1, how="all")

#             if dataframe.empty:
#                 continue

#             table_text = dataframe.to_markdown(index=False)

#             documents.append(
#                 Document(
#                     page_content=(
#                         f"Source: {source_name}\n"
#                         f"Page: {page_number}\n"
#                         f"Table: {table_number}\n\n"
#                         f"{table_text}"
#                     ),
#                     metadata={
#                         "source": source_name,
#                         "page": page_number,
#                         "modality": "table",
#                         "table_number": table_number,
#                     },
#                 )
#             )

#     except Exception as error:
#         print(f"Table extraction failed on page {page_number}: {error}")

#     return documents


# # ---------------------------------------------------------
# # 3. EMBEDDED IMAGE EXTRACTION
# # ---------------------------------------------------------


# def extract_embedded_images(
#     page: fitz.Page,
#     pdf: fitz.Document,
#     page_number: int,
#     source_name: str,
#     extracted_xrefs: set[int],
#     image_dir: Path,
#     summarize_visual: Any,
# ) -> list[Document]:
#     """
#     Extract meaningful embedded images and summarize them.

#     Deduplicates embedded image resources across the PDF.
#     """
#     documents = []

#     for image_number, image_info in enumerate(
#         page.get_images(full=True),
#         start=1,
#     ):
#         xref = image_info[0]

#         if xref in extracted_xrefs:
#             continue

#         try:
#             image_data = pdf.extract_image(xref)
#             image_bytes = image_data["image"]

#             if not is_meaningful_image(image_bytes):
#                 continue

#             image_extension = image_data["ext"]

#             image_path = (
#                 image_dir / f"page_{page_number}_image_{image_number}.{image_extension}"
#             )

#             image_path.write_bytes(image_bytes)

#             # Mark only successfully extracted useful images.
#             extracted_xrefs.add(xref)

#             summary = summarize_visual(
#                 image_path=image_path,
#                 page_number=page_number,
#             )

#             if not summary or not summary.strip():
#                 continue

#             documents.append(
#                 Document(
#                     page_content=(
#                         f"Source: {source_name}\n"
#                         f"Page: {page_number}\n"
#                         f"Visual description:\n{summary}"
#                     ),
#                     metadata={
#                         "source": source_name,
#                         "page": page_number,
#                         "modality": "visual",
#                         "image_path": str(image_path),
#                         "xref": xref,
#                     },
#                 )
#             )

#         except Exception as error:
#             print(
#                 f"Image extraction failed on page {page_number}, xref={xref}: {error}"
#             )

#     return documents


# # ---------------------------------------------------------
# # 4. PAGE RENDERING FALLBACK
# # ---------------------------------------------------------


# def render_page_for_vision(
#     page: fitz.Page,
#     page_number: int,
#     source_name: str,
#     image_dir: Path,
#     summarize_visual: Any,
# ) -> Document | None:
#     """
#     Render a full page for vision analysis.

#     Useful when charts or diagrams are drawn using vector graphics
#     instead of embedded image files.

#     Call this selectively: rendering every page increases processing
#     time and vision-model costs.
#     """
#     image_path = image_dir / f"page_{page_number}_render.png"

#     try:
#         pixmap = page.get_pixmap(
#             matrix=fitz.Matrix(
#                 PAGE_RENDER_SCALE,
#                 PAGE_RENDER_SCALE,
#             ),
#             alpha=False,
#         )

#         pixmap.save(str(image_path))

#         summary = summarize_visual(
#             image_path=image_path,
#             page_number=page_number,
#         )

#         if not summary or not summary.strip():
#             return None

#         return Document(
#             page_content=(
#                 f"Source: {source_name}\n"
#                 f"Page: {page_number}\n"
#                 f"Page visual description:\n{summary}"
#             ),
#             metadata={
#                 "source": source_name,
#                 "page": page_number,
#                 "modality": "page_visual",
#                 "image_path": str(image_path),
#             },
#         )

#     except Exception as error:
#         print(f"Page rendering failed on page {page_number}: {error}")
#         return None


# # ---------------------------------------------------------
# # 5. MAIN PDF EXTRACTION FUNCTION
# # ---------------------------------------------------------


# def extract_multimodal_documents(
#     pdf_path: str | Path,
#     summarize_visual: Any,
#     render_pages: bool = False,
# ) -> list[Document]:
#     """
#     Extract text, tables, embedded images, and optional page visuals.

#     Args:
#         pdf_path:
#             Path to the input PDF.
#         summarize_visual:
#             Function accepting image_path and page_number and
#             returning a text description of the visual.
#         render_pages:
#             If True, render and summarize every page as well.
#             Prefer selective rendering for large clinical PDFs.

#     Returns:
#         LangChain Documents containing extracted content and metadata.
#     """
#     pdf_path = Path(pdf_path)

#     if not pdf_path.is_file():
#         raise FileNotFoundError(f"PDF file not found: {pdf_path}")

#     if pdf_path.suffix.lower() != ".pdf":
#         raise ValueError("Input file must have a .pdf extension.")

#     IMAGE_DIR.mkdir(parents=True, exist_ok=True)

#     documents: list[Document] = []
#     extracted_xrefs: set[int] = set()

#     try:
#         with fitz.open(pdf_path) as pdf:
#             if pdf.is_encrypted:
#                 raise ValueError("Encrypted PDFs are not supported by this extractor.")

#             for page_index, page in enumerate(pdf):
#                 page_number = page_index + 1

#                 print(f"Processing page {page_number}/{len(pdf)}...")

#                 # 1. Extract page text.
#                 text = page.get_text("text").strip()

#                 if text:
#                     documents.append(
#                         Document(
#                             page_content=text,
#                             metadata={
#                                 "source": pdf_path.name,
#                                 "page": page_number,
#                                 "modality": "text",
#                             },
#                         )
#                     )

#                 # 2. Extract tables.
#                 documents.extend(
#                     extract_tables(
#                         page=page,
#                         page_number=page_number,
#                         source_name=pdf_path.name,
#                     )
#                 )

#                 # 3. Extract meaningful embedded images.
#                 documents.extend(
#                     extract_embedded_images(
#                         page=page,
#                         pdf=pdf,
#                         page_number=page_number,
#                         source_name=pdf_path.name,
#                         extracted_xrefs=extracted_xrefs,
#                         image_dir=IMAGE_DIR,
#                         summarize_visual=summarize_visual,
#                     )
#                 )

#                 # 4. Optional full-page vision processing.
#                 if render_pages:
#                     visual_document = render_page_for_vision(
#                         page=page,
#                         page_number=page_number,
#                         source_name=pdf_path.name,
#                         image_dir=IMAGE_DIR,
#                         summarize_visual=summarize_visual,
#                     )

#                     if visual_document is not None:
#                         documents.append(visual_document)

#     except Exception:
#         # Propagate unexpected document errors to the caller.
#         # Individual table/image failures are handled above.
#         raise

#     print(f"Extraction completed: {len(documents)} documents from {pdf_path.name}")

#     return documents


# # if __name__ == "__main__":
# #     documents = extract_multimodal_documents(PDF_PATH)
