import datetime
import json
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import random

app = FastAPI()

# Allow frontend to communicate with backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # or ["http://localhost:3000"]
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class MessageRequest(BaseModel):
    message: str

def generate_ideas(n=5):
    ideas = []
    for _ in range(n):
        idea = {
            'type': 'idea',
            'content': f'idea {random.randint(1, 100)}',
            'time': datetime.datetime.now().isoformat()
        }
        ideas.append(idea)
    return ideas

@app.post("/generate-plan")
async def generate_plan(request: MessageRequest):
    result = generate_ideas(3)
    return json.dumps(result, indent=2)

@app.post("/combine-cards")
async def combine_cards(request: MessageRequest):
    return {'type': 'combine', 'content': f'idea {random.randint(1, 100)}', 'time': datetime.datetime.now().isoformat()}
