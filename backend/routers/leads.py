from fastapi import APIRouter, HTTPException, status, Query
from typing import List, Optional
import sqlite3

from database.database import get_db_connection
from database.models import LeadCreate, LeadUpdate, LeadInDB

router = APIRouter(prefix="/leads", tags=["leads"])

@router.post("/", response_model=LeadInDB, status_code=status.HTTP_201_CREATED)
def create_lead(lead: LeadCreate):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        try:
            cursor.execute(
                "INSERT INTO leads (name, email, phone, status, source) VALUES (?, ?, ?, ?, ?)",
                (lead.name, lead.email, lead.phone, lead.status, lead.source)
            )
            conn.commit()
            lead_id = cursor.lastrowid
            return LeadInDB(id=lead_id, **lead.dict())
        except sqlite3.IntegrityError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, 
                detail="Lead with this email already exists"
            )

@router.get("/", response_model=List[LeadInDB])
def read_leads(
    status_filter: Optional[str] = Query(None, description="Filter by status"),
    source_filter: Optional[str] = Query(None, description="Filter by source"),
    all_leads: bool = Query(False, description="If true, return all leads ignoring limit and offset"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of results"),
    offset: int = Query(0, ge=0, description="Number of results to skip")
):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        query = "SELECT id, name, email, phone, status, source FROM leads"
        params = []
        conditions = []
        
        if status_filter:
            conditions.append("status = ?")
            params.append(status_filter)
        
        if source_filter:
            conditions.append("source = ?")
            params.append(source_filter)
        
        if conditions:
            query += " WHERE " + " AND ".join(conditions)
        
        if not all_leads:
            query += " ORDER BY id DESC LIMIT ? OFFSET ?"
            params.extend([limit, offset])
        else:
            query += " ORDER BY id DESC"
        
        cursor.execute(query, params)
        leads_data = cursor.fetchall()
        
        return [LeadInDB(**dict(lead)) for lead in leads_data]

@router.get("/{lead_id}", response_model=LeadInDB)
def read_lead(lead_id: int):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, name, email, phone, status, source FROM leads WHERE id = ?", 
            (lead_id,)
        )
        lead_data = cursor.fetchone()
        
        if not lead_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, 
                detail="Lead not found"
            )
        
        return LeadInDB(**dict(lead_data))

@router.put("/{lead_id}", response_model=LeadInDB)
def update_lead(lead_id: int, lead: LeadUpdate):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        cursor.execute("SELECT id FROM leads WHERE id = ?", (lead_id,))
        if not cursor.fetchone():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, 
                detail="Lead not found"
            )
        
        try:
            cursor.execute(
                """UPDATE leads 
                   SET name = ?, email = ?, phone = ?, status = ?, source = ?, 
                       updated_at = CURRENT_TIMESTAMP 
                   WHERE id = ?""",
                (lead.name, lead.email, lead.phone, lead.status, lead.source, lead_id)
            )
            conn.commit()
            return LeadInDB(id=lead_id, **lead.dict())
        except sqlite3.IntegrityError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, 
                detail="Lead with this email already exists"
            )

@router.delete("/{lead_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_lead(lead_id: int):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM leads WHERE id = ?", (lead_id,))
        conn.commit()
        
        if cursor.rowcount == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, 
                detail="Lead not found"
            )

@router.get("/{lead_id}/interact")
async def interact_with_lead(lead_id: int, query: str = Query(..., description="Query for LLM interaction")):
    lead = read_lead(lead_id)
    
    from services.llm_service import interact_with_llm
    response = await interact_with_llm(query, lead)
    
    return {"lead_id": lead_id, "query": query, "response": response}