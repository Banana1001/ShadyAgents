import os
import random
import datetime
import json
import uuid
import re # Import re at the top
from typing import Annotated, Literal, List, Dict, Any, Optional, Tuple, Union
from typing_extensions import TypedDict
from dotenv import load_dotenv

# --- Langchain/LangGraph Imports ---
from langchain_core.messages import HumanMessage, BaseMessage, AIMessage, ToolMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, START, END, MessagesState
from langgraph.prebuilt import create_react_agent
from langgraph.types import Command

from langchain_core.runnables import RunnableLambda
from langchain_community.chat_message_histories import SQLChatMessageHistory

# --- Configuration ---
TIMELINE_FILE = "timeline.json"
TRANSACTIONS_FILE = "transactions.json"

# --- Environment Setup ---
load_dotenv()
openai_api_key = os.getenv('API_KEY_GPT')
if not openai_api_key:
    print("Warning: OPENAI_API_KEY not found in environment variables. LLM calls may fail.")

# --- Set up LLM ---
llm = ChatOpenAI(model="gpt-4.1-mini", temperature=0.7, api_key=openai_api_key)

# --- Data Structures ---
CardData = Dict[str, Any]

# --- Timeline/Card Management ---
# ... (load_timeline, save_timeline, add_custom_card, add_idea_card, get_card, format_card_for_prompt, print_timeline functions remain the same) ...
def delete_card_from_timeline(all_cards_dict: Dict[str, CardData], card_id: str) -> bool:
    """
    Deletes a card with the given ID from the unified card dictionary.
    Modifies the dictionary in place.
    Returns True if the card was found and deleted, False otherwise.
    """
    if card_id in all_cards_dict:
        del all_cards_dict[card_id]
        print(f"Deleted card '{card_id}' from internal dictionary.")
        return True
    else:
        # This case should ideally not happen if the ID came from the same loaded data,
        # but good to keep for robustness.
        print(f"Card '{card_id}' not found in internal dictionary for deletion.")
        return False

def load_timeline() -> Dict[str, CardData]:
    """Loads cards from the timeline.json file (in/out lists)
       and returns a unified dictionary keyed by card ID.
    """
    all_cards: Dict[str, CardData] = {}
    if not os.path.exists(TIMELINE_FILE):
        # Create default structure if file doesn't exist
        print(f"{TIMELINE_FILE} not found. Creating default file.")
        default_idea_card: CardData = {
            "id": "card-idea-default",
            "card_type": "IdeaCard",
            "title": "Weekend Trip Example",
            "description": "A sample idea card for a weekend getaway.",
            "budget": "Medium",
            "time": "Weekend",
            "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat()
        }
        # Create the initial dictionary (key = id)
        initial_cards = {default_idea_card["id"]: default_idea_card}
        # Save it using the new save function, which will create the list structure
        save_timeline(initial_cards)
        print(f"Created default '{TIMELINE_FILE}' with an example IdeaCard in 'in_timeline'.")
        return initial_cards # Return the dict representation

    try:
        with open(TIMELINE_FILE, 'r') as f:
            timeline_data = json.load(f)

        # Validate basic structure
        if not isinstance(timeline_data, dict) or "in_timeline" not in timeline_data or "out_timeline" not in timeline_data:
             print(f"Warning: {TIMELINE_FILE} has unexpected structure. Starting fresh.")
             # Optionally backup the old file here
             return {} # Start empty

        # Combine lists into a single dictionary
        for card in timeline_data.get("in_timeline", []):
            if isinstance(card, dict) and "id" in card:
                all_cards[card["id"]] = card
            else:
                print(f"Warning: Found invalid item in 'in_timeline': {card}")
        for card in timeline_data.get("out_timeline", []):
             if isinstance(card, dict) and "id" in card:
                 # Check for duplicate IDs across lists (shouldn't happen with save logic)
                 if card["id"] in all_cards:
                     print(f"Warning: Duplicate card ID '{card['id']}' found in both in/out lists. Using entry from 'in_timeline'.")
                     continue # Prioritize 'in_timeline' if duplicate somehow occurs
                 all_cards[card["id"]] = card
             else:
                 print(f"Warning: Found invalid item in 'out_timeline': {card}")

        return all_cards

    except (json.JSONDecodeError, IOError) as e:
        print(f"Error loading {TIMELINE_FILE}: {e}. Starting with empty card list.")
        # Optionally backup the corrupt file here
        return {}

def save_timeline(all_cards: Dict[str, CardData]):
    """Saves the unified card dictionary into the timeline.json file,
       splitting cards into 'in_timeline' (IdeaCards) and
       'out_timeline' (CustomCards) lists.
    """
    in_timeline_list: List[CardData] = []
    out_timeline_list: List[CardData] = []

    # Sort cards by creation date before splitting for consistent list order
    sorted_cards = sorted(all_cards.values(), key=lambda c: c.get("created_at", ""))

    for card in sorted_cards:
        card_type = card.get("card_type")
        if card_type == "IdeaCard":
            in_timeline_list.append(card)
        elif card_type == "CustomCard":
            out_timeline_list.append(card)
        else:
            # Default: Put unknown types in 'out_timeline'
            print(f"Warning: Card '{card.get('id', 'N/A')}' has unknown type '{card_type}'. Placing in 'out_timeline'.")
            out_timeline_list.append(card)

    timeline_data = {
        "in_timeline": in_timeline_list,
        "out_timeline": out_timeline_list
    }

    try:
        with open(TIMELINE_FILE, 'w') as f:
            json.dump(timeline_data, f, indent=2) # Using indent=2 to match user example
        print("============================================================================================================================================================")
    except IOError as e:
        print(f"Error saving {TIMELINE_FILE}: {e}")

def add_custom_card_by_id(user_query: str)-> Tuple[str, CardData]:
    """Adds a new CustomCard to the internal dictionary."""
    card_id = f"card-custom-{uuid.uuid4().hex[:6]}"
    new_card: CardData = {
        "id": card_id,
        "card_type": "CustomCard",
        "user_query": user_query.strip(),
        "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat()
    }
    all_cards = load_timeline()
    all_cards[card_id] = new_card
    save_timeline(all_cards) # Save the updated timeline
    print(f"CustomCard created with ID: {card_id} (will be saved to 'out_timeline')")
    return card_id, new_card

def add_custom_card(all_cards: Dict[str, CardData], user_query: str) -> Tuple[str, CardData]:
    """Adds a new CustomCard to the internal dictionary."""
    card_id = f"card-custom-{uuid.uuid4().hex[:6]}"
    new_card: CardData = {
        "id": card_id,
        "card_type": "CustomCard",
        "user_query": user_query.strip(),
        "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat()
    }
    all_cards[card_id] = new_card
    print(f"CustomCard created with ID: {card_id} (will be saved to 'out_timeline')")
    return card_id, new_card

