from langgraph.graph import StateGraph, END
from langgraph.prebuilt import tool_node
from typing import List, Dict, TypedDict
from openai import OpenAI
from datetime import date

client = OpenAI(api_key="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")

def idea_to_timeline_node(state: dict) -> dict:
    today_str = date.today().isoformat()  # e.g. '2025-05-03'
    ideas = state['ideas']
    
    prompt = f"""
You are a Planning AI Agent. Your ONLY job is to organize a given list of ideas into a realistic timeline.

IMPORTANT:
- DO NOT create new ideas.
- ONLY use the input ideas.
- Each idea has: 'Title', 'description', and 'cost'.
- Organize these into a smart timeline based on urgency, affordability, and timing.

Today's date is {today_str}.
DO NOT schedule anything before this date.

Here are the user's ideas:
{ideas}

Your output MUST be:
1. A JSON-style array of dictionaries.
2. Each dictionary should look like this:
   {{
     'type': 'idea',
     'content': '<short summary of the input idea>',
     'time': '<date in ISO format like "2025-06-01">'
   }}

Guidelines:
- Only use the user's ideas — do NOT create new ones.
- Use ISO 8601 format: YYYY-MM-DD (e.g. "2025-10-01")
- If unsure of the day, use the 1st of the month.
- Do not assign any dates before {today_str}.

Your mission: Create a clear, achievable roadmap using ONLY the user's provided ideas.
"""
    completion = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "You are an AI agent."},
            {"role": "user", "content": prompt}
        ],
        temperature=0
    )
    response = completion.choices[0].message.content

    # Ideally validate and parse the response safely
    import json
    import re

    try:
        # Find JSON-like content using a regex (to ignore any extra text around it)
        match = re.search(r"\[\s*{.*?}\s*\]", response, re.DOTALL)
        if match:
            timeline = json.loads(match.group())
        else:
            timeline = []
    except Exception as e:
        print("Parsing error:", e)
        print("Raw model output:", response)
        timeline = []

    return {'timeline': timeline}


class TimelineState(TypedDict):
    ideas: List[Dict[str, str]]
    timeline: List[Dict[str, str]]

# Create the graph
graph = StateGraph(TimelineState)

# Add the timeline node
graph.add_node("generate_timeline", idea_to_timeline_node)
graph.set_entry_point("generate_timeline")
graph.set_finish_point("generate_timeline")  # Ends after generating timeline

timeline_app = graph.compile()

sample_ideas = [
    {'Title': 'Trip to Japan', 'description': 'A cultural trip to Tokyo and Kyoto', 'cost': '3000'},
    {'Title': 'Buy Electric Bike', 'description': 'For local commuting', 'cost': '1500'},
    {'Title': 'Emergency Fund', 'description': 'Save up for unforeseen circumstances', 'cost': '5000'}
]

result = timeline_app.invoke({'ideas': sample_ideas})
print(result['timeline'])