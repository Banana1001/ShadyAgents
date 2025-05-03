import datetime
import json
from typing import List
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import random
from test import run_combine_workflow

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

class CombineCardPayload(BaseModel):
    Card1: dict
    Card2: dict

class GeneratePlanPayload(BaseModel):
    Card: dict
    CardList: List


def generate_random_time(range_type: str) -> datetime.datetime:
    now = datetime.datetime.now()

    if range_type == "year":
        start = now - datetime.timedelta(days=365)
        end = now
    elif range_type == "month":
        start = now - datetime.timedelta(days=30)
        end = now
    elif range_type == "day":
        start = now - datetime.timedelta(days=1)
        end = now
    else:
        raise ValueError("Invalid range_type")

    # Generate random datetime between start and end
    delta = end - start
    random_seconds = random.randint(0, int(delta.total_seconds()))
    return start + datetime.timedelta(seconds=random_seconds)

def generate_ideas(n=5):
    ideas = []
    for _ in range(n):
        range_type = random.choice(["year", "month", "day"])
        random_time = generate_random_time(range_type)
        idea = {
            'id': random.randint(1, 1000),
            'type': 'idea',
            'content': f'idea {random.randint(1, 100)}',
            'time': random_time.isoformat(),
            'cost': random.randint(1, 1000)
        }
        ideas.append(idea)
    return ideas

@app.post("/generate-plan")
async def generate_plan(request: GeneratePlanPayload):
    # result = run_combine_workflow(request.Card, request.CardList)
    # print(f"Result: {result}")
    result = generate_ideas(5)  # Generate 5 random ideas for demonstration

    return {'cards': result}

@app.post("/combine-cards")
async def combine_cards(request: CombineCardPayload):
    card1 = request.Card1
    card2 = request.Card2
    result = run_combine_workflow(card1, card2)
    print(f"Result: {result}")

    return {'cards': [{'type': 'combine', 'content': f'idea {random.randint(1, 100)}', 'time': datetime.datetime.now().isoformat(), 'cost': random.randint(1, 1000)}]}