def add_idea_card(
    all_cards: Dict[str, List[Dict[str, Any]]],
    idea_data: Dict[str, Any], # Expect dictionary like {'title': '...', 'description': '...', 'budget': '...', 'time': '...'}
    target_list: Literal['in_timeline', 'out_timeline'] = 'out_timeline' # Default to out_timeline
) -> Tuple[str, Dict[str, List[Dict[str, Any]]]]:
    """
    Adds a new IdeaCard based on idea_data to the specified list ('in_timeline' or 'out_timeline')
    within the provided all_cards dictionary. Does NOT save the file.

    Args:
        all_cards: The dictionary representing the timeline data (e.g., from load_timeline).
        idea_data: A dictionary containing the details for the new idea card.
        target_list: The key ('in_timeline' or 'out_timeline') of the list to add the card to.

    Returns:
        A tuple containing the new card's ID and the modified all_cards dictionary.
    """
    card_id = f"card-idea-{uuid.uuid4()}"
    # Validate idea_data structure minimally
    if not isinstance(idea_data, dict):
         print(f"Warning: Invalid idea_data passed to add_idea_card (expected dict, got {type(idea_data)}). Skipping card creation.")
         # Return dummy ID and unchanged data
         return f"invalid-data-{uuid.uuid4()}", all_cards

    new_card = {
        "id": card_id,
        "card_type": "IdeaCard",
        "title": idea_data.get("title", "Untitled Idea"),
        "description": idea_data.get("description", "No description provided."),
        "budget": idea_data.get("budget", "N/A"),
        "time": idea_data.get("time", "N/A"),
        "timestamp": datetime.datetime.now().isoformat()
    }

    # Ensure the target list exists in the dictionary
    if target_list not in all_cards:
        all_cards[target_list] = []
    # Ensure it's actually a list
    elif not isinstance(all_cards[target_list], list):
         print(f"Warning: Expected '{target_list}' to be a list, but found {type(all_cards[target_list])}. Reinitializing as list.")
         all_cards[target_list] = []


    all_cards[target_list].append(new_card)
    print(f"Prepared new IdeaCard '{card_id}' (Title: {new_card['title']}) for '{target_list}'.")
    return card_id, all_cards # Return ID and the modified dictionary


def get_card(all_cards: Dict[str, CardData], card_id: str) -> Optional[CardData]:
    """Retrieves a card by its ID from the internal dictionary."""
    return all_cards.get(card_id)

def format_card_for_prompt(card: CardData) -> str:
    """Formats card details into a string for LLM prompts."""
    card_type = card.get("card_type", "Unknown")
    card_id = card.get("id", "N/A")
    details = []
    if card_type == "CustomCard":
        details.append(f"Type: CustomCard")
        details.append(f"ID: {card_id}")
        details.append(f"Query: '{card.get('user_query', '')}'")
    elif card_type == "IdeaCard":
        details.append(f"Type: IdeaCard")
        details.append(f"ID: {card_id}")
        details.append(f"Title: '{card.get('title', '')}'")
        details.append(f"Description: '{card.get('description', '')}'")
        details.append(f"Budget: {card.get('budget', 'N/A')}")
        details.append(f"Time: {card.get('time', 'N/A')}")
    else:
        details.append(f"Type: Unknown")
        details.append(f"ID: {card_id}")
        details.append(f"Content: {json.dumps(card)}") # Fallback

    return f"Card({', '.join(details)})"

def print_timeline(all_cards: Dict[str, CardData]):
    """Prints the current list of cards, grouped by timeline status."""
    if not all_cards:
        print("\n--- Timeline Empty ---")
        print("Use 'create <query>' to add a CustomCard (out of timeline).")
        return

    # Separate based on type for printing
    in_timeline_cards = {k: v for k, v in all_cards.items() if v.get("card_type") == "IdeaCard"}
    out_timeline_cards = {k: v for k, v in all_cards.items() if v.get("card_type") == "CustomCard"}
    other_cards = {k: v for k, v in all_cards.items() if v.get("card_type") not in ["IdeaCard", "CustomCard"]}

    print("\n--- In Timeline (IdeaCards) ---")
    if not in_timeline_cards:
        print("  (No cards currently in timeline)")
    else:
        # Sort by creation date for consistent display
        for card_id, card_data in sorted(in_timeline_cards.items(), key=lambda item: item[1].get("created_at", "")):
             print(f"  ID: {card_id}")
             print(f"    Title: {card_data.get('title', 'N/A')}")
             print(f"    Desc: {card_data.get('description', 'N/A')}")
             print(f"    Budget: {card_data.get('budget', 'N/A')}")
             print(f"    Time: {card_data.get('time', 'N/A')}")
             print(f"    Created: {card_data.get('created_at', 'N/A')}")
             print("-" * 20)

    print("\n--- Out of Timeline (CustomCards) ---")
    if not out_timeline_cards:
        print("  (No cards currently out of timeline)")
    else:
         # Sort by creation date for consistent display
        for card_id, card_data in sorted(out_timeline_cards.items(), key=lambda item: item[1].get("created_at", "")):
            print(f"  ID: {card_id}")
            print(f"    Query: {card_data.get('user_query', 'N/A')}")
            print(f"    Created: {card_data.get('created_at', 'N/A')}")
            print("-" * 20)

    if other_cards:
        print("\n--- Other Cards (Unknown Type) ---")
         # Sort by creation date for consistent display
        for card_id, card_data in sorted(other_cards.items(), key=lambda item: item[1].get("created_at", "")):
             print(f"  ID: {card_id} ({card_data.get('card_type', 'Unknown')})")
             print(f"    Data: {card_data}")
             print(f"    Created: {card_data.get('created_at', 'N/A')}")
             print("-" * 20)

    print("--- End of Timeline ---")


# --- IdeaAgent Functions (From IdeaAgent.py) ---
# ... (load_transactions remains the same) ...
def load_transactions(file_path: str):
    """Load and parse transactions from JSON file."""
    try:
        with open(file_path, "r") as f:
            transactions = json.load(f)
        return transactions
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"Error loading transactions from {file_path}: {e}")
        # Return empty list as fallback
        return []
    except Exception as e:
        print(f"Unexpected error loading transactions from {file_path}: {e}")
        return []

class AgentState(MessagesState):
    waiting_for_response_from: Optional[str] = None
    completed_tasks: List[str] = []
    rewritten_query_for_next_agent: Optional[str] = None
    combine_flow_stage: Optional[Literal["combiner_started", "combiner_complete", "idea_started", "idea_complete"]] = None
    combine_data: Optional[Dict[str, Any]] = None
    current_ideas: List[Dict[str, Any]] = []
    action: Optional[Literal["plan", "idea"]] = None


