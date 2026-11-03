# from langchain_core.documents import Document
# from pathlib import Path
# from typing import Any
# from langchain_text_splitters import RecursiveCharacterTextSplitter
# import pymupdf
# from src.medicare_copilot.rag.visual_model import summarize_visual
# from src.medicare_copilot.utils.settings import settings
# import cohere
# from langchain_cohere import CohereEmbeddings
# from langchain_core.vectorstores import InMemoryVectorStore

# TEXT_DIR = Path("RAG_DATA/extracted_text.txt")
# PDF_PATH = Path("RAG_DATA/KDIGO-2024-CKD-Guideline (1).pdf")


# def get_text(pdf_path):
#     doc = pymupdf.open(pdf_path)  # open a document
#     metadata = doc.metadata
#     documents = []
#     for page_number in range(doc.page_count):  # iterate the document pages
#         page = doc[page_number].get_text()

#         page_metadata = {**metadata, "page_number": page_number}
#         documents.append(Document(page_content=page, metadata=page_metadata))

#     return documents


# def create_chunks(PATH:Path):
#     documents:Document = get_text(PATH)
#     splitter = RecursiveCharacterTextSplitter(
#         chunk_size=1000, chunk_overlap=200, separators=["\n\n", "\n", " ", ""]
#     )
#     chunks = splitter.split_documents(documents)

#     return chunks


# def create_embeddings(documents:Document):
#     embeddings = CohereEmbeddings(model="embd-v4.0",cohere_api_key = settings.COHERE_API_KEY)
#     vector_store = InMemoryVectorStore(documents, embedding=embeddings)


# if __name__ == "__main__":
#     resp = create_chunks(PDF_PATH)
#     for i, docs in resp[:2]:
#         print(
#             "index:", i, "metadata:", docs.metadata, "page_Content", docs.page_content
#         )
