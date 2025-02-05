from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel
from typing import List, Optional, Union
from datetime import datetime
from bson import ObjectId
import os
from dotenv import load_dotenv
from contextlib import asynccontextmanager

# Load environment variables
load_dotenv()
MONGODB_URL = os.getenv("MONGODB_URL")

# Global database client
client = None

# Startup and shutdown events
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    global client
    client = AsyncIOMotorClient(
        MONGODB_URL,
        maxPoolSize=10,
        minPoolSize=5,
        maxIdleTimeMS=50000,
        connectTimeoutMS=5000,
        serverSelectionTimeoutMS=5000
    )
    yield
    # Shutdown
    if client:
        client.close()

# Initialize FastAPI app with lifespan
app = FastAPI(lifespan=lifespan)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Dependency to get database
async def get_db():
    global client
    db = client.voting_app
    return db

# Pydantic models
class Question(BaseModel):
    question_text: str
    type: str
    options: Optional[List[str]]
    scale: Optional[int]

class Response(BaseModel):
    question_id: str
    response_text: Union[str, int, List[str]]
    submitted_at: datetime

# Health Check Endpoint
@app.get("/api/health")
async def health_check(db=Depends(get_db)):
    try:
        print("MONGODB_URL printing ", MONGODB_URL)
        await db.command('ping')
        return {"status": "healthy", "database": "connected"}
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))

# Fetch All Questions with caching headers
@app.get("/api/questions")
async def get_questions(db=Depends(get_db)):
    try:
        questions = await db.questions.find().to_list(length=None)
        return [
            {**question, "_id": str(question["_id"])}
            for question in questions
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Fetch Single Question
@app.get("/api/questions/{question_id}")
async def get_question(question_id: str, db=Depends(get_db)):
    try:
        question = await db.questions.find_one({"_id": ObjectId(question_id)})
        if not question:
            raise HTTPException(status_code=404, detail="Question not found")
        question["_id"] = str(question["_id"])
        return question
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Submit Response
@app.post("/api/responses")
async def submit_response(response: Response, db=Depends(get_db)):
    try:
        response_dict = response.dict()
        response_dict["submitted_at"] = datetime.utcnow()
        result = await db.responses.insert_one(response_dict)
        return {"response_id": str(result.inserted_id)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Get Responses for a Question
@app.get("/api/responses/{question_id}")
async def get_responses(question_id: str, db=Depends(get_db)):
    try:
        responses = await db.responses.find({"question_id": question_id}).to_list(length=None)
        return [
            {**response, "_id": str(response["_id"])}
            for response in responses
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Root route for Vercel
@app.get("/")
async def root():
    return {"message": "Voting API is running"}