from database.models import LeadInDB
from typing import Dict

async def send_email_action(lead: LeadInDB, subject: str, body: str) -> Dict[str, str]:
    print(f"Simulating Email Send to: {lead.email}")
    print(f"Subject: {subject}")
    print(f"Body: {body}")
    return {"status": "success", "message": f"Email simulated to {lead.email}"}

async def update_status_action(lead: LeadInDB, new_status: str) -> Dict[str, str]:
    print(f"Simulating Status Update for {lead.name}: {lead.status} -> {new_status}")
    return {"status": "success", "message": f"Status simulated for {lead.name} to {new_status}"}