# --- Agent Prompts and Definitions ---
# ... (combiner_agent_prompt, idea_agent_prompt, supervisor_system_prompt remain the same) ...
# CombinerAgent Prompt
# Updated portion of the combiner_agent_prompt
combiner_agent_prompt = (
    "You are the CombinerAgent. Your task is to analyze two JSON lists provided in the user's request, understanding their structure and content, and generate a *single, final query* for the IdeaAgent.\n\n"
    
    "**JSON List Analysis Process:**\n"
    "1. Carefully examine both lists to identify their purpose and content\n"
    "2. The lists could contain any of the following:\n"
    "   - Ideas/cards with titles, descriptions, budgets, and times\n"
    "   - User queries or modification requests\n"
    "   - Any combination of structured data relevant to event planning\n"
    "3. There's no fixed order - either list could contain the main ideas or the modification requests\n\n"
    
    "**Output Requirements:**\n"
    "1. Generate ONE FINAL query that intelligently combines elements from both lists\n"
    "2. Your query must be specific, actionable, and creative\n"
    "3. Begin your response with 'FINAL QUERY:' to signal completion\n"
    "4. After the 'FINAL QUERY:' prefix, provide ONLY the query text - no explanations\n\n"
    
    "**Important Rules:**\n"
    "1. Avoid redundancy and repetition in your query\n"
    "2. If one list contains modification requests (e.g., 'increase budget', 'family-friendly'), apply these to the content ideas\n"
    "3. If both lists contain ideas, extract complementary elements and combine them meaningfully\n"
    "4. Consider the unique ID of each item to differentiate between similar-looking entries\n"
    "5. Your output should be a single, focused query that will guide the IdeaAgent to generate new ideas\n\n"
    
    "Remember, your response must start with 'FINAL QUERY:' followed immediately by your creative, combined query."
)
# IdeaAgent Prompt (From IdeaAgent.py, slightly modified)
idea_agent_prompt = (

    "You will receive:\n"
    "- A query text that tells you what to do;\n"
    "- A payment history, which you must take into consideration when performing your tasks;\n"
    "- Any existing activities that might need to be updated;\n"
    "- An action type ('idea' or 'plan') which determines your exact task.\n\n"

    "If action is 'idea': \n"
    "Pretext: The user wants to plan and improve event activities, and you are their assistant.\n"
    "An event may contain multiple activities that has a title, a description and a budget.\n"
    "For a planned activity, you will be asked to update the activity creatively based on some given modifications.\n\n"

    "-> Your query text will specify what kind of activity to generate or how to modify an existing activity\n"
    "-> You must take into consideration the payment histories when making or updating activities\n"
    "-> You will receive one activity to be updated, you must creatively generate 3 differentd updated activities.\n"
    "-> The generated activities must be specific, realistic for the planned event, with consideration to the user's past transactions.\n"

    "Return the result as a JSON array, where each object has:\n"
    "- idea_id: a number starting from 1\n"
    "- title: short and clear\n"
    "- description: plain language explanation\n"
    "- budget: a realistic cost estimate (number only)\n"
    "- time: approximate duration (e.g., 'Weekend', 'Day', 'Evening')\n\n"
    
    "Example output format (same for both action types, just different quantity):\n"
    "[\n"
    "  {\n"
    "    \"idea_id\": 1,\n"
    "    \"title\": \"Pizza Brainstorm Night\",\n"
    "    \"description\": \"Teams share pizza and talk project ideas after dinner.\",\n"
    "    \"budget\": 180,\n"
    "    \"time\": \"Evening\"\n"
    "  },\n"
    "  {\n"
    "    \"idea_id\": 2,\n"
    "    \"title\": \"Weekend Team Building Retreat\",\n"
    "    \"description\": \"A comprehensive weekend retreat focused on team building and strategic planning.\",\n"
    "    \"budget\": 3500,\n"
    "    \"time\": \"Weekend\"\n"
    "  }\n"
    "  {..."
    "  }"
    "]\n\n\n"

    "If action is 'plan': \n"
    "Pretext: You are a helpful assistant helping users build a custom event plan from a list of activities.\n"
    "Each activity has an idea_id, a title, a budget, and a description.\n"

    "-> Your query text will specify an event which you have to plan its activities for."
    "-> You must take into consideration the payment histories when making or generating activities\n"
    "-> The generated activities must be specific, realistic for the planned event, with consideration to the user's past transactions.\n"
    "-> You must generate the activities considering a reaonsable chrnological order, that would be the best use of the user's time."

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
    "  },\n"
    "  {..."
    "  }"
    "]"
)

# Supervisor Prompt (Modified to include the IdeaAgent)
members = ["CombinerAgent", "IdeaAgent"]
options = members + ["FINISH"]

class Router(TypedDict):
    next: Literal[*options]
    reasoning: str
    rewritten_query: Optional[str]
    final_ideas: Optional[Union[Dict[str, Any], List[Dict[str, Any]]]]
