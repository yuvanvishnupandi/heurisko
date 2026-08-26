"""
API endpoints for the Fact Checking System.
"""

# --- Start: Add project root to sys.path for direct execution ---
import sys
import os
# Calculate the path to the project root directory (Heurisko-Web-Researcher-Agent)
# __file__ is research_system/api/main.py
# os.path.dirname(__file__) is research_system/api
# os.path.dirname(os.path.dirname(__file__)) is research_system
# os.path.dirname(os.path.dirname(os.path.dirname(__file__))) is the project root
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)
# --- End: Add project root to sys.path ---

from fastapi import FastAPI, HTTPException, BackgroundTasks, status, Depends, Header
from pydantic import BaseModel
import uvicorn
import logging
from typing import List, Dict, Any, Optional
import uuid
import asyncio
import json
from fastapi.middleware.cors import CORSMiddleware

# Import our custom research logic and database models
from research_system.agent import run_web_research
from research_system.schemas import ResearchRequest, ResearchReport, ErrorResponse
from research_system.database import engine, Base, get_db
from research_system.models import ChatHistory, User
from research_system.api import auth
from sqlalchemy.orm import Session

# Initialize database
Base.metadata.create_all(bind=engine)

# Setup basic logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Web Research Agent API", # Updated title
    description="API for performing automated web research using an AI agent.", # Updated description
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)

# In-memory storage for task results (Replace with Redis/Celery/DB for production)
task_results: Dict[str, Any] = {}


class ClaimRequest(BaseModel):
    claim: str
    language: str = "en"  # Default language

class ClaimResponse(BaseModel):
    claim: str
    result: str # e.g., "True", "False", "Uncertain"
    confidence_score: float
    explanation: str
    sources: List[Dict[str, Any]] = [] # Make sure this is List[Dict[str, Any]]

# New response model for initiating a task
class TaskResponse(BaseModel):
    task_id: str
    message: str
    history_id: Optional[int] = None

# New response model for task status/result
class ResultResponse(BaseModel):
    status: str # e.g., "processing", "completed", "error"
    result: Optional[ResearchReport] = None # Use ResearchReport
    error: Optional[ErrorResponse] = None # Include structured error


