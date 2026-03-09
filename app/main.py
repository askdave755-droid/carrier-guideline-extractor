"""
FastAPI application
"""
import os
from fastapi import FastAPI, File, UploadFile, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional

from app.models import LineOfBusiness, CarrierTier
from app.extractor import extractor
from app.database import db from models import db

app = FastAPI(title="Carrier Guideline AI")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup():
    await db.connect()
    await db.ensure_table()
    print("✓ Carrier Guideline AI ready")

@app.on_event("shutdown")
async def shutdown():
    await db.close()

@app.get("/health")
async def health_check():
    return {"status": "healthy", "database": "connected" if db.pool else "disconnected"}

@app.post("/extract/pdf")
async def extract_pdf(
    file: UploadFile = File(...),
    carrier: str = Form(...),
    states: str = Form(""),
    line_of_business: str = Form("commercial_auto"),
    tier: Optional[str] = Form(None)
):
    if not file.filename.endswith('.pdf'):
        raise HTTPException(400, detail="Only PDF files accepted")
        
    state_list = [s.strip() for s in states.split(',') if s.strip()] if states else []
    contents = await file.read()
    
    try:
        results = extractor.extract(
            pdf_bytes=contents,
            carrier=carrier,
            states=state_list,
            lob=line_of_business,
            tier=tier
        )
        
        if not results:
            raise HTTPException(422, detail="Could not extract data from PDF")
            
        result = results[0]
        
        record_id = await db.insert_guideline(
            carrier_name=result.carrier_name,
            line_of_business=result.line_of_business,
            state=result.states[0] if result.states else 'XX',
            tier=result.tier,
            content=result.raw_text,
            metadata=result.dict()
        )
        
        return {
            "success": True,
            "carrier": carrier,
            "state": result.states[0] if result.states else 'XX',
            "extracted_data": result.dict(),
            "saved_to_db": True,
            "record_id": record_id,
            "confidence": result.confidence_score
        }
        
    except Exception as e:
        raise HTTPException(500, detail=f"Extraction failed: {str(e)}")

class MatchRequest(BaseModel):
    carrier: str
    state: str
    fleet_size: int
    has_dui: bool = False
    dui_years_ago: Optional[int] = None
    hazmat: bool = False
    vehicle_age: Optional[int] = None

@app.post("/api/match-carrier")
async def match_carrier(req: MatchRequest):
    rules = await db.get_carrier_rules(req.carrier, req.state)
    
    if not rules:
        return {
            "carrier": req.carrier,
            "eligible": False,
            "reason": "No guidelines found",
            "action": "SKIP"
        }
    
    fleet_min = rules.get('fleet_size', {}).get('min', 1)
    fleet_max = rules.get('fleet_size', {}).get('max', 9999)
    dui_allowed = rules.get('dui_policy', {}).get('allowed', True)
    dui_lookback = rules.get('dui_policy', {}).get('lookback_years')
    hazmat_allowed = rules.get('hazmat_policy', {}).get('allowed', True)
    
    reasons = []
    eligible = True
    
    if req.fleet_size < fleet_min or req.fleet_size > fleet_max:
        eligible = False
        reasons.append(f"Fleet size {req.fleet_size} outside range {fleet_min}-{fleet_max}")
        
    if req.has_dui:
        if not dui_allowed:
            eligible = False
            reasons.append("DUIs not allowed")
        elif dui_lookback and req.dui_years_ago and req.dui_years_ago < dui_lookback:
            eligible = False
            reasons.append(f"DUI too recent ({req.dui_years_ago} years < {dui_lookback} required)")
            
    if req.hazmat and not hazmat_allowed:
        eligible = False
        reasons.append("Hazmat not allowed")
    
    return {
        "carrier": req.carrier,
        "state": req.state,
        "eligible": eligible,
        "reasons": reasons if not eligible else ["Meets all criteria"],
        "action": "QUOTE" if eligible else "DECLINE",
        "confidence": rules.get('confidence_score', 0.8)
    }

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))

    uvicorn.run(app, host="0.0.0.0", port=port)