supervisor_system_prompt = (
    "You are a supervisor in a system that helps users plan events and activities by manipulating 'cards'. "
    f"Your job is to route requests between agents: {', '.join(members)} and manage the final response. "
    "Based on the user's message, conversation history, and current state, you decide:\n"
    "1. Which agent to route to next (or FINISH)\n"
    "2. What specific instruction (rewritten_query) to give that agent\n"
    "3. Reasoning for your decision\n"
    "4. Which idea(s) to finalize based on the 'action' state (populating 'final_ideas')\n\n" # Added point 4

    "**Card Types:**\n"
    "- **CustomCard:** Contains a user-defined query (`user_query`).\n"
    "- **IdeaCard:** Contains structured fields: `title`, `description`, `budget`, `time`.\n\n"

    "**Agent Capabilities:**\n"
    "- **CombinerAgent:** Takes two cards and creates a new query by intelligently combining them. "
    "This agent also determines the 'action' type ('plan' or 'idea') based on the combination.\n"
    "- **IdeaAgent:** Generates creative event/activity ideas based on a query. "
    "This agent populates the 'current_ideas' list with new ideas.\n\n"

    "**Special Workflow for 'Combine' Operations:**\n"
    "When processing a combine operation, follow this sequence:\n"
    "1. Route to **CombinerAgent** with the raw combine request.\n"
    "2. When CombinerAgent responds, route to **IdeaAgent** with the output from CombinerAgent.\n"
    "3. When IdeaAgent completes, examine the 'action' state value:\n"
    "   - If action is 'idea': Select ONLY the SINGLE BEST IDEA from the 'current_ideas' list based on relevance to the original query. Populate the `final_ideas` field with this single idea dictionary.\n"
    "     Format your response message as a summary of just that one selected idea.\n"
    "   - If action is 'plan': Select ALL ideas from the `current_ideas` list. Populate the `final_ideas` field with a LIST containing all these idea dictionaries.\n"
    "     Format your response message as a summary or list of these plans.\n\n" # Clarified plan case


    "**Response Format:**\n"
    "Respond with a JSON object matching the Router structure. 'final_ideas' should contain the selected idea object (for action: idea) or a list of idea objects (for action: plan) if applicable, otherwise null.\n"
    "```json\n"
    "{\n"
    '  "next": "<CombinerAgent|IdeaAgent|FINISH>",\n'
    '  "reasoning": "<Explanation>",\n'
    '  "rewritten_query": "<Instruction for the next agent, or null if FINISH>",\n'
    '  "final_ideas": <Single idea object OR List of idea objects OR null>\n' # Clarified example
    "}\n"
    "```"
)
def supervisor_node(state: AgentState) -> Command:
    """Routes the request based on combine flow state or LLM decision."""
    print("\n--- SUPERVISOR ---")
    # Ensure messages is always a list, even if empty initially
    messages = state.get('messages', [])
    combine_flow_stage = state.get('combine_flow_stage')
    action = state.get('action')
    current_ideas = state.get('current_ideas', [])
    last_message = messages[-1] if messages else None

    print(f"Combine Flow Stage: {combine_flow_stage}")
    print(f"Action: {action}")
    print(f"Current Ideas Count: {len(current_ideas)}")
    if last_message:
        print("Last Message:", last_message.pretty_repr() if hasattr(last_message, 'pretty_repr') else str(last_message))
    else:
        print("Last Message: None")

    # --- Combine Workflow Logic ---

    # 1. Final stage: Process IdeaAgent output
    if combine_flow_stage == "idea_complete" and current_ideas:
        print(f"Supervisor: Processing final stage with action '{action}'")

        response_text = ""
        final_content_payload = None # Will hold the Python object (dict or list) before JSON conversion

        if action == "idea":
            print("Supervisor: Processing idea action - selecting best idea for JSON output")
            # Simple heuristic: select the first idea generated.
            if current_ideas:
                # Assuming ideas are dicts as generated by IdeaAgent
                selected_idea = current_ideas[0]
                # Ensure it's a dictionary
                if isinstance(selected_idea, dict):
                    final_content_payload = selected_idea # Assign the dictionary directly
                    print(f"Supervisor: Selected idea for JSON output: {selected_idea.get('title', 'N/A')}")
                else:
                    print("Supervisor Warning: Selected idea is not a dictionary.")
                    final_content_payload = {"error": "Selected idea data is invalid (not a dictionary)"}
            else:
                print("Supervisor: No ideas found to select for 'idea' action.")
                # Return an empty JSON object or an error indicator
                final_content_payload = {"message": "No ideas generated"}

        elif action == "plan":
            print("Supervisor: Processing plan action - formatting all ideas as JSON list")
            # Use the list of idea dictionaries directly
            # Sorting is optional but can be kept
            # Ensure current_ideas is actually a list before sorting/assigning
            if isinstance(current_ideas, list):
                # Filter out non-dict items just in case
                valid_ideas = [idea for idea in current_ideas if isinstance(idea, dict)]
                # Sort valid ideas
                sorted_ideas = sorted(valid_ideas, key=lambda x: x.get('idea_id', 999))
                final_content_payload = sorted_ideas # Assign the list of dictionaries
                print(f"Supervisor: Assigned {len(sorted_ideas)} ideas as JSON list.")
            else:
                 print("Supervisor Warning: 'current_ideas' for plan action is not a list.")
                 final_content_payload = {"error": "Plan ideas data is invalid (not a list)"}

        else:
            # Fallback for unknown action type - create error dictionary
            print(f"Supervisor Warning: Unhandled action type '{action}' during final processing.")
            final_content_payload = {"error": "Unknown action type during final processing", "action_received": action}

        # Convert the Python payload (dict or list) to a JSON string
        final_content_json_str = ""
        try:
            # Use indent for pretty printing, makes reading the AIMessage content easier
            final_content_json_str = json.dumps(final_content_payload, indent=2)
        except TypeError as e:
            print(f"Supervisor Error: Failed to serialize payload to JSON: {e}")
            # Fallback to a simple error JSON string
            final_content_json_str = json.dumps({"error": "Failed to serialize final content", "details": str(e)}, indent=2)

        # Create the final message with JSON string content
        final_message = AIMessage(content=final_content_json_str)

        # Prepare the final state update, clearing relevant fields for workflow end
        # Ensure you append the new final_message correctly to the history
        # Decide if you want to keep the original 'messages' history or just return the final one
        # Appending seems standard:
        final_update = {
            "messages": state['messages'] + [final_message], # Append the final JSON message
            "combine_flow_stage": None, # Reset flow stage
            "rewritten_query_for_next_agent": None,
            "action": None, # Clear action state
            "current_ideas": [], # Clear generated ideas list
            "final_ideas": None, # Clear the LLM selected ideas field too if using it
            "waiting_for_response_from": None # Ensure no longer waiting
        }

        # Clear state and finish by routing to END
        print("Supervisor: Final JSON message prepared. Routing to END.")
        return Command(
            goto=END,
            update=final_update
        )

    # 2. Start Combine Flow
    # Check if the last message is the specific initial prompt for combine
    is_combine_start_command = isinstance(last_message, HumanMessage) and last_message.content.startswith("Combine the following two JSON lists:")

    if is_combine_start_command and not combine_flow_stage:
        print("Supervisor: Starting combine flow -> CombinerAgent")
        return Command(
            goto="CombinerAgent",
            update={
                "combine_flow_stage": "combiner_started",
                "rewritten_query_for_next_agent": last_message.content, # Pass the structured prompt
                "current_ideas": [], # Ensure ideas are cleared at the start
                # 'action' should already be set in the initial_state from run_combine_workflow
            }
        )

    # 3. After CombinerAgent completes -> Route to IdeaAgent
    # Heuristic check: Does the last message look like output from CombinerAgent?
    is_combiner_output = isinstance(last_message, AIMessage) and last_message.content.strip().startswith("FINAL QUERY:")

    # Condition: Route to IdeaAgent if the stage is 'combiner_complete' (ideal)
    # OR if the message looks like combiner output AND we haven't already started the idea stage (fallback/robustness)
    if combine_flow_stage == "combiner_complete" or (is_combiner_output and combine_flow_stage != "idea_started"):
        if isinstance(last_message, AIMessage): # Ensure it's an AI message
            combiner_output_content = last_message.content.strip()
            print(f"Supervisor: Detected output from CombinerAgent (Stage: {combine_flow_stage}, Heuristic: {is_combiner_output}). Routing to IdeaAgent.")

            # Extract the actual query part after "FINAL QUERY:"
            final_query_match = re.search(r"FINAL QUERY:\s*(.*)", combiner_output_content, re.DOTALL)
            if final_query_match:
                actual_query_for_idea_agent = final_query_match.group(1).strip()
                print(f"Supervisor: Extracted query for IdeaAgent: '{actual_query_for_idea_agent[:100]}...'")
            else:
                print("Supervisor Warning: Combiner output format unexpected (missing 'FINAL QUERY:'). Using full content as query.")
                actual_query_for_idea_agent = combiner_output_content # Fallback

            # Prepare query context for IdeaAgent (transactions + action type)
            tx_summary = ""
            try:
                transactions = load_transactions(TRANSACTIONS_FILE)
                if transactions:
                    tx_summary = "\n".join(
                        f"{tx['type'].capitalize()} - ${tx['amount']} - {tx['description']}"
                        for tx in transactions
                    )
                    tx_summary = f"\n\nContext: Past Transactions:\n{tx_summary}"
                else:
                    tx_summary = "\n\nContext: No transaction data available."
            except Exception as e:
                print(f"Warning: Could not load transactions for IdeaAgent query: {e}")
                tx_summary = f"\n\nContext: Error loading transaction data: {e}"

            # Construct the full prompt for IdeaAgent including action type
            idea_query_full = (
                f"Action Type Hint: {action}\n\n" # Pass the determined action type
                f"User Query: {actual_query_for_idea_agent}\n"
                f"{tx_summary}"
            )
            print(f"Supervisor: Full input for IdeaAgent:\n{idea_query_full}")


            return Command(
                goto="IdeaAgent",
                update={
                    "combine_flow_stage": "idea_started", # Explicitly set next stage
                    "rewritten_query_for_next_agent": idea_query_full, # Pass combined query + context
                    # Keep 'action' and 'current_ideas' as they are
                }
            )
        else:
             # This case should be rare if is_combiner_output was true
             print(f"Supervisor Warning: Expected AIMessage after combiner based on content check, but got {type(last_message)}. Falling back.")
             # Fall through to LLM router might be the safest fallback


    # --- Fallback to LLM Router ---
    # This block is reached if none of the specific workflow conditions above are met.
    print("Supervisor: No specific workflow step matched, falling back to LLM router.")
    # Add a safety check: If the message looks like combiner output, DON'T use LLM router, force END or error.
    if is_combiner_output:
         print("Supervisor ERROR: Message looks like Combiner output, but routing conditions failed. Preventing loop. FINISHING.")
         # This indicates a logic error in the state or conditions above.
         return Command(goto=END, update={"messages": [AIMessage(content="Error: Unexpected state after CombinerAgent. Workflow halted.")]})


    structured_llm = llm.with_structured_output(Router)
    # Update supervisor prompt if necessary to guide LLM better about the flow
    # For now, assume supervisor_system_prompt is adequate but be mindful it might need adjustment
    supervisor_prompt_messages = [{"role": "system", "content": supervisor_system_prompt}]
    # Append conversation history for the LLM
    for msg in messages:
        role = "user" if isinstance(msg, HumanMessage) else "assistant"
        supervisor_prompt_messages.append({"role": role, "content": msg.content})

    try:
        print("Supervisor: Asking LLM for routing decision...")
        response: Router = structured_llm.invoke(supervisor_prompt_messages) # Type hint for clarity
        next_route = response.get('next')
        reasoning = response.get('reasoning', "No reasoning provided.")
        rewritten_query = response.get('rewritten_query')

        # --- LLM Routing Decision Logging ---
        print(f"Supervisor Decision (LLM): Route to '{next_route}'")
        print(f"Supervisor Reasoning (LLM): {reasoning}")
        if rewritten_query:
            print(f"Supervisor Rewritten Query for {next_route}: {rewritten_query}")
        # --- End Logging ---

        # Safety check: Prevent LLM from looping back to CombinerAgent after it just ran.
        if next_route == 'CombinerAgent' and is_combiner_output:
            print("Supervisor ERROR: LLM attempted to loop back to CombinerAgent immediately. Overriding to FINISH.")
            return Command(goto=END, update={"messages": [AIMessage(content="Error: Detected LLM routing loop attempt after CombinerAgent.")]})

        update_state = {"rewritten_query_for_next_agent": rewritten_query}
        goto = END if next_route == "FINISH" else next_route

        # If LLM decides to FINISH, reset combine-specific state
        if goto == END:
             print("Supervisor: LLM decided to FINISH. Resetting combine flow state.")
             update_state.update({
                 "combine_flow_stage": None,
                 "action": None,
                 "current_ideas": []
             })

        return Command(goto=goto, update=update_state)

    except Exception as e:
        print(f"Error during supervisor LLM call: {e}")
        # Default behavior on error: Finish with error message
        error_msg = f"Error during supervisor routing: {e}"
        return Command(goto=END, update={
            "messages": messages + [AIMessage(content=error_msg)], # Append error to history
            "rewritten_query_for_next_agent": None,
            "combine_flow_stage": None, # Reset state on error
            "action": None,
            "current_ideas": []
        })

