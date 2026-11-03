# from pathlib import Path

# from src.medicare_copilot.rag.pdf_extacter import (
#     extract_multimodal_documents,
# )
# from src.medicare_copilot.rag.visual_model import summarize_visual

# PDF_PATH = Path("RAG_DATA/KDIGO-2024-CKD-Guideline (1).pdf")
# IMAGE_DIR = Path("RAG_DATA/EXTRACTED")

# documents = extract_multimodal_documents(
#     pdf_path=PDF_PATH,
#     summarize_visual=summarize_visual,
#     render_pages=False,
# )

# for document in documents[:5]:
#     print(document.metadata)
#     print(document.page_content[:500])
#     print("-" * 80)
