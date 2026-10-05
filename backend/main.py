from fastapi import FastAPI, HTTPException, Request, UploadFile
import os
import logging
from contextlib import asynccontextmanager

from models import VerifyRequest, VerifyResponse, Verdict, ReferenceResult
from verify_one import verify_reference
from extract import extract_references, ReferenceExtractionError
from document_parser import extract_document_text, DocumentExtractionError

logger = logging.getLogger("citecheck")

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting CiteCheck...")
    logger.info("Configuration Diagnostic:")
    logger.info(f"  GEMINI_API_KEY Configured: {'YES' if os.environ.get('GEMINI_API_KEY') else 'NO'}")
    logger.info(f"  GEMINI_MODEL: {os.environ.get('GEMINI_MODEL', 'gemini-3.8-flash')}")
    logger.info(f"  CROSSREF_MAILTO Configured: {'YES' if os.environ.get('CROSSREF_MAILTO') else 'NO'}")
    logger.info(f"  OPENALEX_MAILTO Configured: {'YES' if os.environ.get('OPENALEX_MAILTO') else 'NO'}")
    logger.info(f"  SEMANTIC_SCHOLAR_API_KEY Configured: {'YES' if os.environ.get('SEMANTIC_SCHOLAR_API_KEY') else 'NO'}")
    logger.info(f"  CITECHECK_CACHE_DB: {os.environ.get('CITECHECK_CACHE_DB', 'citecheck_cache.db')}")
    yield
    logger.info("Shutting down CiteCheck...")

app = FastAPI(title="CiteCheck Backend", lifespan=lifespan)

@app.get("/")
def read_root():
    return {"message": "CiteCheck backend is running"}

@app.post("/verify", response_model=VerifyResponse)
async def verify_endpoint(request: Request):
    content_type = request.headers.get("content-type", "")
    references_to_verify = []
    
    if "application/json" in content_type:
        try:
            data = await request.json()
            verify_req = VerifyRequest(**data)
        except Exception as e:
            raise HTTPException(status_code=422, detail=f"Invalid JSON body: {e}")
            
        references_to_verify = verify_req.references
        if verify_req.text is not None:
            try:
                references_to_verify = extract_references(verify_req.text)
            except ReferenceExtractionError as e:
                raise HTTPException(status_code=500, detail=str(e))
                
    elif "multipart/form-data" in content_type:
        form = await request.form()
        file = form.get("file")
        if not file or not hasattr(file, "filename"):
            raise HTTPException(status_code=422, detail="Missing 'file' field in multipart form data")
            
        max_mb = int(os.environ.get("CITECHECK_MAX_UPLOAD_MB", 10))
        file_bytes = await file.read()
        await file.close()
        
        if len(file_bytes) > max_mb * 1024 * 1024:
            raise HTTPException(status_code=413, detail=f"File exceeds maximum upload size of {max_mb}MB")
            
        try:
            text = extract_document_text(file_bytes, file.filename, file.content_type)
        except DocumentExtractionError as e:
            raise HTTPException(status_code=400, detail=str(e))
            
        try:
            references_to_verify = extract_references(text)
        except ReferenceExtractionError as e:
            raise HTTPException(status_code=500, detail=str(e))
            
    else:
        raise HTTPException(status_code=415, detail="Unsupported Content-Type. Use application/json or multipart/form-data")
        
    results = []
    
    # Process sequentially for deterministic predictability and stability
    for ref in references_to_verify or []:
        result = await verify_reference(ref)
        results.append(result)
        
    verdict_counts = {v: 0 for v in Verdict}
    for res in results:
        verdict_counts[res.verdict] += 1
        
    total = len(results)
    
    # Reliability score: verified references / total checkable references.
    # We define checkable as references that are not CANNOT_VERIFY.
    checkable = total - verdict_counts.get(Verdict.CANNOT_VERIFY, 0)
    
    reliability_score = None
    if checkable > 0:
        verified_count = verdict_counts.get(Verdict.VERIFIED, 0)
        reliability_score = verified_count / checkable
        
    return VerifyResponse(
        results=results,
        total_references=total,
        verdict_counts=verdict_counts,
        reliability_score=reliability_score
    )
