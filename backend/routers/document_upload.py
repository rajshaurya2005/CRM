from fastapi import APIRouter, File, UploadFile, HTTPException, status
from typing import List
import os

from services.document_processing_service import process_document_for_lead, DocumentProcessingError
from database.models import DocumentUploadResponse
from routers.leads import create_lead

router = APIRouter(prefix="/documents", tags=["documents"])

ALLOWED_CONTENT_TYPES = {
    "application/pdf": ".pdf",
    "text/plain": ".txt",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx"
}

MAX_FILE_SIZE = 10 * 1024 * 1024

@router.post("/upload", response_model=DocumentUploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_document(file: UploadFile = File(...)):
    if file.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid file type. Allowed types: {', '.join(ALLOWED_CONTENT_TYPES.keys())}"
        )
    
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Filename is required"
        )
    
    try:
        contents = await file.read()
        
        if len(contents) > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"File size exceeds maximum allowed size of {MAX_FILE_SIZE} bytes"
            )
        
        file_extension = os.path.splitext(file.filename)[1].lower()
        
        leads_data, text_length = await process_document_for_lead(contents, file_extension)
        
        created_leads = []
        for lead_data in leads_data:
            try:
                created_lead = create_lead(lead_data)
                created_leads.append(created_lead)
            except HTTPException as e:
                if e.status_code == status.HTTP_400_BAD_REQUEST and "email already exists" in e.detail:
                    print(f"Skipping lead due to duplicate email: {lead_data.email}")
                else:
                    raise

        if not created_leads:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="No new leads could be extracted or all extracted leads were duplicates."
            )

        return DocumentUploadResponse(
            message="Document processed successfully and leads uploaded.",
            leads=created_leads,
            extracted_text_length=text_length
        )
        
    except DocumentProcessingError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process document: {str(e)}"
        )

@router.get("/supported-formats")
async def get_supported_formats():
    return {
        "supported_formats": list(ALLOWED_CONTENT_TYPES.keys()),
        "max_file_size_mb": MAX_FILE_SIZE / (1024 * 1024)
    }