def create_agent_node(agent, agent_name: str):
    """Creates a node function for a given agent."""
    def agent_node(state: AgentState) -> Command:
        print(f"\n--- Running {agent_name} ---")
        rewritten_query = state.get('rewritten_query_for_next_agent')
        current_messages = state.get('messages', [])
        input_messages = list(current_messages)  # Copy messages

        if rewritten_query:
            print(f"Injecting rewritten query: '{rewritten_query}'")
            input_messages.append(HumanMessage(content=rewritten_query))

        try:
            # Invoke the agent with potentially modified messages
            result = agent.invoke({"messages": input_messages})
            agent_response = result["messages"][-1] if result["messages"] else AIMessage(content="<No response generated>")

            # Prepare base state update: add response, clear query
            update_state = {
                "messages": [agent_response],
                "rewritten_query_for_next_agent": None  # Clear the query after use
            }

            # Update combine flow stage if applicable
            current_combine_stage = state.get('combine_flow_stage')
            if agent_name == "CombinerAgent" and current_combine_stage == "combiner_started":
                update_state["combine_flow_stage"] = "combiner_complete"
                print(f"Agent Node ({agent_name}): Updated combine stage to 'combiner_complete'")
                
                # # Set the action type based on the combination
                # # For now, always set to "idea" as per requirements
                # # Later can be enhanced to detect "plan" actions
                # update_state["action"] = "idea"
                # print(f"Agent Node ({agent_name}): Set action to 'idea'")
                
                # In the future, parse the response to determine if it's a plan or idea
                # Example logic (placeholder):
                # if "plan" in agent_response.content.lower():
                #     update_state["action"] = "plan"
                # else:
                #     update_state["action"] = "idea"
                
            if agent_name == "IdeaAgent" and current_combine_stage == "idea_started":
                update_state["combine_flow_stage"] = "idea_complete"
                print(f"Agent Node ({agent_name}): Updated combine stage to 'idea_complete'")

                # Get the current action type
                current_action = state.get('action', 'idea')  # Default to 'idea' if not specified
                print(f"Agent Node ({agent_name}): Processing with action type '{current_action}'")
                
                # Process IdeaAgent output
                try:
                    if isinstance(agent_response, AIMessage):
                        content = agent_response.content
                        
                        # Extract JSON array from response
                        json_match = re.search(r'(\[.*\])', content, re.DOTALL)
                        if json_match:
                            ideas_json_str = json_match.group(1)
                            try:
                                ideas = json.loads(ideas_json_str)
                                if isinstance(ideas, list):
                                    # Get existing ideas and append new ones
                                    current_ideas = state.get('current_ideas', [])
                                    current_ideas.extend(ideas)
                                    update_state["current_ideas"] = current_ideas
                                    
                                    if current_action == "idea":
                                        print(f"Agent Node ({agent_name}): Added {len(ideas)} ideas to current_ideas (now {len(current_ideas)} total, target: 3)")
                                    else:  # plan
                                        print(f"Agent Node ({agent_name}): Added {len(ideas)} ideas to current_ideas (now {len(current_ideas)} total, target: 6-10)")
                                    
                                    # Print the ideas in JSON list format
                                    print(f"New ideas in JSON list format:")
                                    print(json.dumps(ideas, indent=2))
                                    
                                    # Save all ideas to timeline
                                    all_cards = load_timeline()
                                    new_card_count = 0
                                    for idea in ideas:
                                        if isinstance(idea, dict):
                                            idea_title = idea.get('title', 'Untitled Idea')
                                            idea_desc = idea.get('description', 'No description')
                                            idea_budget = str(idea.get('budget', 'Medium'))
                                            idea_time = idea.get('time', 'Any time')
                                            add_idea_card(all_cards, idea_title, idea_desc, idea_budget, idea_time)
                                            new_card_count += 1
                                        else:
                                            print(f"Warning: Invalid item in IdeaAgent JSON response: {idea}")

                                    if new_card_count > 0:
                                        save_timeline(all_cards)
                                        print(f"Agent Node ({agent_name}): Saved {new_card_count} new IdeaCards to timeline.")
                                else:
                                    print(f"Warning: IdeaAgent JSON response was not a list: {ideas_json_str}")

                            except json.JSONDecodeError as json_e:
                                print(f"Error decoding JSON from IdeaAgent response: {json_e}")
                                print(f"Content received: {ideas_json_str}")
                        else:
                            print(f"Warning: No JSON array found in IdeaAgent response: {content}")
                except Exception as e:
                    print(f"Error processing IdeaAgent output in agent node: {e}")

            # Always return to supervisor after agent execution
            return Command(update=update_state, goto="supervisor")

        except Exception as e:
            print(f"Error invoking {agent_name}: {e}")
            error_message = AIMessage(content=f"Error encountered in {agent_name}: {str(e)}")
            # On error, clear state and return to supervisor
            return Command(
                update={
                    "messages": [error_message],
                    "rewritten_query_for_next_agent": None,
                    "combine_flow_stage": None,  # Reset flow on error
                    "action": None,  # Reset action on error
                    "current_ideas": []  # Reset ideas on error
                },
                goto="supervisor"
            )

    return agent_node

