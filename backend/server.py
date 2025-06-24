from fastapi import FastAPI, APIRouter, File, UploadFile, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import JSONResponse
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
import uuid
from datetime import datetime, timedelta
import json
import pandas as pd
import io
import bcrypt
import jwt
import base64
from openai import OpenAI
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# OpenAI client
openai_client = OpenAI(api_key=os.environ['OPENAI_API_KEY'])

# JWT settings
JWT_SECRET = "your-secret-key-change-in-production"
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION = timedelta(days=7)

# Create the main app without a prefix
app = FastAPI(title="RAG SaaS Application", description="AI-powered document analysis and reporting")

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

# Security
security = HTTPBearer()

# Models
class User(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    email: str
    name: str
    password_hash: str
    created_at: datetime = Field(default_factory=datetime.utcnow)

class UserCreate(BaseModel):
    email: str
    name: str
    password: str

class UserLogin(BaseModel):
    email: str
    password: str

class Document(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    filename: str
    file_type: str
    content: List[Dict[str, Any]]
    embeddings: List[List[float]]
    chunks: List[str]
    uploaded_at: datetime = Field(default_factory=datetime.utcnow)
    processed: bool = False

class QueryRequest(BaseModel):
    query: str
    language: str = "en"  # "en" or "id"

class QueryResponse(BaseModel):
    answer: str
    sources: List[str]
    context_used: List[str]

# Helper functions
def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))

