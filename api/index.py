from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel
from typing import List, Optional, Union
from datetime import datetime
from bson import ObjectId
import json
import os
from dotenv import load_dotenv

load_dotenv()
app = FastAPI()

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://survey-app-frontend-mwv6kuqz9-mr-195s-projects.vercel.app"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# MongoDB Atlas connection string
# Replace with your actual connection string
MONGODB_URL = os.getenv("MONGODB_URL")
# Create a client instance
try:
    client = AsyncIOMotorClient(MONGODB_URL)
    # Ping the server to confirm connection
    client.admin.command('ping')
    print("Successfully connected to MongoDB Atlas!")
except Exception as e:
    print(f"Error connecting to MongoDB Atlas: {e}")
    raise

db = client.voting_app

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

# Health check endpoint
@app.get("/api/health")
async def health_check():
    try:
        print("MONGODB_URL", MONGODB_URL)
        await client.admin.command('ping')
        return {"status": "healthy", "database": "connected"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database connection error: {str(e)}")

# Routes
@app.get("/api/questions")
async def get_questions():
    try:
        questions = await db.questions.find().to_list(length=None)
        # Convert ObjectId to string for JSON serialization
        for question in questions:
            question["_id"] = str(question["_id"])
        return questions
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching questions: {str(e)}")

@app.get("/api/questions/{question_id}")
async def get_question(question_id: str):
    try:
        question = await db.questions.find_one({"_id": ObjectId(question_id)})
        if question:
            question["_id"] = str(question["_id"])
            return question
        raise HTTPException(status_code=404, detail="Question not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching question: {str(e)}")

@app.post("/api/responses")
async def submit_response(response: Response):
    try:
        response_dict = response.dict()
        response_dict["submitted_at"] = datetime.utcnow()
        result = await db.responses.insert_one(response_dict)
        return {"response_id": str(result.inserted_id)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error submitting response: {str(e)}")

@app.get("/api/responses/{question_id}")
async def get_responses(question_id: str):
    try:
        responses = await db.responses.find({"question_id": question_id}).to_list(length=None)
        for response in responses:
            response["_id"] = str(response["_id"])
        return responses
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching responses: {str(e)}")