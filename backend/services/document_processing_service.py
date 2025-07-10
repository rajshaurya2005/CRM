from typing import Dict, Any, List
import os
import tempfile
import asyncio
from pathlib import Path

from langchain_community.document_loaders import TextLoader, PyPDFLoader
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from pydantic import BaseModel, Field
from langchain.chat_models import init_chat_model
from dotenv import load_dotenv

from database.models import LeadCreate

load_dotenv()

class ExtractedLead(BaseModel):
    name: str = Field(description="Name of the lead")
    email: str = Field(description="Email of the lead")
    phone: str = Field(description="Phone number of the lead, or 'N/A' if not found")
    status: str = Field(description="Status of the lead, typically 'New'")
    source: str = Field(description="Source of the lead, typically 'Document'")

class ExtractedLeadsData(BaseModel):
    leads: List[ExtractedLead] = Field(description="A list of extracted lead data")

LEAD_EXTRACTION_PROMPT = """
You are an expert at extracting lead information from raw text.
Extract all lead information, including name, email, and phone number, from the following text.
If a phone number is not found for a lead, use 'N/A'.
The status for each lead should always be 'New' and the source should always be 'Document'.

Be careful to:
- Extract complete names (first and last name if available) for all distinct individuals.
- Find valid email addresses (check format) for all individuals.
- Find phone numbers in various formats for all individuals.
- Ensure all found leads are included in the output list.

Text:
{text}

Format Instructions:
{format_instructions}
"""

class DocumentProcessingError(Exception):
    pass

async def extract_text_from_file(file_content: bytes, file_extension: str) -> str:
    if file_extension == ".pdf":
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
            tmp_file.write(file_content)
            tmp_file_path = tmp_file.name
        
        try:
            loader = PyPDFLoader(tmp_file_path)
            documents = await asyncio.get_event_loop().run_in_executor(
                None, loader.load
            )
            text = "\n".join([doc.page_content for doc in documents])
            return text
        finally:
            Path(tmp_file_path).unlink(missing_ok=True)
            
    elif file_extension == ".txt":
        try:
            return file_content.decode('utf-8')
        except UnicodeDecodeError:
            return file_content.decode('latin-1')
    else:
        raise DocumentProcessingError(f"Unsupported file type: {file_extension}")

async def extract_lead_data_with_llm(raw_text: str) -> List[ExtractedLead]:
    if not raw_text.strip():
        raise DocumentProcessingError("No text content found in document")
    
    try:
        llm = init_chat_model(
            model_provider="groq", 
            model="llama-3.3-70b-versatile", 
            temperature=0
        )
        
        parser = JsonOutputParser(pydantic_object=ExtractedLeadsData)
        
        prompt = ChatPromptTemplate.from_template(LEAD_EXTRACTION_PROMPT)
        chain = prompt | llm | parser
        
        extracted_data_dict = await chain.ainvoke({
            "text": raw_text[:4000],
            "format_instructions": parser.get_format_instructions()
        })
        
        return [ExtractedLead(**lead_dict) for lead_dict in extracted_data_dict.get("leads", [])]
    
    except Exception as e:
        raise DocumentProcessingError(f"LLM processing failed: {str(e)}")

async def process_document_for_lead(file_content: bytes, file_extension: str) -> tuple[List[LeadCreate], int]:
    try:
        raw_text = await extract_text_from_file(file_content, file_extension)
        
        if not raw_text.strip():
            raise DocumentProcessingError("No readable text found in document")
        
        extracted_leads_data = await extract_lead_data_with_llm(raw_text)
        
        leads_to_create = []
        for extracted_lead in extracted_leads_data:
            lead_data = LeadCreate(
                name=extracted_lead.name,
                email=extracted_lead.email,
                phone=extracted_lead.phone,
                status=extracted_lead.status,
                source=extracted_lead.source
            )
            leads_to_create.append(lead_data)
        
        return leads_to_create, len(raw_text)
        
    except Exception as e:
        if isinstance(e, DocumentProcessingError):
            raise
        raise DocumentProcessingError(f"Document processing failed: {str(e)}")