def create_jwt_token(user_id: str) -> str:
    payload = {
        "user_id": user_id,
        "exp": datetime.utcnow() + JWT_EXPIRATION
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        payload = jwt.decode(credentials.credentials, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        user_id = payload.get("user_id")
        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid token")
        
        user = await db.users.find_one({"id": user_id})
        if user is None:
            raise HTTPException(status_code=401, detail="User not found")
        
        return User(**user)
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

def get_embeddings(texts: List[str]) -> List[List[float]]:
    """Generate embeddings using OpenAI API"""
    try:
        response = openai_client.embeddings.create(
            model="text-embedding-3-small",
            input=texts
        )
        return [embedding.embedding for embedding in response.data]
    except Exception as e:
        logging.error(f"Error generating embeddings: {e}")
        return []

def process_excel_file(file_content: bytes) -> tuple[List[str], List[Dict[str, Any]]]:
    """Process Excel file and extract text chunks"""
    try:
        df = pd.read_excel(io.BytesIO(file_content))
        
        # Convert DataFrame to structured data
        data = df.to_dict('records')
        
        # Create text chunks from each row
        chunks = []
        for row in data:
            chunk = " | ".join([f"{k}: {v}" for k, v in row.items() if pd.notna(v)])
            chunks.append(chunk)
        
        return chunks, data
    except Exception as e:
        logging.error(f"Error processing Excel file: {e}")
        return [], []

def process_json_file(file_content: bytes) -> tuple[List[str], List[Dict[str, Any]]]:
    """Process JSON file and extract text chunks"""
    try:
        data = json.loads(file_content.decode('utf-8'))
        
        if isinstance(data, list):
            chunks = []
            for item in data:
                if isinstance(item, dict):
                    chunk = " | ".join([f"{k}: {v}" for k, v in item.items()])
                    chunks.append(chunk)
                else:
                    chunks.append(str(item))
            return chunks, data
        else:
            # Single object
            chunk = " | ".join([f"{k}: {v}" for k, v in data.items()]) if isinstance(data, dict) else str(data)
            return [chunk], [data]
    except Exception as e:
        logging.error(f"Error processing JSON file: {e}")
        return [], []

def similarity_search(query_embedding: List[float], document_embeddings: List[List[float]], chunks: List[str], top_k: int = 5) -> List[tuple[str, float]]:
    """Perform similarity search using cosine similarity"""
    try:
        query_embedding = np.array(query_embedding).reshape(1, -1)
        doc_embeddings = np.array(document_embeddings)
        
        similarities = cosine_similarity(query_embedding, doc_embeddings)[0]
        
        # Get top_k most similar chunks
        top_indices = np.argsort(similarities)[::-1][:top_k]
        
        results = []
        for idx in top_indices:
            if similarities[idx] > 0.1:  # Threshold for relevance
                results.append((chunks[idx], float(similarities[idx])))
        
        return results
    except Exception as e:
        logging.error(f"Error in similarity search: {e}")
        return []

# Auth endpoints
@api_router.post("/auth/register")
async def register(user_create: UserCreate):
    # Check if user already exists
    existing_user = await db.users.find_one({"email": user_create.email})
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Create new user
    user = User(
        email=user_create.email,
        name=user_create.name,
        password_hash=hash_password(user_create.password)
    )
    
    await db.users.insert_one(user.dict())
    
    # Generate JWT token
    token = create_jwt_token(user.id)
    
    return {
        "message": "User registered successfully",
        "token": token,
        "user": {
            "id": user.id,
            "email": user.email,
            "name": user.name
        }
    }

@api_router.post("/auth/login")
async def login(user_login: UserLogin):
    # Find user
    user_data = await db.users.find_one({"email": user_login.email})
    if not user_data:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    user = User(**user_data)
    
    # Verify password
    if not verify_password(user_login.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    # Generate JWT token
    token = create_jwt_token(user.id)
    
    return {
        "message": "Login successful",
        "token": token,
        "user": {
            "id": user.id,
            "email": user.email,
            "name": user.name
        }
    }

# Document endpoints
@api_router.delete("/documents/{document_id}")
async def delete_document(
    document_id: str,
    current_user: User = Depends(get_current_user)
):
    # Find and delete the document
    result = await db.documents.delete_one({
        "id": document_id,
        "user_id": current_user.id
    })
    
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Document not found")
    
    return {"message": "Document deleted successfully"}

@api_router.post("/documents/upload")
async def upload_document(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user)
):
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided")
    
    # Read file content
    content = await file.read()
    
    # Process file based on type
    file_extension = file.filename.lower().split('.')[-1]
    
    if file_extension in ['xlsx', 'xls']:
        chunks, data = process_excel_file(content)
        file_type = "excel"
    elif file_extension == 'json':
        chunks, data = process_json_file(content)
        file_type = "json"
    else:
        raise HTTPException(status_code=400, detail="Unsupported file type. Please upload Excel or JSON files.")
    
    if not chunks:
        raise HTTPException(status_code=400, detail="Could not process file content")
    
    # Generate embeddings
    embeddings = get_embeddings(chunks)
    if not embeddings:
        raise HTTPException(status_code=500, detail="Error generating embeddings")
    
    # Save document to database
    document = Document(
        user_id=current_user.id,
        filename=file.filename,
        file_type=file_type,
        content=data,
        embeddings=embeddings,
        chunks=chunks,
        processed=True
    )
    
    await db.documents.insert_one(document.dict())
    
    return {
        "message": "Document uploaded and processed successfully",
        "document_id": document.id,
        "filename": document.filename,
        "chunks_count": len(chunks),
        "file_type": file_type
    }

@api_router.get("/documents")
async def list_documents(current_user: User = Depends(get_current_user)):
    documents = await db.documents.find({"user_id": current_user.id}).to_list(100)
    
    return [
        {
            "id": doc["id"],
            "filename": doc["filename"],
            "file_type": doc["file_type"],
            "uploaded_at": doc["uploaded_at"],
            "processed": doc["processed"],
            "chunks_count": len(doc.get("chunks", []))
        }
        for doc in documents
    ]

# RAG Query endpoint
@api_router.post("/query", response_model=QueryResponse)
async def rag_query(
    query_request: QueryRequest,
    current_user: User = Depends(get_current_user)
):
    if not query_request.query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty")
    
    # Get user's documents
    documents = await db.documents.find({"user_id": current_user.id, "processed": True}).to_list(100)
    
    if not documents:
        raise HTTPException(status_code=400, detail="No processed documents found. Please upload documents first.")
    
    # Generate query embedding
    query_embeddings = get_embeddings([query_request.query])
    if not query_embeddings:
        raise HTTPException(status_code=500, detail="Error processing query")
    
    query_embedding = query_embeddings[0]
    
    # Search across all documents
    all_results = []
    source_docs = []
    
    for doc in documents:
        doc_results = similarity_search(
            query_embedding, 
            doc["embeddings"], 
            doc["chunks"], 
            top_k=3
        )
        
        for chunk, score in doc_results:
            all_results.append((chunk, score, doc["filename"]))
            if doc["filename"] not in source_docs:
                source_docs.append(doc["filename"])
    
    # Sort by similarity score and take top results
    all_results.sort(key=lambda x: x[1], reverse=True)
    top_results = all_results[:5]
    
    if not top_results:
        return QueryResponse(
            answer="Maaf, saya tidak dapat menemukan informasi yang relevan dalam dokumen Anda untuk menjawab pertanyaan tersebut." if query_request.language == "id" else "Sorry, I couldn't find relevant information in your documents to answer that question.",
            sources=[],
            context_used=[]
        )
    
    # Prepare context for OpenAI
    context = "\n\n".join([result[0] for result in top_results])
    context_used = [result[0] for result in top_results]
    
    # Generate response using OpenAI
    system_prompt = (
        "Anda adalah asisten AI yang membantu menganalisis data dan membuat laporan. "
        "Berdasarkan konteks yang diberikan, berikan jawaban yang akurat dan informatif. "
        "Jika pertanyaan dalam bahasa Indonesia, jawab dalam bahasa Indonesia. "
        "Jika dalam bahasa Inggris, jawab dalam bahasa Inggris."
        if query_request.language == "id" else
        "You are an AI assistant that helps analyze data and create reports. "
        "Based on the provided context, give accurate and informative answers. "
        "Answer in the same language as the question."
    )
    
    try:
        response = openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Context:\n{context}\n\nQuestion: {query_request.query}\n\nPlease provide a comprehensive answer based on the context provided."}
            ],
            max_tokens=500,
            temperature=0.3
        )
        
        answer = response.choices[0].message.content
        
    except Exception as e:
        logging.error(f"Error generating response: {e}")
        raise HTTPException(status_code=500, detail="Error generating response")
    
    return QueryResponse(
        answer=answer,
        sources=source_docs,
        context_used=context_used
    )

