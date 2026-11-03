from fastapi import APIRouter, Depends, File, UploadFile, status
from src.medicare_copilot.utils.db import get_db
from sqlalchemy.orm import Session
from src.medicare_copilot.backend.routes import controller

user_route = APIRouter(prefix="/user")


@user_route.post("/bulk_upload_csv", status_code=status.HTTP_201_CREATED)
async def bulk_ingest(file: UploadFile = File(...), db: Session = Depends(get_db)):
    print(file.filename, file.content_type)
    return await controller.ingest_patients_csv(file, db)