# --- Create Agents ---
combiner_agent = create_react_agent(llm, tools=[], prompt=combiner_agent_prompt)
idea_agent = create_react_agent(llm, tools=[], prompt=idea_agent_prompt)

# --- Create Node Functions ---
combiner_agent_node = create_agent_node(combiner_agent, "CombinerAgent")
idea_agent_node = create_agent_node(idea_agent, "IdeaAgent")

# --- Construct Graph ---
builder = StateGraph(AgentState)
builder.add_node("supervisor", supervisor_node)
builder.add_node("CombinerAgent", combiner_agent_node)
builder.add_node("IdeaAgent", idea_agent_node)

# Edges: Start -> Supervisor, Agents -> Supervisor, Supervisor -> Agents/END
builder.add_edge(START, "supervisor")
builder.add_edge("CombinerAgent", "supervisor")
builder.add_edge("IdeaAgent", "supervisor")

# Conditional edges from supervisor are handled by the Command return value's 'goto'
# builder.add_edge("supervisor", "CombinerAgent") # Not needed like this
# builder.add_edge("supervisor", "IdeaAgent") # Not needed like this

# Compile the graph
graph = builder.compile()
print("\nGraph compiled successfully.")

# --- Helper Functions for Running Commands ---
# ... (run_combine_workflow, run_idea_query remain the same) ...
def run_combine_workflow(
    json_list1: List[Dict[str, Any]],
    json_list2: List[Dict[str, Any]]
) -> Optional[List[Dict[str, Any]]]:
    """Runs the Supervisor -> Combiner -> Idea workflow for two JSON lists.
    Sets action type based on list lengths.
    """
    print(f"\n--- Starting Combine Workflow for two JSON lists ---")
    # print(f"Original IdeaCard ID to potentially replace: {original_idea_card_id}") # Removed

    # Determine action type based on list lengths (existing logic)
    len1 = len(json_list1)
    len2 = len(json_list2)
    action_type = "idea" # Default to idea
    if len1 > len2:
        action_type = "plan"
        print(f"List 1 has more elements ({len1} > {len2}): Setting action to 'plan'")
    elif len2 > len1:
        action_type = "plan"
        print(f"List 2 has more elements ({len2} > {len1}): Setting action to 'plan'")
    else:
        action_type = "idea"
        print(f"Both lists have equal elements ({len1} = {len2}): Setting action to 'idea'")

    # Format JSON lists for the initial message (existing logic)
    list1_str = json.dumps(json_list1, indent=2)
    list2_str = json.dumps(json_list2, indent=2)
    initial_message_content = f"Combine the following two JSON lists:\n\nList 1:\n{list1_str}\n\nList 2:\n{list2_str}"
    print(f"Initial message for JSON combination: {initial_message_content}")

    # Initialize state WITHOUT the original ID
    initial_state = {
        "messages": [HumanMessage(content=initial_message_content)],
        "combine_flow_stage": None,
        "action": action_type,
        # Removed: "original_idea_card_id_to_replace": original_idea_card_id
    }

    # Stream the workflow execution (existing logic)
    final_state = None
    try:
        events = graph.stream(
            initial_state,
            stream_mode="values",
            config={"recursion_limit": 15}
        )
        print("Workflow steps:")
        for step, value in enumerate(events):
            print(f"Step {step+1} completed. Current state keys: {list(value.keys())}")
            print(f"  Action type: {value.get('action')}")
            print(f"  Combine Stage: {value.get('combine_flow_stage')}")
            # print(f"  Original ID Tracked: {value.get('original_idea_card_id_to_replace')}") # Removed
            final_state = value

    except Exception as e:
        print(f"\nError during graph execution: {e}")
        return f"Error during graph execution: {e}"

    # --- Post-Workflow Processing ---
    final_result_message = "Workflow finished without a final message."
    if final_state and final_state.get('messages'):
        last_message = final_state['messages'][-1]
        print("\n--- Combine Workflow Finished ---")
        if isinstance(last_message, AIMessage):
            final_result_message = last_message.content
        else:
            final_result_message = f"Workflow ended. Last message: {last_message.pretty_repr() if hasattr(last_message, 'pretty_repr') else last_message}"
    else:
        print("\n--- Combine Workflow Finished (No final state message found) ---")


    # ** The post-workflow removal block that was here is REMOVED **


    return final_result_message



    
def combine_json_with_timeline(custom_card_id: str) -> Optional[str]:
    """Runs the Supervisor -> Combiner -> Idea workflow using the entire in_timeline list 
    and a single CustomCard.
    """
    print(f"\n--- Starting Combine Workflow with timeline and CustomCard {custom_card_id} ---")
    
    # Load all cards
    all_cards = load_timeline()
    
    # Get the specified CustomCard
    custom_card = get_card(all_cards, custom_card_id)
    if not custom_card or custom_card.get("card_type") != "CustomCard":
        error_msg = f"Error: Card {custom_card_id} is not found or not a CustomCard."
        print(error_msg)
        return error_msg
    
    # Extract all IdeaCards from in_timeline
    idea_cards = [card for card in all_cards.values() if card.get("card_type") == "IdeaCard"]
    if not idea_cards:
        error_msg = "Error: No IdeaCards found in the timeline."
        print(error_msg)
        return error_msg
    
    # Convert IdeaCards to JSON list format
    idea_list = []
    for i, card in enumerate(idea_cards):
        idea_list.append({
            "id": card.get("id", f"idea-{i+1}"),
            "title": card.get("title", "Untitled"),
            "description": card.get("description", "No description"),
            "budget": card.get("budget", "Medium"),
            "time": card.get("time", "Any time")
        })
    
    # Convert CustomCard to JSON list format (as a single item list)
    custom_list = [{
        "id": custom_card.get("id", "custom-1"),
        "title": "User Query",
        "description": custom_card.get("user_query", "No query"),
        "budget": "N/A",
        "time": "N/A"
    }]
    
    # Since custom_list always has length 1, action will always be "plan"
    action_type = "plan"
    print(f"Using action type: '{action_type}' (custom_list length is always 1)")
    
    # Format JSON lists for the initial message
    idea_list_str = json.dumps(idea_list, indent=2)
    custom_list_str = json.dumps(custom_list, indent=2)
    
    # Create a specific prompt format for JSON lists
    initial_message_content = f"Combine the following two JSON lists:\n\nList 1:\n{idea_list_str}\n\nList 2:\n{custom_list_str}"

    print(f"Initial message for JSON combination: {initial_message_content}")
    
    # Initialize state with action type
    initial_state = {
        "messages": [HumanMessage(content=initial_message_content)], 
        "combine_flow_stage": None,
        "action": action_type
    }

    # Stream the workflow execution
    final_state = None
    try:
        events = graph.stream(
            initial_state,
            stream_mode="values",
            config={"recursion_limit": 15}
        )
        print("Workflow steps:")
        for step, value in enumerate(events):
            print(f"Step {step+1} completed. Current state keys: {value.keys()}")
            final_state = value

    except Exception as e:
        print(f"\nError during graph execution: {e}")
        return f"Error during graph execution: {e}"

    # Extract and return the final response
    if final_state and final_state.get('messages'):
        last_message = final_state['messages'][-1]
        print("\n--- Combine JSON Workflow Finished ---")
        if isinstance(last_message, AIMessage):
            return last_message.content
        else:
            return f"Workflow ended. Last message: {last_message.pretty_repr() if hasattr(last_message, 'pretty_repr') else last_message}"
    else:
        print("\n--- Combine JSON Workflow Finished (No final state message found) ---")
        return "Workflow finished without a final message."