# Report generation endpoint
@api_router.post("/reports/generate")
async def generate_report(
    query_request: QueryRequest,
    current_user: User = Depends(get_current_user)
):
    # Get RAG response first
    rag_response = await rag_query(query_request, current_user)
    
    # Get user's documents for additional context
    documents = await db.documents.find({"user_id": current_user.id, "processed": True}).to_list(100)
    
    # Extract data from documents and context for Excel report
    report_data = []
    
    # Try to extract tabular data from the context
    for context_chunk in rag_response.context_used:
        # Parse pipe-separated data back to structured format
        if "|" in context_chunk:
            row_data = {}
            pairs = context_chunk.split(" | ")
            for pair in pairs:
                if ":" in pair:
                    key, value = pair.split(":", 1)
                    row_data[key.strip()] = value.strip()
            if row_data:
                report_data.append(row_data)
    
    # If no structured data found, create a summary report
    if not report_data:
        report_data = [{
            "Query": query_request.query,
            "Answer": rag_response.answer,
            "Language": query_request.language,
            "Generated_At": datetime.utcnow().isoformat(),
            "Sources": ", ".join(rag_response.sources),
            "Document_Count": len(documents)
        }]
    
    # Create Excel file
    df = pd.DataFrame(report_data)
    excel_file = io.BytesIO()
    df.to_excel(excel_file, index=False, sheet_name='RAG Report')
    excel_file.seek(0)
    
    # Convert to base64 for JSON response
    import base64
    excel_b64 = base64.b64encode(excel_file.getvalue()).decode()
    
    return {
        "message": "Excel report generated successfully",
        "excel_data": excel_b64,
        "filename": f"rag-report-{datetime.utcnow().strftime('%Y%m%d-%H%M%S')}.xlsx",
        "query": query_request.query,
        "answer": rag_response.answer,
        "sources": rag_response.sources
    }

# Health check
@api_router.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}

# Include the router in the main app
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()