# --- Helper function to run the research in the background ---
def run_background_research(task_id: str, query: str, language: str, chat_history: List[Dict[str, str]], history_id: Optional[int], token: Optional[str] = None): 
    """Runs the web research agent and stores the result or error."""
    logger.info(f"Background research task started for task_id: {task_id}, query: '{query}' (lang: {language})")
    try:
        research_result = asyncio.run(run_web_research(query=query, chat_history=chat_history))

        if isinstance(research_result, ResearchReport):
            logger.info(f"Background research task completed for task_id: {task_id}. Storing report.")
            task_results[task_id] = ResultResponse(status="completed", result=research_result)
            
            # Save to db if token exists
            if token:
                from research_system.database import SessionLocal
                db = SessionLocal()
                try:
                    user = auth.get_current_user(token, db)
                    if user:
                        # Convert ResearchReport to dict to append to messages array
                        report_dict = json.loads(research_result.model_dump_json())
                        
                        if history_id:
                            # Append to existing history thread
                            history_item = db.query(ChatHistory).filter(ChatHistory.id == history_id, ChatHistory.user_id == user.id).first()
                            if history_item:
                                # We store an array of message dicts in report_json
                                try:
                                    messages = json.loads(history_item.report_json) if history_item.report_json else []
                                except json.JSONDecodeError:
                                    messages = [] # Fallback if it was old schema
                                
                                # Prevent duplicating the user message if it was already added synchronously
                                if not messages or messages[-1].get("role") != "user" or messages[-1].get("content") != query:
                                    messages.append({"role": "user", "content": query})
                                    
                                messages.append({"role": "assistant", "content": report_dict})
                                history_item.report_json = json.dumps(messages)
                                db.commit()
                        else:
                            # Create new history thread
                            messages = [
                                {"role": "user", "content": query},
                                {"role": "assistant", "content": report_dict}
                            ]
                            history_item = ChatHistory(
                                user_id=user.id,
                                query=query,
                                report_json=json.dumps(messages)
                            )
                            db.add(history_item)
                            db.commit()
                            # We can potentially return the new history_id in TaskResponse in the future
                except Exception as db_e:
                    logger.error(f"Failed to save history: {db_e}")
                finally:
                    db.close()
                    
        elif isinstance(research_result, ErrorResponse):
             logger.error(f"Background research task failed for task_id: {task_id}. Storing error: {research_result.error}")
             task_results[task_id] = ResultResponse(status="error", error=research_result)
             
             # Save error state to history if possible
             if token:
                 db = SessionLocal()
                 try:
                     user = auth.get_current_user(token, db)
                     if user and history_id:
                         history_item = db.query(ChatHistory).filter(ChatHistory.id == history_id, ChatHistory.user_id == user.id).first()
                         if history_item:
                             messages = json.loads(history_item.report_json) if history_item.report_json else []
                             messages.append({"role": "assistant", "content": {"summary": f"**Research Failed:** {research_result.error}"}})
                             history_item.report_json = json.dumps(messages)
                             db.commit()
                 except Exception:
                     pass
                 finally:
                     db.close()
        else:
            logger.error(f"Background task for {task_id} returned unexpected type: {type(research_result)}. Storing generic error.")
            task_results[task_id] = ResultResponse(status="error", error=ErrorResponse(error="Agent returned unexpected result type", details=str(research_result)))

    except ImportError as ie:
         logger.error(f"ImportError during background task for task_id {task_id}: {ie}. Agent might not be available.", exc_info=True)
         task_results[task_id] = ResultResponse(status="error", error=ErrorResponse(error="Agent component import failed", details=str(ie)))
    except Exception as e:
        logger.error(f"Exception during background task for task_id {task_id}, query '{query}': {e}", exc_info=True)
        task_results[task_id] = ResultResponse(status="error", error=ErrorResponse(error="Internal server error during research", details=str(e)))


from fastapi import FastAPI, Depends, HTTPException, status, BackgroundTasks, Header, UploadFile, File
import uuid
import json
import io
import PyPDF2
from docx import Document

# ...

# --- API Endpoints ---\

# --- Search Endpoints ---

@app.post("/research", response_model=TaskResponse, status_code=status.HTTP_202_ACCEPTED)
async def start_research_endpoint(request: ResearchRequest, background_tasks: BackgroundTasks, authorization: Optional[str] = Header(None)):
    """
    Receives a research query, starts the research process in the background,
    and returns a task ID.
    """
    logger.info(f"Received query: '{request.query}' with language '{request.language}'. Starting background task.")
    task_id = str(uuid.uuid4())
    
    token = None
    if authorization and authorization.startswith("Bearer "):
        token = authorization.split(" ")[1]

    # Create History Synchronously if it's a new thread so the user can immediately see it in the sidebar
    db_history_id = request.history_id
    if token and not db_history_id:
        from research_system.database import SessionLocal
        db = SessionLocal()
        try:
            user = auth.get_current_user(token, db)
            if user:
                # Create placeholder history item with the user's query
                messages = [{"role": "user", "content": request.query}]
                new_history = ChatHistory(
                    user_id=user.id,
                    query=request.query,
                    report_json=json.dumps(messages)
                )
                db.add(new_history)
                db.commit()
                db.refresh(new_history)
                db_history_id = new_history.id
        except Exception as e:
            logger.error(f"Failed to pre-create history: {e}")
        finally:
            db.close()

    # Pass the db_history_id (either newly created or provided) to the background task
    background_tasks.add_task(run_background_research, task_id, request.query, request.language, request.chat_history, db_history_id, token)

    # Store initial processing status
    task_results[task_id] = ResultResponse(status="processing", result=None)

    return TaskResponse(task_id=task_id, message="Web research process started.", history_id=db_history_id)


