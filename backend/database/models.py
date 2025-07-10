from pydantic import BaseModel, validator
from typing import Optional, List
from datetime import datetime
import re

class LeadBase(BaseModel):
    name: str
    email: str
    phone: Optional[str] = None
    status: str = "New"
    source: str

    @validator('name')
    def validate_name(cls, v):
        if not v or not v.strip():
            raise ValueError('Name cannot be empty')
        if len(v.strip()) < 2:
            raise ValueError('Name must be at least 2 characters long')
        return v.strip()

    @validator('phone')
    def validate_phone(cls, v):
        if v and v != 'N/A':
            phone_pattern = re.compile(r'^\+?[\d\s\-\(\)]{7,}$')
            if not phone_pattern.match(v):
                raise ValueError('Invalid phone number format')
        return v

    @validator('status')
    def validate_status(cls, v):
        valid_statuses = ['New', 'Contacted', 'Qualified', 'Proposal', 'Negotiation', 'Closed Won', 'Closed Lost']
        if v not in valid_statuses:
            raise ValueError(f'Status must be one of: {", ".join(valid_statuses)}')
        return v

    @validator('source')
    def validate_source(cls, v):
        valid_sources = ['Manual', 'Document', 'Web Form', 'Email', 'Phone', 'Social Media', 'Referral']
        if v not in valid_sources:
            raise ValueError(f'Source must be one of: {", ".join(valid_sources)}')
        return v

class LeadCreate(LeadBase):
    pass

class LeadUpdate(LeadBase):
    pass

class LeadInDB(LeadBase):
    id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class LeadInteractionRequest(BaseModel):
    query: str
    
    @validator('query')
    def validate_query(cls, v):
        if not v or not v.strip():
            raise ValueError('Query cannot be empty')
        return v.strip()

class LeadInteractionResponse(BaseModel):
    lead_id: int
    query: str
    response: str
    timestamp: datetime = datetime.now()

class DocumentUploadResponse(BaseModel):
    message: str
    leads: List[LeadInDB]
    extracted_text_length: int