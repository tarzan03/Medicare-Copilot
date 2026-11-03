from fastapi import FastAPI
from src.medicare_copilot.backend.routes.router import user_route
from medicare_copilot.backend.routes.rag import rag_router

app = FastAPI(title="Welcome to medicare Copilot")


@app.get("/")
def root():
    return "welcome!"


app.include_router(user_route)
app.include_router(rag_router)
