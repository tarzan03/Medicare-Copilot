from langchain_groq import ChatGroq
from src.medicare_copilot.utils.settings import settings
from groq import Groq
from pathlib import Path
import pymupdf
import base64
from src.medicare_copilot.rag.embeddings import embed_documents, embed_query
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, PointStruct, VectorParams

VISION_MODEL = "qwen/qwen3.8-27b"
groq_client = Groq(api_key=settings.GROQ_API_KEY)

PDF_PATH = Path("RAG_DATA/KDIGO-2024-CKD-Guideline (1).pdf")


def load_pdf_images(PDF_PATH):
    if not PDF_PATH:
        raise ValueError("File path required")
    pages = pymupdf.open(Path(PDF_PATH))
    metadata = pages.metadata
    urls, pngs = [], []

    for page_num in range(pages.page_count):
        png = pages[page_num].get_pixmap().tobytes("png")
        b64 = base64.b64encode(png).decode()
        url = f"data:image/png;base64,{b64}"

        urls.append(url)
        pngs.append(png)

    return urls, pngs, metadata


def generate_and_store_embeddings(PDF_PATH: Path, vectordb_url: str):
    client = QdrantClient(url=vectordb_url)
    DIM = 1024
    COLLECTION_NAME = "KDIGO-2024-pdf-pages"
    if not client.collection_exists(COLLECTION_NAME):
        client.create_collection(
            collection_name=COLLECTION_NAME,
            vectors_config=VectorParams(size=DIM, distance=Distance.COSINE),
        )
    page_urls, page_png, metadata = load_pdf_images(PDF_PATH)
    vectors = embed_documents(page_urls[:90])
    points = []
    for index, vector in enumerate(vectors):
        point = PointStruct(
            id=index, vector=vector, payload={"page_number": index, **metadata}
        )

        points.append(point)

    client.upsert(collection_name=COLLECTION_NAME, points=points)

    return "pdf stored Succesfully!"


# def summarize_visual(image_path, page_number):
#     image_data = image_to_data_uri(image_path)

#     prompt = f"""
# This visual was extracted from page {page_number} of the KDIGO-2024_CKD-Guideline.

# Describe the useful business information visible in the visual.

# If it is a chart or graph:
# - mention important values
# - mention highest/lowest values
# - mention the main trend

# If it is a diagram:
# - identify important components
# - explain the flow or relationships

# If it is a normal business image:
# - describe the useful factual information

# Keep the description concise and factual.
# """

#     response = groq_client.chat.completions.create(
#         model=VISION_MODEL,
#         messages=[
#             {
#                 "role": "user",
#                 "content": [
#                     {"type": "text", "text": prompt},
#                     {
#                         "type": "image_url",
#                         "image_url": {"url": image_data},
#                     },
#                 ],
#             }
#         ],
#         temperature=0,
#         max_completion_tokens=500,
#     )

#     return response.choices[0].message.content.strip()


# vectordb_url = "localhost:6333"
# client = QdrantClient(url=vectordb_url)

# page_urls, page_png, metadata = load_pdf_images(PDF_PATH)
# vectors = embed_documents(page_urls)

# points = []
# for index, vector in enumerate(vectors):
#     point = PointStruct(
#         id=index, vector=vector, payload={"page_number": index, **metadata}
#     )

#     points.append(point)

# client.upsert(collection_name=COLLECTION_NAME, points=points)

if __name__ == "__main__":
    print(
        generate_and_store_embeddings(PDF_PATH=PDF_PATH, vectordb_url="localhost:6333")
    )