@app.get("/results/{task_id}", response_model=ResultResponse)
async def get_results_endpoint(task_id: str):
    """
    Retrieves the status or result of a web research task.
    """
    logger.debug(f"Checking results for task_id: {task_id}")
    result_info = task_results.get(task_id) # Renamed variable

    if not result_info:
        logger.warning(f"Task ID not found: {task_id}")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task ID not found")

    logger.debug(f"Current status for task_id {task_id}: {result_info.status}")
    # Optionally remove completed/error tasks after retrieval? Or implement TTL?
    # Be careful with concurrent requests if modifying shared dict here.

    return result_info

@app.post("/extract-text")
async def extract_text_endpoint(file: UploadFile = File(...)):
    """
    Extracts text from uploaded PDF, DOCX, or TXT/MD files.
    """
    try:
        content = await file.read()
        text = ""
        filename = file.filename.lower()
        
        if filename.endswith(".pdf"):
            pdf_reader = PyPDF2.PdfReader(io.BytesIO(content))
            for page in pdf_reader.pages:
                text += page.extract_text() + "\n"
        elif filename.endswith(".docx"):
            doc = Document(io.BytesIO(content))
            for para in doc.paragraphs:
                text += para.text + "\n"
        elif filename.endswith(".txt") or filename.endswith(".md"):
            text = content.decode("utf-8", errors="replace")
        else:
            raise HTTPException(status_code=400, detail="Unsupported file format")
            
        return {"filename": file.filename, "text": text.strip()}
    except Exception as e:
        logger.error(f"Error extracting text from {file.filename}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to extract text: {e}")

class HistoryItem(BaseModel):
    id: int
    query: str
    created_at: str

@app.get("/history", response_model=List[HistoryItem])
async def get_history(authorization: str = Header(...), db: Session = Depends(get_db)):
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid token")
    token = authorization.split(" ")[1]
    
    user = auth.get_current_user(token, db)
    if not user:
        raise HTTPException(status_code=401, detail="Unauthorized")
        
    histories = db.query(ChatHistory).filter(ChatHistory.user_id == user.id).order_by(ChatHistory.created_at.desc()).all()
    
    return [HistoryItem(id=h.id, query=h.query, created_at=h.created_at.isoformat()) for h in histories]

@app.get("/history/{history_id}")
async def get_history_detail(history_id: int, authorization: str = Header(...), db: Session = Depends(get_db)):
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid token")
    token = authorization.split(" ")[1]
    
    user = auth.get_current_user(token, db)
    if not user:
        raise HTTPException(status_code=401, detail="Unauthorized")
        
    history = db.query(ChatHistory).filter(ChatHistory.id == history_id, ChatHistory.user_id == user.id).first()
    if not history:
        raise HTTPException(status_code=404, detail="History not found")
        
    report_data = json.loads(history.report_json) if history.report_json else []
    # If it's an old format (dict), convert to array
    if isinstance(report_data, dict):
        report_data = [
            {"role": "user", "content": history.query},
            {"role": "assistant", "content": report_data}
        ]
        
    return {"query": history.query, "messages": report_data}
    
@app.delete("/history/{history_id}")
async def delete_history(history_id: int, authorization: str = Header(...), db: Session = Depends(get_db)):
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid token")
    token = authorization.split(" ")[1]
    
    user = auth.get_current_user(token, db)
    if not user:
        raise HTTPException(status_code=401, detail="Unauthorized")
        
    history = db.query(ChatHistory).filter(ChatHistory.id == history_id, ChatHistory.user_id == user.id).first()
    if not history:
        raise HTTPException(status_code=404, detail="History not found")
        
    db.delete(history)
    db.commit()
    
    return {"message": "History deleted successfully"}

@app.get("/")
async def root():
    """
    Root endpoint providing a welcome message.
    """
    return {"message": "Welcome to the Web Research Agent API!"} # Updated message


if __name__ == "__main__":
    # Note: Reload=True is good for development. Consider turning it off for production.
    # The path here 'research_system.api.main:app' should work if uvicorn is run
    # from the project root directory (parent of research_system).
    # Example: python -m uvicorn research_system.api.main:app --reload
    uvicorn.run("research_system.api.main:app", host="0.0.0.0", port=8000, reload=True) 