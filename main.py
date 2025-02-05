from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel
from typing import List, Optional, Union
from datetime import datetime
from bson import ObjectId
import os
from dotenv import load_dotenv
import certifi

# Load environment variables
load_dotenv()
MONGODB_URL = os.getenv("MONGODB_URL")

# Database connection management
class Database:
    client: Optional[AsyncIOMotorClient] = None
    
    @classmethod
    def get_client(cls):
        if cls.client is None:
            # Initialize client with correct parameters
            cls.client = AsyncIOMotorClient(
                MONGODB_URL,
                tlsCAFile=certifi.where(),
                serverSelectionTimeoutMS=5000,
                connectTimeoutMS=10000,
                socketTimeoutMS=20000,
                maxPoolSize=10,
                minPoolSize=0,
                maxIdleTimeMS=50000,
                retryWrites=True
            )
        return cls.client

    @classmethod
    def get_db(cls):
        client = cls.get_client()
        return client.voting_app

# Initialize FastAPI app
app = FastAPI()

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Get database instance
def get_database():
    return Database.get_db()

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

# Root route
@app.get("/api")
async def root():
    return {"message": "Voting API is running"}

# Health Check
@app.get("/api/health")
async def health_check():
    db = get_database()
    try:
        await db.command('ping')
        return {"status": "healthy", "database": "connected"}
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))

# Fetch All Questions
@app.get("/api/questions")
async def get_questions():
    db = get_database()
    try:
        cursor = db.questions.find()
        questions = await cursor.to_list(length=100)
        return [
            {**question, "_id": str(question["_id"])}
            for question in questions
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Fetch Single Question
@app.get("/api/questions/{question_id}")
async def get_question(question_id: str):
    db = get_database()
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
async def submit_response(response: Response):
    db = get_database()
    try:
        response_dict = response.dict()
        response_dict["submitted_at"] = datetime.utcnow()
        result = await db.responses.insert_one(response_dict)
        return {"response_id": str(result.inserted_id)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Get Responses for a Question
@app.get("/api/responses/{question_id}")
async def get_responses(question_id: str):
    db = get_database()
    try:
        cursor = db.responses.find({"question_id": question_id})
        responses = await cursor.to_list(length=100)
        return [
            {**response, "_id": str(response["_id"])}
            for response in responses
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Shutdown event
@app.on_event("shutdown")
async def shutdown_db_client():
    if Database.client:
        Database.client.close()