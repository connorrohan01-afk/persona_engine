from fastapi import APIRouter, Request
import httpx

router = APIRouter()

@router.post("/create")
async def create_workflow(request: Request):
    payload = await request.json()
    return {"ok": True, "message": "n8n router working", "data": payload}