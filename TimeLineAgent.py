import os
import json
from dotenv import load_dotenv
from langgraph.prebuilt import create_react_agent
from langgraph.graph import StateGraph
from langgraph.graph import MessagesState, START, END
from langgraph.types import Command
from langchain_core.messages import HumanMessage, AIMessage
from langchain_openai import ChatOpenAI
from datetime import datetime
import uuid


# Data
weekend_ideas = [
    {
        "idea_id": 1,
        "title": "Luxury Weekend Getaway",
        "description": "Upgrade your weekend trip with a stay at a 4-star hotel, gourmet dining experiences, and a private guided tour of local attractions.",
        "budget": 800
    },
    {
        "idea_id": 2,
        "title": "Adventure and Relaxation Weekend",
        "description": "Combine thrilling outdoor activities like zip-lining or kayaking during the day with spa treatments and fine dining in the evening.",
        "budget": 750
    },
    {
        "idea_id": 3,
        "title": "Cultural Immersion Weekend",
        "description": "Enjoy a weekend exploring museums, attending a live theater performance, and dining at top-rated local restaurants.",
        "budget": 700
    },
    {
        "idea_id": 4,
        "title": "Exclusive Weekend Retreat",
        "description": "Book a private cabin with amenities such as a hot tub and chef-prepared meals, plus a personalized itinerary including wine tasting or cooking classes.",
        "budget": 850
    }
]

weekend_ideas_summary = "\n".join(
    f"id={idea['idea_id']} - {idea['title']} - ${idea['budget']} - {idea['description']}"
    for idea in weekend_ideas
)

# Setup
load_dotenv()
openai_api_key = os.getenv("API_KEY_GPT")
os.environ["OPENAI_API_KEY"] = openai_api_key
llm = ChatOpenAI(model="gpt-4.1-mini", temperature=0.7)

# idea system prompt
timeline_agent_prompt = (
    "You are a helpful assistant helping users build a custom event plan from a list of activities.\n"
    "Each activity has an idea_id, a title, a budget, and a description.\n"
    "You will be given a list of activities and a prompt. Your job is to return the idea_ids of some selected activities\n"
    "in the best order they could be arranged for the user's goal and fit in the user's event's time.\n\n"
    "You must respond with a JSON list of activities you choose and schedule.\n"
    "Each object in the list should have the following keys:\n"
    "- 'card_type': always 'IdeaCard'\n"
    "- 'title': the activity title\n"
    "- 'description': the activity description\n"
    "- 'budget': the activity budget\n"
    "- 'time': suggest a realistic date and time to schedule the activity, must show date in ISO format (e.g. 2025-05-04T10:00:00).\n\n"
    "You will be given the current datetime to help with planning. Respond ONLY with the JSON list.\n"
    "RESPONSE RULES:\n"
    "- Respond ONLY with a valid JSON array. Do not include any explanation, markdown, or text.\n"
    "- DO NOT wrap your response in ```json or any other formatting.\n"
    "- Ensure all keys and string values use double quotes.\n\n"
    "Example:\n"
    "[\n"
    "  {\n"
    "    \"card_type\": \"IdeaCard\",\n"
    "    \"title\": \"Luxury Getaway\",\n"
    "    \"description\": \"Enjoy a spa and fine dining weekend.\",\n"
    "    \"budget\": 900,\n"
    "    \"time\": \"2025-05-04T10:00:00\"\n"
    "  }\n"
    "]"
)

# LangGraph Agent
event_agent = create_react_agent(
    llm,
    tools=[],
    prompt=timeline_agent_prompt
)

class AgentState(MessagesState):
    pass

# Create the node function for the agent
def create_agent_node(agent, agent_name: str):
    """Creates a node function for a given agent with rewritten query injection."""
    def agent_node(state: dict) -> Command:
        print(f"\n--- Running {agent_name} ---")

        input_for_agent = state
        rewritten_query = state.get('rewritten_query_for_next_agent')

        if rewritten_query:
            print(f"Injecting rewritten query into agent input: '{rewritten_query}'")
            modified_input_state = state.copy()
            current_messages = modified_input_state.get('messages', [])
            if not isinstance(current_messages, list):
                current_messages = []
            modified_input_state['messages'] = list(current_messages) + [HumanMessage(content=rewritten_query)]
            input_for_agent = modified_input_state

        result = agent.invoke(input_for_agent)
        agent_response = result["messages"][-1]
        return Command(update={"messages": [agent_response]}, goto=END)

    return agent_node

# Build the LangGraph
builder = StateGraph(AgentState)
builder.add_node("TimeLineAgent", create_agent_node(event_agent, "TimeLineAgent"))
builder.set_entry_point("TimeLineAgent")
builder.add_edge("TimeLineAgent", END)
graph = builder.compile()

# Run query
def run_query(prompt: str):
    current_time = datetime.now().strftime("%A %B %d, %Y %I:%M %p")
    user_prompt = (
        f"{prompt}\n"
        f"Here is the current datetime: {current_time}\n\n"
        f"Here are the current pool of activities:\n\n{weekend_ideas_summary}"
    )

    # Run the graph
    events = graph.stream({"messages": [HumanMessage(content=user_prompt)]}, stream_mode="values")
    final_state = list(events)[-1]
    in_timeline_list = []   

    for msg in final_state.get("messages", []):
        print("\nRAW AI RESPONSE:\n", msg.content) 

        try:
            cards = json.loads(msg.content)  

            for card in cards:
                card["id"] = f"card-idea-{uuid.uuid4().hex[:6]}"
            in_timeline_list.extend(cards)

        except json.JSONDecodeError as e:
            print(f"Error decoding JSON: {e}")

    print(in_timeline_list)

    with open("timeline.json") as f:
        timeline_data = json.load(f)

    timeline_data["in_timeline"] = in_timeline_list

    with open("timeline.json", "w") as f:
        json.dump(timeline_data, f, indent=2)

# Run
if __name__ == "__main__":
    run_query("Make a plan with activities using the following activities:\n")