def run_idea_query(query: str) -> Optional[str]:
    """Runs a direct query to the IdeaAgent through the supervisor."""
    print(f"\n--- Starting Idea Query: '{query}' ---")

    # Ensure initial state has combine_flow_stage as None
    initial_state = {"messages": [HumanMessage(content=query)], "combine_flow_stage": None}

    # Stream the workflow execution
    final_state = None
    try:
        events = graph.stream(
            initial_state,
            stream_mode="values",
            config={"recursion_limit": 10}
        )
        print("Workflow steps:")
        for step, value in enumerate(events):
            print(f"Step {step+1} completed")
            final_state = value

    except Exception as e:
        print(f"\nError during graph execution: {e}")
        return f"Error during graph execution: {e}"

    # Extract and return the final response
    if final_state and final_state.get('messages'):
        last_message = final_state['messages'][-1]
        print("\n--- Idea Query Finished ---")
        if isinstance(last_message, AIMessage):
            return last_message.content
        else:
            return f"Workflow ended. Last message: {last_message.pretty_repr() if hasattr(last_message, 'pretty_repr') else last_message}"
    else:
        print("\n--- Idea Query Finished (No final state message found) ---")
        return "Workflow finished without a final message."


# --- Main CLI Application Loop ---
# ... (print_help, main remain the same) ...
def print_help():
    print("\nAvailable Commands:")
    print("  create <query>           - Create a new CustomCard (adds to 'out_timeline').")
    print("  combine <id1> <id2>      - Combine two cards by ID.")
    print("  idea <query>             - Generate ideas directly with a query.")
    print("  list                     - Show all cards grouped by timeline status.")
    print("  show <id>                - Show details of a specific card.")
    print("  help                     - Show this help message.")
    print("  exit                     - Quit the application.")

