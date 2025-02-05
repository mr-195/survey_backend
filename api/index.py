from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel
from typing import List, Optional, Union
from datetime import datetime
from bson import ObjectId
import os
from dotenv import load_dotenv
from contextlib import asynccontextmanager

load_dotenv()

MONGODB_URL = os.getenv("MONGODB_URL")
def get_db():
    client = AsyncIOMotorClient(MONGODB_URL)
    return client,client.voting_app
# Lifespan context manager to handle startup & shutdown
@asynccontextmanager
async def lifespan(app: FastAPI):
    client,db = get_db()
    print("✅ Successfully connected to MongoDB")
    
    yield  # Let FastAPI run

    print("🛑 Closing MongoDB connection...")
    client.close()

app = FastAPI(lifespan=lifespan)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydantic models
class Question(BaseModel):
    question_text: str
    type: str
    options: Optional[List[str]]  # For MCQ
    scale: Optional[int]  # For Likert

class Response(BaseModel):
    question_id: str
    response_text: Union[str, int, List[str]]
    submitted_at: datetime

# Health check
@app.get("/api/health")
async def health_check():
    try:
        client,db = get_db()
        await client.admin.command('ping')
        client.close()
        return {"status": "healthy", "database": "connected"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database connection error: {str(e)}")

# Fetch questions
@app.get("/api/questions")
async def get_questions():
    try:
        client,db = get_db()
        questions = await db.questions.find().to_list(length=None)
        client.close()
        for question in questions:
            question["_id"] = str(question["_id"])
        return questions
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching questions: {str(e)}")

# Fetch a single question
@app.get("/api/questions/{question_id}")
async def get_question(question_id: str):
    try:
        client,db = get_db()
        question = await db.questions.find_one({"_id": ObjectId(question_id)})
        client.close()
        if question:
            question["_id"] = str(question["_id"])
            return question
        raise HTTPException(status_code=404, detail="Question not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching question: {str(e)}")

# Submit response
@app.post("/api/responses")
async def submit_response(response: Response):
    try:
        client,db = get_db()
        response_dict = response.dict()
        response_dict["submitted_at"] = datetime.utcnow()
        result = await db.responses.insert_one(response_dict)
        client.close()
        return {"response_id": str(result.inserted_id)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error submitting response: {str(e)}")

# Get responses for a question
@app.get("/api/responses/{question_id}")
async def get_responses(question_id: str):
    
    try:
        client,db = get_db()
        responses = await db.responses.find({"question_id": question_id}).to_list(length=None)
        for response in responses:
            response["_id"] = str(response["_id"])
        client.close()
        return responses
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching responses: {str(e)}")

# Run server command: uvicorn index:app --host 0.0.0.0 --port 8000 --reload

