from fastapi import APIRouter, HTTPException, UploadFile, File
from typing import List
from schemas import QueryRequest, SummaryRequest
from services import query_rag_model, upload_file


# vector_store_dir = "./chroma_db"

router = APIRouter()
conversation_history=[]
summaries_db = {}

@router.post("/upload")
async def upload_pdfs(files: List[UploadFile] = File(...)):
    for file in files:
        if file.content_type != "application/pdf":
            raise HTTPException(status_code=400, detail=f"Invalid file type: {file.filename} is not a PDF.")

    try:
        response = upload_file(files)  
        store_request = SummaryRequest(pdf_name=file.filename, summary=response.get("summary"))
        await store_summary(store_request)
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/query")
async def query_rag(request: QueryRequest):
    try:
        return query_rag_model(request, conversation_history)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/store-summary")
async def store_summary(request: SummaryRequest):
    summaries_db[request.pdf_name] = request.summary
    
    return {"status": "success"}

@router.get("/get-summary/{pdf_name}")
async def get_summary(pdf_name: str):
    summary = summaries_db.get(pdf_name)
    if summary:
        return {"summary": summary}
    else:
        raise HTTPException(status_code=404, detail="Summary not found")


@router.get("/get-all-summaries")
async def get_all_summaries():
    if not summaries_db:
        raise HTTPException(status_code=404, detail="No summaries found")
    
    # Return all summaries as a list of objects
    return [{"pdf_name": pdf_name, "summary": summary} for pdf_name, summary in summaries_db.items()]
    