def main():
    print("\n--- Timeline Card System CLI ---")
    # Load timeline
    timeline_cards = load_timeline()

    # Print timeline
    print_timeline(timeline_cards)

    while True:
        try:
            command_line = input("\nEnter command (or 'help'/'exit'): ").strip()
            if not command_line:
                continue

            parts = command_line.split(maxsplit=1)
            command = parts[0].lower()
            args_str = parts[1] if len(parts) > 1 else ""

            if command == "exit":
                break
            elif command == "help":
                print_help()
            elif command == "create":
                if not args_str:
                    print("Error: 'create' command needs a query for the CustomCard.")
                    continue
                # Add to the internal dict
                add_custom_card(timeline_cards, args_str)
                # Save using the new function (which handles splitting to lists)
                save_timeline(timeline_cards)
                # Print using the new function
                print_timeline(timeline_cards)
            elif command == "list":
                # Print using the new function
                print_timeline(timeline_cards)
            elif command == "show":
                if not args_str:
                    print("Error: 'show' command needs a card ID.")
                    continue
                card_id_to_show = args_str.strip()
                # Get from the internal dict
                card = get_card(timeline_cards, card_id_to_show)
                if card:
                    print("\n--- Card Details ---")
                    # Display logic remains similar, checks type
                    card_type = card.get("card_type", "Unknown")
                    timeline_status = "'in_timeline'" if card_type == "IdeaCard" else "'out_timeline'"
                    print(f"  ID: {card['id']} ({card_type} - {timeline_status})") # Show status
                    if card_type == "CustomCard":
                        print(f"    Query: {card.get('user_query', 'N/A')}")
                    elif card_type == "IdeaCard":
                        print(f"    Title: {card.get('title', 'N/A')}")
                        print(f"    Desc: {card.get('description', 'N/A')}")
                        print(f"    Budget: {card.get('budget', 'N/A')}")
                        print(f"    Time: {card.get('time', 'N/A')}")
                    else:
                        print(f"    Data: {card}")
                    print(f"    Created: {card.get('created_at', 'N/A')}")
                    print("--------------------")
                else:
                    print(f"Error: Card with ID '{card_id_to_show}' not found.")
            elif command == "combine":
                combine_args = args_str.split()
                if len(combine_args) != 2:
                    print("Error: 'combine' command needs exactly two card IDs.")
                    continue
                id1, id2 = combine_args[0].strip(), combine_args[1].strip()

                # --- Card Retrieval (existing logic) ---
                timeline_cards = load_timeline() # Load fresh before getting cards
                card1 = get_card(timeline_cards, id1)
                card2 = get_card(timeline_cards, id2)

                if not card1:
                    print(f"Error: Card with ID '{id1}' not found.")
                    continue
                if not card2:
                    print(f"Error: Card with ID '{id2}' not found.")
                    continue

                # --- JSON List Conversion (existing logic) ---
                json_list1 = [{ # Format card1
                    "id": card1.get("id", ""),
                    "title": card1.get("title", card1.get("user_query", "Untitled")),
                    "description": card1.get("description", card1.get("user_query", "No description")),
                    "budget": card1.get("budget", "N/A"),
                    "time": card1.get("time", "N/A")
                }]
                json_list2 = [{ # Format card2
                    "id": card2.get("id", ""),
                    "title": card2.get("title", card2.get("user_query", "Untitled")),
                    "description": card2.get("description", card2.get("user_query", "No description")),
                    "budget": card2.get("budget", "N/A"),
                    "time": card2.get("time", "N/A")
                }]

                # --- Run Workflow (Reverted: No extra ID passed) ---
                print(f"Running combine workflow for '{id1}' and '{id2}'...")
                combination_result = run_combine_workflow(json_list1, json_list2)

                print("\n--- Combination Result ---")
                print(combination_result if combination_result else "No result generated.")
                print("--------------------------")

                # --- NEW Deletion Logic ---
                # Check if workflow seems successful (returned a result, didn't start with "Error:")
                if combination_result and not str(combination_result).strip().startswith("Error:"):
                    print(f"\nWorkflow completed. Attempting to delete input cards: '{id1}', '{id2}' from timeline...")
                    try:
                        # Load the latest timeline data again before modifying
                        current_timeline_data = load_timeline()
                        # Use the helper function to delete cards by ID
                        deleted1 = delete_card_from_timeline(current_timeline_data, id1)
                        deleted2 = delete_card_from_timeline(current_timeline_data, id2)

                        if deleted1 or deleted2: # Save only if changes were made
                            save_timeline(current_timeline_data)
                            print("Timeline saved after deleting input cards.")
                        else:
                            print("Neither input card was found in the timeline; no deletion occurred.")
                    except Exception as e:
                        print(f"Error during post-combine card deletion: {e}")
                else:
                     print("\nWorkflow did not complete successfully or returned an error. Skipping input card deletion.")
                # --- End Deletion Logic ---

                # Refresh timeline view AFTER potential deletion
                print("\nRefreshing timeline view after combine operation...")
                timeline_cards = load_timeline() # Reload to see changes
                print_timeline(timeline_cards)
                # --- End ID determination ---


                # Convert the individual cards to JSON lists format (existing logic)
                json_list1 = [{
                    "id": card1.get("id", ""),
                    "title": card1.get("title", card1.get("user_query", "Untitled")),
                    "description": card1.get("description", card1.get("user_query", "No description")),
                    "budget": card1.get("budget", "N/A"),
                    "time": card1.get("time", "N/A")
                }]
                json_list2 = [{
                    "id": card2.get("id", ""),
                    "title": card2.get("title", card2.get("user_query", "Untitled")),
                    "description": card2.get("description", card2.get("user_query", "No description")),
                    "budget": card2.get("budget", "N/A"),
                    "time": card2.get("time", "N/A")
                }]

                print(f"Converting cards to JSON lists before combining...")
                # Pass the identified original_idea_card_id to the workflow function
                combination_result = run_combine_workflow(json_list1, json_list2)

                print("\n--- Combination Result ---")
                print(combination_result if combination_result else "No result generated.")
                print("--------------------------")

                # Refresh timeline view AFTER the workflow (which might have modified it)
                print("\nRefreshing timeline view after combine operation...")
                timeline_cards = load_timeline() # Reload to see changes
                print_timeline(timeline_cards)


            elif command == "idea":
                if not args_str:
                    print("Error: 'idea' command needs a query.")
                    continue

                # Run the idea query
                idea_result = run_idea_query(args_str)

                print("\n--- Idea Generation Result ---")
                print(idea_result if idea_result else "No ideas generated.")
                print("--------------------------")

                # Refresh timeline after idea operation
                print("\nRefreshing timeline after idea operation...")
                timeline_cards = load_timeline()
                print_timeline(timeline_cards)
            
            elif command == "combine_json":
                if not args_str:
                    print("Error: 'combine_json' command needs the paths to two JSON list files.")
                    continue
                
                # Parse file paths from args
                file_paths = args_str.split()
                if len(file_paths) != 2:
                    print("Error: Need exactly two JSON file paths.")
                    continue
                
                # Load JSON lists from files
                try:
                    with open(file_paths[0], 'r') as f1:
                        json_list1 = json.load(f1)
                    with open(file_paths[1], 'r') as f2:
                        json_list2 = json.load(f2)
                        
                    # Validate they're actually lists
                    if not isinstance(json_list1, list) or not isinstance(json_list2, list):
                        print("Error: Both files must contain JSON lists.")
                        continue
                        
                    # Run the combine workflow for JSON lists
                    combination_result = run_combine_workflow(json_list1, json_list2)
                    
                    print("\n--- JSON List Combination Result ---")
                    print(combination_result if combination_result else "No result generated.")
                    print("--------------------------")
                except Exception as e:
                    print(f"Error processing JSON files: {e}")
                
            elif command == "combine_timeline":
                if not args_str:
                    print("Error: 'combine_timeline' command needs a CustomCard ID.")
                    continue

                custom_card_id = args_str.strip()

                # --- Run Workflow (existing logic) ---
                # Ensure the function `combine_json_with_timeline` exists and works as intended
                # Assuming it takes the custom_card_id and returns a result string or None/Error
                print(f"Running combine_timeline workflow with CustomCard '{custom_card_id}'...")
                combination_result = combine_json_with_timeline(custom_card_id) # Make sure this function exists and is called correctly

                print("\n--- Timeline + CustomCard Combination Result ---")
                print(combination_result if combination_result else "No result generated.")
                print("--------------------------")

                # --- NEW Deletion/Cleanup Logic ---
                if combination_result and not str(combination_result).strip().startswith("Error:"):
                    print(f"\nTimeline combine workflow completed. Clearing 'in_timeline' and deleting '{custom_card_id}'...")
                    try:
                        # --- Logic specific to 'plan' action result ---
                        # Assumes combination_result is a JSON string list of new IdeaCards

                        # 1. Parse the new ideas from the workflow result
                        new_ideas_list = json.loads(combination_result)
                        if not isinstance(new_ideas_list, list):
                            # Handle cases where the result might not be a list as expected
                            print(f"Warning: Workflow result was not a list. Result:\n{combination_result}")
                            raise ValueError("Workflow result is not a JSON list.")
                        print(f"Parsed {len(new_ideas_list)} new idea(s) from workflow result.")

                        # 2. Load the current timeline data (unified dict)
                        current_timeline_data = load_timeline()
                        print(f"Loaded {len(current_timeline_data)} cards from current timeline before update.")

                        # 3. Prepare the updated timeline dictionary - START FRESH
                        updated_timeline_data = {}

                        # Add the NEW ideas (they will form the new in_timeline)
                        for idea in new_ideas_list:
                            if isinstance(idea, dict) and "title" in idea and "description" in idea:
                                # Ensure necessary fields and generate ID if missing
                                idea['card_type'] = "IdeaCard" # Explicitly set type
                                if 'id' not in idea or not idea['id']:
                                    idea_id = f"card-idea-{uuid.uuid4().hex[:6]}"
                                    idea['id'] = idea_id
                                    print(f"Generated new ID for idea: {idea_id}")
                                else:
                                        idea_id = idea['id'] # Use existing ID if provided by LLM

                                if 'created_at' not in idea: # Add timestamp if missing
                                        idea['created_at'] = datetime.datetime.now(datetime.timezone.utc).isoformat()

                                updated_timeline_data[idea_id] = idea # Add to new dictionary
                            else:
                                print(f"Warning: Skipping invalid idea structure in result: {idea}")
                        print(f"Added {len(updated_timeline_data)} new IdeaCards to the updated timeline data.")

                        # Keep existing CustomCards (out_timeline), EXCLUDING the input one
                        num_kept_custom = 0
                        num_discarded_custom = 0
                        for card_id, card_data in current_timeline_data.items():
                            if card_data.get("card_type") == "CustomCard":
                                if card_id != custom_card_id:
                                    # Only add if it's NOT the input custom card
                                    updated_timeline_data[card_id] = card_data
                                    num_kept_custom += 1
                                else:
                                    num_discarded_custom +=1 # Count the discarded input card

                        print(f"Kept {num_kept_custom} existing CustomCard(s). Discarded input CustomCard '{custom_card_id}' (count: {num_discarded_custom}).")


                        # 4. Save the completely rebuilt timeline
                        print(f"Saving updated timeline with {len(updated_timeline_data)} total cards (New Ideas + Kept Custom)...")
                        save_timeline(updated_timeline_data) # save_timeline correctly handles dict -> lists
                        print("Timeline saved successfully, replacing the old plan.")

                    except json.JSONDecodeError:
                            print(f"Error: Workflow result could not be parsed as JSON. Result:\n{combination_result}")
                    except Exception as e:
                        print(f"Error during post-combine_timeline update (plan action): {e}")
                        import traceback # Optional: for more detailed errors
                        traceback.print_exc() # Optional: for more detailed errors
                        
                # Refresh timeline view AFTER potential deletion/cleanup
                print("\nRefreshing timeline view after combine_timeline operation...")
                timeline_cards = load_timeline() # Reload to see changes
                print_timeline(timeline_cards)



        except EOFError:
            print("\nExiting...")
            break
        except KeyboardInterrupt:
            print("\nExiting...")
            break
        except Exception as e:
            print(f"\nAn unexpected error occurred in the main loop: {e}")
            # import traceback
            # traceback.print_exc() # Uncomment for detailed traceback during debugging

    print("\nApplication finished.")

if __name__ == "__main__":
    main()