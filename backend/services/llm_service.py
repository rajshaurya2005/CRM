from langchain.chat_models import init_chat_model
from langchain_core.prompts import ChatPromptTemplate
from dotenv import load_dotenv

from database.models import LeadInDB

load_dotenv()

LLM_SUGGEST_FOLLOW_UP_PROMPT = """
You are a helpful CRM assistant. Given the following lead details, suggest a concise follow-up action.
Lead Name: {name}
Lead Email: {email}
Lead Status: {status}

Suggestion:
"""

LLM_LEAD_DETAILS_PROMPT = """
You are a helpful CRM assistant. Given the following lead details, provide a summary of their information.
Lead Name: {name}
Lead Email: {email}
Lead Phone: {phone}
Lead Status: {status}
Lead Source: {source}

Summary:
"""

LLM_DEFAULT_PROMPT = """
You are a helpful CRM assistant. The user is asking about a lead.
If the user asks to "Suggest follow-up", provide a concise follow-up action.
If the user asks for "Lead details", provide a summary of their information.
Otherwise, respond with "Ask about follow-up or details."

User query: {query}
Lead Name: {name}
Lead Email: {email}
Lead Phone: {phone}
Lead Status: {status}
Lead Source: {source}

Response:
"""

async def interact_with_llm(query: str, lead: LeadInDB) -> str:
    llm = init_chat_model(model_provider = "groq", model = "llama-3.3-70b-versatile", temperature = 0)

    if "suggest follow-up" in query.lower():
        prompt = ChatPromptTemplate.from_template(LLM_SUGGEST_FOLLOW_UP_PROMPT)
        chain = prompt | llm
        response = await chain.ainvoke({
            "name": lead.name,
            "email": lead.email,
            "status": lead.status
        })
        return response.content
    elif "lead details" in query.lower():
        prompt = ChatPromptTemplate.from_template(LLM_LEAD_DETAILS_PROMPT)
        chain = prompt | llm
        response = await chain.ainvoke({
            "name": lead.name,
            "email": lead.email,
            "phone": lead.phone,
            "status": lead.status,
            "source": lead.source
        })
        return response.content
    else:
        prompt = ChatPromptTemplate.from_template(LLM_DEFAULT_PROMPT)
        chain = prompt | llm
        response = await chain.ainvoke({
            "query": query,
            "name": lead.name,
            "email": lead.email,
            "phone": lead.phone,
            "status": lead.status,
            "source": lead.source
        })
        return response.content