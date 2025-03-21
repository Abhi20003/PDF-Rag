from pydantic import BaseModel

class QueryRequest(BaseModel):
    query: str

class SummaryRequest(BaseModel):
    pdf_name: str
    summary: str
