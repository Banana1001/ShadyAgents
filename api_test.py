import os
import datetime
import json
import uuid
import re
import logging
from typing import List, Dict, Any, Optional, Tuple, Union, Literal
from typing_extensions import TypedDict
from dotenv import load_dotenv

# --- FastAPI Imports ---
from fastapi import FastAPI, HTTPException, Path
from fastapi.middleware.cors import CORSMiddleware
# from pydantic import BaseModel # Keep if you need request bodies later

# --- Langchain/LangGraph Imports ---
from langchain_core.messages import HumanMessage, AIMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, START, END, MessagesState
from langgraph.prebuilt import create_react_agent
from langgraph.types import Command

# --- Configuration ---
TIMELINE_FILE = "timeline.json"
TRANSACTIONS_FILE = "transactions.json" # Ensure this file exists or handle its absence

# --- Logging Setup ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Environment Setup ---
load_dotenv()
openai_api_key = os.getenv('API_KEY_GPT')
if not openai_api_key:
    logger.warning("API_KEY_GPT not found in environment variables. LLM calls may fail.")
    # Consider raising an error or exiting if the key is essential
    # raise ValueError("API_KEY_GPT environment variable not set.")

# --- Set up LLM ---
# Add error handling in case the key is missing but execution proceeds
try:
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.7, api_key=openai_api_key)
except Exception as e:
    logger.error(f"Failed to initialize ChatOpenAI: {e}")
    # Depending on your app's needs, you might exit or disable LLM features
    llm = None # Set llm to None to indicate failure

# --- Data Structures ---
CardData = Dict[str, Any]

# --- Timeline/Card Management (Functions remain largely the same) ---

def delete_card_from_timeline(all_cards_dict: Dict[str, CardData], card_id: str) -> bool:
    """Deletes a card by ID from the dictionary. Modifies in place."""
    if card_id in all_cards_dict:
        del all_cards_dict[card_id]
        logger.info(f"Deleted card '{card_id}' from internal dictionary.")
        return True
    else:
        logger.warning(f"Card '{card_id}' not found for deletion.")
        return False

def load_timeline() -> Dict[str, CardData]:
    """Loads cards into a unified dictionary keyed by card ID."""
    all_cards: Dict[str, CardData] = {}
    if not os.path.exists(TIMELINE_FILE):
        logger.info(f"{TIMELINE_FILE} not found. Creating default file.")
        default_idea_card: CardData = {
            "id": "card-idea-default",
            "card_type": "IdeaCard",
            "title": "Weekend Trip Example",
            "description": "A sample idea card for a weekend getaway.",
            "budget": "Medium",
            "time": "Weekend",
            "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat()
        }
        initial_cards = {default_idea_card["id"]: default_idea_card}
        save_timeline(initial_cards) # Save will create the list structure
        return initial_cards

    try:
        with open(TIMELINE_FILE, 'r') as f:
            # Handle empty file case
            content = f.read()
            if not content:
                logger.warning(f"{TIMELINE_FILE} is empty. Returning empty dictionary.")
                return {}
            timeline_data = json.loads(content)

        if not isinstance(timeline_data, dict) or "in_timeline" not in timeline_data or "out_timeline" not in timeline_data:
             logger.warning(f"{TIMELINE_FILE} has unexpected structure. Returning empty dictionary.")
             # Optionally backup the old file here
             return {}

        for card in timeline_data.get("in_timeline", []):
            if isinstance(card, dict) and "id" in card:
                all_cards[card["id"]] = card
            else:
                logger.warning(f"Found invalid item in 'in_timeline': {card}")
        for card in timeline_data.get("out_timeline", []):
             if isinstance(card, dict) and "id" in card:
                 if card["id"] in all_cards:
                     logger.warning(f"Duplicate card ID '{card['id']}' found. Using entry from 'in_timeline'.")
                     continue
                 all_cards[card["id"]] = card
             else:
                 logger.warning(f"Found invalid item in 'out_timeline': {card}")
        logger.info(f"Loaded {len(all_cards)} cards from {TIMELINE_FILE}.")
        return all_cards

    except json.JSONDecodeError as e:
        logger.error(f"Error decoding JSON from {TIMELINE_FILE}: {e}. Returning empty card list.")
        return {}
    except IOError as e:
        logger.error(f"Error reading {TIMELINE_FILE}: {e}. Returning empty card list.")
        return {}
    except Exception as e:
        logger.error(f"Unexpected error loading {TIMELINE_FILE}: {e}. Returning empty card list.")
        return {}

def save_timeline(all_cards: Dict[str, CardData]):
    """Saves the unified card dictionary into the timeline.json file."""
    in_timeline_list: List[CardData] = []
    out_timeline_list: List[CardData] = []

    sorted_cards = sorted(all_cards.values(), key=lambda c: c.get("created_at", ""))

    for card in sorted_cards:
        card_type = card.get("card_type")
        if card_type == "IdeaCard":
            in_timeline_list.append(card)
        elif card_type == "CustomCard":
            out_timeline_list.append(card)
        else:
            logger.warning(f"Card '{card.get('id', 'N/A')}' has unknown type '{card_type}'. Placing in 'out_timeline'.")
            out_timeline_list.append(card) # Default to out_timeline

    timeline_data = {
        "in_timeline": in_timeline_list,
        "out_timeline": out_timeline_list
    }

    try:
        with open(TIMELINE_FILE, 'w') as f:
            json.dump(timeline_data, f, indent=2)
        logger.info(f"Timeline saved successfully to {TIMELINE_FILE} with {len(in_timeline_list)} in_timeline and {len(out_timeline_list)} out_timeline cards.")
    except IOError as e:
        logger.error(f"Error saving {TIMELINE_FILE}: {e}")
    except Exception as e:
        logger.error(f"Unexpected error saving {TIMELINE_FILE}: {e}")


def add_custom_card(all_cards: Dict[str, CardData], user_query: str) -> Tuple[str, CardData]:
    """Adds a new CustomCard to the internal dictionary. Modifies in place."""
    card_id = f"card-custom-{uuid.uuid4().hex[:6]}"
    new_card: CardData = {
        "id": card_id,
        "card_type": "CustomCard",
        "user_query": user_query.strip(),
        "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat()
    }
    all_cards[card_id] = new_card
    logger.info(f"Prepared CustomCard '{card_id}' for 'out_timeline'.")
    return card_id, new_card

# --- Corrected add_idea_card function ---
def add_idea_card(
    all_cards: Dict[str, CardData], # Use consistent type hint
    idea_data: Dict[str, Any]
    # target_list argument removed as save_timeline handles placement
) -> Tuple[str, Dict[str, CardData]]: # Return type hint matches input/output
    """
    Adds a new IdeaCard based on idea_data to the provided all_cards dictionary.
    Modifies the dictionary in place.

    Args:
        all_cards: The dictionary representing the timeline data (e.g., from load_timeline).
        idea_data: A dictionary containing the details for the new idea card.

    Returns:
        A tuple containing the new card's ID and the modified all_cards dictionary.
    """
    card_id = f"card-idea-{uuid.uuid4().hex[:6]}" # Use shorter UUID
    if not isinstance(idea_data, dict):
        logger.warning(f"Invalid idea_data passed to add_idea_card (expected dict, got {type(idea_data)}). Skipping card creation.")
        # Return a distinct invalid ID and unchanged data
        return f"invalid-data-{uuid.uuid4().hex[:6]}", all_cards

    new_card: CardData = {
        "id": card_id,
        "card_type": "IdeaCard", # Explicitly set type
        "title": idea_data.get("title", "Untitled Idea"),
        "description": idea_data.get("description", "No description provided."),
        "budget": idea_data.get("budget", "N/A"), # Store as received
        "time": idea_data.get("time", "N/A"),
        "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat() # Use consistent timestamp
    }

    # Add directly to the dictionary
    all_cards[card_id] = new_card
    logger.info(f"Prepared new IdeaCard '{card_id}' (Title: {new_card['title']}). Will be saved to 'in_timeline' by save_timeline.")
    return card_id, all_cards # Return ID and the modified dictionary

def get_card(all_cards: Dict[str, CardData], card_id: str) -> Optional[CardData]:
    """Retrieves a card by its ID from the internal dictionary."""
    return all_cards.get(card_id)

def format_card_for_prompt(card: CardData) -> str:
    """Formats card details into a string for LLM prompts."""
    # (Keep this function as is)
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

# --- Transaction Loading (Keep as is, add error handling) ---
def load_transactions(file_path: str) -> List[Dict[str, Any]]:
    """Load and parse transactions from JSON file."""
    if not os.path.exists(file_path):
        logger.warning(f"Transactions file not found: {file_path}. Returning empty list.")
        return []
    try:
        with open(file_path, "r") as f:
            # Handle empty file
            content = f.read()
            if not content:
                logger.warning(f"Transactions file {file_path} is empty. Returning empty list.")
                return []
            transactions = json.loads(content)
        if not isinstance(transactions, list):
            logger.error(f"Transactions file {file_path} does not contain a JSON list. Returning empty list.")
            return []
        # Optional: Validate transaction structure here if needed
        logger.info(f"Loaded {len(transactions)} transactions from {file_path}.")
        return transactions
    except json.JSONDecodeError as e:
        logger.error(f"Error decoding JSON from transactions file {file_path}: {e}. Returning empty list.")
        return []
    except IOError as e:
        logger.error(f"Error reading transactions file {file_path}: {e}. Returning empty list.")
        return []
    except Exception as e:
        logger.error(f"Unexpected error loading transactions from {file_path}: {e}. Returning empty list.")
        return []


# --- Agent State (Keep as is) ---
class AgentState(MessagesState):
    waiting_for_response_from: Optional[str] = None
    completed_tasks: List[str] = []
    rewritten_query_for_next_agent: Optional[str] = None
    combine_flow_stage: Optional[Literal["combiner_started", "combiner_complete", "idea_started", "idea_complete"]] = None
    combine_data: Optional[Dict[str, Any]] = None
    current_ideas: List[Dict[str, Any]] = []
    action: Optional[Literal["plan", "idea"]] = None


# --- Agent Prompts (Keep as is) ---
combiner_agent_prompt = """
You are the CombinerAgent. Your task is to analyze two JSON lists provided in the user's request, understanding their structure and content, and generate a *single, final query* for the IdeaAgent.

**JSON List Analysis Process:**
1. Carefully examine both lists to identify their purpose and content.
2. The lists could contain any of the following:
   - Ideas/cards with titles, descriptions, budgets, and times
   - User queries or modification requests
   - Any combination of structured data relevant to event planning
3. There's no fixed order - either list could contain the main ideas or the modification requests.

**Output Requirements:**
1. Generate ONE FINAL query that intelligently combines elements from both lists.
2. Your query must be specific, actionable, and creative.
3. Begin your response with 'FINAL QUERY:' to signal completion.
4. After the 'FINAL QUERY:' prefix, provide ONLY the query text - no explanations.

**Important Rules:**
1. Avoid redundancy and repetition in your query.
2. If one list contains modification requests (e.g., 'increase budget', 'family-friendly'), apply these to the content ideas.
3. If both lists contain ideas, extract complementary elements and combine them meaningfully.
4. Consider the unique ID of each item to differentiate between similar-looking entries.
5. Your output should be a single, focused query that will guide the IdeaAgent to generate new ideas.

Remember, your response must start with 'FINAL QUERY:' followed immediately by your creative, combined query.
"""

idea_agent_prompt = """
You will receive:
- A query text that tells you what to do;
- A payment history, which you must take into consideration when performing your tasks;
- Any existing activities that might need to be updated;
- An action type ('idea' or 'plan') which determines your exact task.

If action is 'idea':
Pretext: The user wants to plan and improve event activities, and you are their assistant.
An event may contain multiple activities that has a title, a description and a budget.
For a planned activity, you will be asked to update the activity creatively based on some given modifications.

-> Your query text will specify what kind of activity to generate or how to modify an existing activity
-> You must take into consideration the payment histories when making or updating activities
-> You will receive one activity to be updated, you must creatively generate 3 different updated activities.
-> The generated activities must be specific, realistic for the planned event, with consideration to the user's past transactions.

Return the result as a JSON array, where each object has:
- idea_id: a number starting from 1
- title: short and clear
- description: plain language explanation
- budget: a realistic cost estimate (number only)
- time: approximate duration (e.g., 'Weekend', 'Day', 'Evening')

Example output format (same for both action types, just different quantity):
[
  {
    "idea_id": 1,
    "title": "Pizza Brainstorm Night",
    "description": "Teams share pizza and talk project ideas after dinner.",
    "budget": 180,
    "time": "Evening"
  },
  {
    "idea_id": 2,
    "title": "Weekend Team Building Retreat",
    "description": "A comprehensive weekend retreat focused on team building and strategic planning.",
    "budget": 3500,
    "time": "Weekend"
  }
]


If action is 'plan':
Pretext: You are a helpful assistant helping users build a custom event plan from a list of activities.
Each activity has an idea_id, a title, a budget, and a description.

-> Your query text will specify an event which you have to plan its activities for.
-> You must take into consideration the payment histories when making or generating activities
-> The generated activities must be specific, realistic for the planned event, with consideration to the user's past transactions.
-> You must generate the activities considering a reasonable chronological order, that would be the best use of the user's time.

You must respond with a JSON list of activities you choose and schedule.
Each object in the list should have the following keys:
- 'card_type': always 'IdeaCard'
- 'title': the activity title
- 'description': the activity description
- 'budget': the activity budget (number or string like 'Medium')
- 'time': suggest a realistic date and time to schedule the activity, must show date in ISO format (e.g. 2025-05-04T10:00:00) or duration (e.g., 'Weekend').

You will be given the current datetime to help with planning. Respond ONLY with the JSON list.
RESPONSE RULES:
- Respond ONLY with a valid JSON array. Do not include any explanation, markdown, or text like ```json.
- Ensure all keys and string values use double quotes.

Example:
[
  {
    "card_type": "IdeaCard",
    "title": "Luxury Getaway",
    "description": "Enjoy a spa and fine dining weekend.",
    "budget": 900,
    "time": "2025-05-04T10:00:00"
  }
]
"""

members = ["CombinerAgent", "IdeaAgent"]
options = members + ["FINISH"]

class Router(TypedDict):
    next: Literal[*options]
    reasoning: str
    rewritten_query: Optional[str]
    final_ideas: Optional[Union[Dict[str, Any], List[Dict[str, Any]]]] # This is for LLM internal use

supervisor_system_prompt = f"""
You are a supervisor in a system that helps users plan events and activities by manipulating 'cards'.
Your job is to route requests between agents: {', '.join(members)} and manage the final response.
Based on the user's message, conversation history, and current state, you decide:
1. Which agent to route to next (or FINISH)
2. What specific instruction (rewritten_query) to give that agent
3. Reasoning for your decision

**Card Types:**
- **CustomCard:** Contains a user-defined query (`user_query`).
- **IdeaCard:** Contains structured fields: `title`, `description`, `budget`, `time`.

**Agent Capabilities:**
- **CombinerAgent:** Takes two cards (formatted as JSON lists) and creates a new query by intelligently combining them. This agent also determines the 'action' type ('plan' or 'idea') based on the combination. Outputs 'FINAL QUERY: <query_text>'.
- **IdeaAgent:** Generates creative event/activity ideas (as a JSON list) based on a query, action type, and transaction context.

**Special Workflow for 'Combine' Operations:**
When processing a combine operation (indicated by the initial message format), follow this sequence:
1. Route to **CombinerAgent** with the raw combine request.
2. When CombinerAgent responds with 'FINAL QUERY:', route to **IdeaAgent** with the extracted query and context.
3. When IdeaAgent completes (outputs a JSON list), the workflow should **FINISH**. The supervisor's role is primarily routing in this flow; the final JSON output comes directly from the IdeaAgent's message.

**Response Format:**
Respond with a JSON object matching the Router structure. 'final_ideas' is for internal reasoning and not the final API output.
```json
{{
  "next": "<CombinerAgent|IdeaAgent|FINISH>",
  "reasoning": "<Explanation>",
  "rewritten_query": "<Instruction for the next agent, or null if FINISH>",
  "final_ideas": null
}}
```
"""

# --- Supervisor Node (Refactored for clarity and direct JSON handling) ---
def supervisor_node(state: AgentState) -> Command:
    """Routes the request based on combine flow state or LLM decision."""
    logger.info("--- SUPERVISOR ---")
    messages = state.get('messages', [])
    combine_flow_stage = state.get('combine_flow_stage')
    action = state.get('action')
    current_ideas = state.get('current_ideas', []) # List of dicts from IdeaAgent
    last_message = messages[-1] if messages else None

    logger.info(f"Combine Stage: {combine_flow_stage}, Action: {action}, Ideas Count: {len(current_ideas)}")
    if last_message:
        logger.debug(f"Last Message: {last_message.pretty_repr() if hasattr(last_message, 'pretty_repr') else str(last_message)[:200]}") # Log snippet

    # --- Combine Workflow Logic ---

    # 1. Final stage: IdeaAgent has run, its output is the final result.
    if combine_flow_stage == "idea_complete":
        logger.info(f"Supervisor: IdeaAgent completed (Action: '{action}'). Routing to END.")
        # The final result is expected to be in the last message (AIMessage from IdeaAgent)
        # No further processing needed here; the calling function will extract it.
        # Reset state for next potential run.
        final_update = {
            "combine_flow_stage": None,
            "rewritten_query_for_next_agent": None,
            "action": None,
            "current_ideas": [],
            "waiting_for_response_from": None
            # Keep messages history as is for context, graph stream returns final state
        }
        return Command(goto=END, update=final_update)

    # 2. Start Combine Flow: Check if the initial message matches the expected format.
    is_combine_start_command = isinstance(last_message, HumanMessage) and last_message.content.startswith("Combine the following two JSON lists:")
    if is_combine_start_command and not combine_flow_stage:
        logger.info("Supervisor: Starting combine flow -> CombinerAgent")
        return Command(
            goto="CombinerAgent",
            update={
                "combine_flow_stage": "combiner_started",
                "rewritten_query_for_next_agent": last_message.content, # Pass the structured prompt
                "current_ideas": [], # Ensure ideas are cleared
                # 'action' should have been set in the initial state
            }
        )

    # 3. After CombinerAgent: Route to IdeaAgent. Check if last message is Combiner output.
    is_combiner_output = isinstance(last_message, AIMessage) and last_message.content.strip().startswith("FINAL QUERY:")
    # Condition: Route if stage is 'combiner_complete' OR if message looks like combiner output (robustness)
    if combine_flow_stage == "combiner_complete" or (is_combiner_output and combine_flow_stage != "idea_started"):
        if isinstance(last_message, AIMessage):
            combiner_output_content = last_message.content.strip()
            logger.info(f"Supervisor: Detected CombinerAgent output. Routing to IdeaAgent.")

            # Extract the actual query
            final_query_match = re.search(r"FINAL QUERY:\s*(.*)", combiner_output_content, re.DOTALL)
            if final_query_match:
                actual_query_for_idea_agent = final_query_match.group(1).strip()
                logger.info(f"Supervisor: Extracted query for IdeaAgent: '{actual_query_for_idea_agent[:100]}...'")
            else:
                logger.warning("Supervisor: Combiner output format unexpected. Using full content.")
                actual_query_for_idea_agent = combiner_output_content # Fallback

            # Prepare context for IdeaAgent
            tx_summary = ""
            try:
                transactions = load_transactions(TRANSACTIONS_FILE)
                if transactions:
                    # Simple summary, adjust formatting as needed
                    tx_summary_lines = [f"- {tx.get('type','N/A')}: ${tx.get('amount','N/A')} ({tx.get('description','N/A')})" for tx in transactions[:5]] # Limit summary
                    tx_summary = "\n\nContext: Recent Transactions:\n" + "\n".join(tx_summary_lines)
                    if len(transactions) > 5:
                         tx_summary += "\n..."
                else:
                    tx_summary = "\n\nContext: No transaction data available."
            except Exception as e:
                logger.warning(f"Could not load transactions for IdeaAgent context: {e}")
                tx_summary = f"\n\nContext: Error loading transaction data: {e}"

            # Construct the full prompt for IdeaAgent
            current_time_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
            idea_query_full = (
                f"Current Time: {current_time_iso}\n"
                f"Action Type Hint: {action}\n\n"
                f"User Query: {actual_query_for_idea_agent}\n"
                f"{tx_summary}"
            )
            logger.debug(f"Supervisor: Full input for IdeaAgent:\n{idea_query_full}")

            return Command(
                goto="IdeaAgent",
                update={
                    "combine_flow_stage": "idea_started",
                    "rewritten_query_for_next_agent": idea_query_full,
                }
            )
        else:
             logger.warning(f"Supervisor: Expected AIMessage after combiner, got {type(last_message)}. Falling back.")
             # Fall through to LLM router might be the safest fallback

    # --- Fallback to LLM Router (Should ideally not be needed for combine flow) ---
    logger.warning("Supervisor: No specific workflow step matched, falling back to LLM router.")
    # Add safety check: Prevent looping back to CombinerAgent immediately
    if is_combiner_output:
         logger.error("Supervisor ERROR: Message looks like Combiner output, but routing conditions failed. FINISHING.")
         return Command(goto=END, update={"messages": [AIMessage(content="Error: Unexpected state after CombinerAgent.")]})

    if not llm:
        logger.error("Supervisor: LLM not initialized. Cannot use LLM router. FINISHING.")
        return Command(goto=END, update={"messages": [AIMessage(content="Error: LLM not available for routing.")]})

    try:
        structured_llm = llm.with_structured_output(Router)
        supervisor_prompt_messages = [{"role": "system", "content": supervisor_system_prompt}]
        for msg in messages: # Ensure messages are serializable
            role = "user" if isinstance(msg, HumanMessage) else "assistant"
            content = msg.content if isinstance(msg.content, str) else json.dumps(msg.content)
            supervisor_prompt_messages.append({"role": role, "content": content})

        logger.info("Supervisor: Asking LLM for routing decision...")
        response: Router = structured_llm.invoke(supervisor_prompt_messages)
        next_route = response.get('next')
        reasoning = response.get('reasoning', "N/A")
        rewritten_query = response.get('rewritten_query')

        logger.info(f"Supervisor Decision (LLM): Route='{next_route}', Reasoning='{reasoning}'")
        if rewritten_query:
            logger.info(f"Supervisor Rewritten Query (LLM): {rewritten_query}")

        # Safety check: Prevent LLM loop back to Combiner
        if next_route == 'CombinerAgent' and is_combiner_output:
            logger.error("Supervisor ERROR: LLM attempted loop back to CombinerAgent. Overriding to FINISH.")
            return Command(goto=END, update={"messages": [AIMessage(content="Error: LLM routing loop attempt.")]})

        update_state = {"rewritten_query_for_next_agent": rewritten_query}
        goto = END if next_route == "FINISH" else next_route

        if goto == END:
             logger.info("Supervisor: LLM decided to FINISH. Resetting combine state.")
             update_state.update({
                 "combine_flow_stage": None, "action": None, "current_ideas": []
             })

        return Command(goto=goto, update=update_state)

    except Exception as e:
        logger.error(f"Error during supervisor LLM call: {e}", exc_info=True)
        error_msg = f"Error during supervisor routing: {e}"
        return Command(goto=END, update={
            "messages": messages + [AIMessage(content=error_msg)],
            "rewritten_query_for_next_agent": None,
            "combine_flow_stage": None, "action": None, "current_ideas": []
        })

# --- Agent Node Creator (Refactored with corrected add_idea_card call) ---
def create_agent_node(agent, agent_name: str):
    """Creates a node function for a given agent."""
    def agent_node(state: AgentState) -> Command:
        logger.info(f"--- Running {agent_name} ---")
        rewritten_query = state.get('rewritten_query_for_next_agent')
        current_messages = state.get('messages', [])
        input_messages = list(current_messages)

        if rewritten_query:
            logger.debug(f"Injecting rewritten query: '{rewritten_query[:200]}...'")
            # Ensure query is in a message format agent expects
            input_messages.append(HumanMessage(content=rewritten_query))
        else:
             logger.warning(f"{agent_name} called without rewritten_query. Using existing messages.")

        if not llm:
             logger.error(f"{agent_name}: LLM not available. Returning error.")
             return Command(update={"messages": [AIMessage(content=f"Error: LLM not available for {agent_name}")]}, goto="supervisor")

        try:
            # Invoke the agent
            result = agent.invoke({"messages": input_messages})
            # Agent response is typically the last message in the result's 'messages' list
            agent_response = result["messages"][-1] if result.get("messages") else AIMessage(content="<No response generated>")
            logger.debug(f"{agent_name} Raw Response: {agent_response.content[:200] if isinstance(agent_response.content, str) else agent_response.content}")

            # Prepare base state update
            update_state = {
                "messages": [agent_response], # Return only the agent's response for supervisor
                "rewritten_query_for_next_agent": None
            }

            # Update combine flow stage
            current_combine_stage = state.get('combine_flow_stage')
            if agent_name == "CombinerAgent" and current_combine_stage == "combiner_started":
                update_state["combine_flow_stage"] = "combiner_complete"
                logger.info(f"Agent Node ({agent_name}): Updated combine stage to 'combiner_complete'")
                # Action type is already set in initial state

            if agent_name == "IdeaAgent" and current_combine_stage == "idea_started":
                update_state["combine_flow_stage"] = "idea_complete"
                logger.info(f"Agent Node ({agent_name}): Updated combine stage to 'idea_complete'")

                # Process IdeaAgent output (JSON list of ideas)
                try:
                    if isinstance(agent_response, AIMessage) and isinstance(agent_response.content, str):
                        content = agent_response.content.strip()
                        # Try to find JSON array (handle potential markdown backticks)
                        json_match = re.search(r'```json\s*(\[.*\])\s*```', content, re.DOTALL)
                        if not json_match:
                             json_match = re.search(r'(\[.*\])', content, re.DOTALL) # Fallback: find any list

                        if json_match:
                            ideas_json_str = json_match.group(1)
                            try:
                                ideas = json.loads(ideas_json_str) # This should be the list of idea dicts
                                if isinstance(ideas, list):
                                    # Store the generated ideas in the state
                                    update_state["current_ideas"] = ideas # Store the list directly
                                    logger.info(f"Agent Node ({agent_name}): Stored {len(ideas)} ideas in state.")

                                    # --- Automatic Saving Removed ---
                                    # The saving logic is moved to the API endpoint after successful workflow completion.
                                    # logger.info(f"Agent Node ({agent_name}): Saving logic moved to API endpoint.")
                                    # --- End Removal ---

                                else:
                                    logger.warning(f"IdeaAgent JSON response was not a list: {ideas_json_str[:200]}")
                                    update_state["current_ideas"] = [] # Reset ideas on invalid format

                            except json.JSONDecodeError as json_e:
                                logger.error(f"Error decoding JSON from IdeaAgent response: {json_e}. Content: {ideas_json_str[:200]}")
                                update_state["current_ideas"] = []
                        else:
                            logger.warning(f"No JSON array found in IdeaAgent response: {content[:200]}")
                            update_state["current_ideas"] = []
                    else:
                         logger.warning(f"IdeaAgent response was not an AIMessage with string content: {type(agent_response)}")
                         update_state["current_ideas"] = []
                except Exception as e:
                    logger.error(f"Error processing IdeaAgent output in agent node: {e}", exc_info=True)
                    update_state["current_ideas"] = [] # Reset on error

            # Always return to supervisor
            return Command(update=update_state, goto="supervisor")

        except Exception as e:
            logger.error(f"Error invoking {agent_name}: {e}", exc_info=True)
            error_message = AIMessage(content=f"Error encountered in {agent_name}: {str(e)}")
            # On error, clear state and return to supervisor
            return Command(
                update={
                    "messages": [error_message],
                    "rewritten_query_for_next_agent": None,
                    "combine_flow_stage": None,
                    "action": None,
                    "current_ideas": []
                },
                goto="supervisor"
            )

    return agent_node


# --- Create Agents (Ensure LLM is available) ---
if llm:
    combiner_agent = create_react_agent(llm, tools=[], prompt=combiner_agent_prompt)
    idea_agent = create_react_agent(llm, tools=[], prompt=idea_agent_prompt)
    combiner_agent_node = create_agent_node(combiner_agent, "CombinerAgent")
    idea_agent_node = create_agent_node(idea_agent, "IdeaAgent")
else:
    logger.error("LLM not initialized. Agents cannot be created.")
    # Handle this case gracefully, maybe disable API endpoints that need agents
    combiner_agent = None
    idea_agent = None
    combiner_agent_node = None
    idea_agent_node = None


# --- Construct Graph (Only if agents were created) ---
graph = None
if combiner_agent_node and idea_agent_node:
    builder = StateGraph(AgentState)
    builder.add_node("supervisor", supervisor_node)
    builder.add_node("CombinerAgent", combiner_agent_node)
    builder.add_node("IdeaAgent", idea_agent_node)

    builder.add_edge(START, "supervisor")
    builder.add_edge("CombinerAgent", "supervisor")
    builder.add_edge("IdeaAgent", "supervisor")
    # Conditional edges from supervisor are handled by Command's 'goto'

    try:
        graph = builder.compile()
        logger.info("LangGraph compiled successfully.")
    except Exception as e:
        logger.error(f"Error compiling LangGraph: {e}", exc_info=True)
        graph = None # Ensure graph is None if compilation fails
else:
    logger.error("Graph cannot be compiled because agent nodes are missing.")


# --- Workflow Execution Functions (Refactored to return Python object) ---

def run_graph_workflow(initial_state: AgentState) -> Optional[Union[List[Dict], Dict, str]]:
    """Runs the compiled graph with the given initial state and returns the final result object or error string."""
    if not graph:
        logger.error("Graph is not compiled. Cannot run workflow.")
        return "Error: Graph not compiled."
    if not llm:
         logger.error("LLM not available. Cannot run workflow.")
         return "Error: LLM not available."

    final_state = None
    result_object = None
    error_message = None

    logger.info(f"Starting graph workflow with initial action: {initial_state.get('action')}")
    try:
        # Use stream_mode="values" to get the full state at each step
        events = graph.stream(
            initial_state,
            stream_mode="values",
            config={"recursion_limit": 15} # Adjust recursion limit if needed
        )
        for i, value in enumerate(events):
            logger.info(f"Workflow Step {i+1} completed. State keys: {list(value.keys())}")
            logger.debug(f"  Action: {value.get('action')}, Stage: {value.get('combine_flow_stage')}")
            final_state = value # Keep track of the last state

    except Exception as e:
        logger.error(f"Error during graph execution: {e}", exc_info=True)
        error_message = f"Error during graph execution: {e}"
        return error_message # Return error string immediately

    # --- Post-Workflow Result Extraction ---
    if final_state and final_state.get('messages'):
        last_message = final_state['messages'][-1]
        logger.info("Workflow finished. Processing final state.")
        if isinstance(last_message, AIMessage):
            final_content = last_message.content
            if isinstance(final_content, str):
                # Attempt to parse if it looks like JSON
                final_content_stripped = final_content.strip()
                if final_content_stripped.startswith('[') and final_content_stripped.endswith(']'):
                    try:
                        result_object = json.loads(final_content_stripped)
                        logger.info("Successfully parsed final message content as JSON list/dict.")
                    except json.JSONDecodeError as json_e:
                        logger.warning(f"Could not parse final AIMessage content as JSON: {json_e}. Content: {final_content_stripped[:200]}")
                        # Decide fallback: return string or specific error
                        result_object = f"Workflow ended, but final message is not valid JSON: {final_content_stripped}"
                elif final_content_stripped.startswith('{') and final_content_stripped.endswith('}'):
                     try:
                        result_object = json.loads(final_content_stripped)
                        logger.info("Successfully parsed final message content as JSON dict.")
                     except json.JSONDecodeError as json_e:
                        logger.warning(f"Could not parse final AIMessage content as JSON dict: {json_e}. Content: {final_content_stripped[:200]}")
                        result_object = f"Workflow ended, but final message is not valid JSON dict: {final_content_stripped}"
                else:
                    # If it's not JSON, return the string content directly
                    logger.info("Final message content is not JSON, returning as string.")
                    result_object = final_content_stripped
            else:
                 # If content is not string (e.g., already a dict/list - unlikely with current setup)
                 logger.info("Final message content is not a string, returning as is.")
                 result_object = final_content # Assume it's the object we want
        else:
            # If the last message isn't from AI, return its representation
            logger.warning(f"Workflow ended, but last message was not AIMessage: {type(last_message)}")
            result_object = f"Workflow ended unexpectedly. Last message: {last_message.pretty_repr() if hasattr(last_message, 'pretty_repr') else str(last_message)}"
    else:
        logger.warning("Workflow finished, but no final state or messages found.")
        result_object = "Workflow finished without a final message."

    return result_object


# --- FastAPI App Setup ---
app = FastAPI(title="Timeline Card Agent API")

# CORS Configuration
origins = [
    "http://localhost",      # Allow local development
    "http://localhost:3000", # Default Next.js dev port
    # Add your deployed frontend URL here
    # "[https://your-frontend-domain.com](https://your-frontend-domain.com)",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"], # Allows all methods (GET, POST, etc.)
    allow_headers=["*"], # Allows all headers
)

# --- API Endpoints ---

@app.get("/")
async def read_root():
    """Root endpoint for basic API check."""
    return {"message": "Timeline Card Agent API is running."}

@app.post("/combine/{card_id1}/{card_id2}", status_code=200)
async def combine_two_cards(
    card_id1: str = Path(..., title="ID of the first card"),
    card_id2: str = Path(..., title="ID of the second card")
):
    """
    Combines two specific cards (IdeaCard or CustomCard) by their IDs,
    runs the workflow, returns the generated ideas/plan, and deletes
    the original two cards from the timeline upon success.
    """
    logger.info(f"Received request to combine cards: '{card_id1}' and '{card_id2}'")

    # 1. Load Timeline and Get Cards
    all_cards = load_timeline()
    card1 = get_card(all_cards, card_id1)
    card2 = get_card(all_cards, card_id2)

    if not card1:
        logger.error(f"Card '{card_id1}' not found.")
        raise HTTPException(status_code=404, detail=f"Card with ID '{card_id1}' not found.")
    if not card2:
        logger.error(f"Card '{card_id2}' not found.")
        raise HTTPException(status_code=404, detail=f"Card with ID '{card_id2}' not found.")

    # 2. Format Cards as JSON Lists for the Workflow
    def format_card_as_list_item(card):
        # Helper to create the dict structure expected by the initial prompt
        return {
            "id": card.get("id", ""),
            "title": card.get("title", card.get("user_query", "Untitled")), # Use query if title missing
            "description": card.get("description", card.get("user_query", "No description")), # Use query if desc missing
            "budget": card.get("budget", "N/A"),
            "time": card.get("time", "N/A")
        }

    json_list1 = [format_card_as_list_item(card1)]
    json_list2 = [format_card_as_list_item(card2)]

    # 3. Determine Action Type (Simple logic: 'idea' for combine two)
    action_type = "idea" # Combining two specific cards usually implies generating variations/ideas
    logger.info(f"Setting action type to '{action_type}' for combining two cards.")

    # 4. Prepare Initial State for the Graph
    initial_message_content = f"Combine the following two JSON lists:\n\nList 1:\n{json.dumps(json_list1, indent=2)}\n\nList 2:\n{json.dumps(json_list2, indent=2)}"
    logger.debug(f"Initial message for combine workflow: {initial_message_content}")

    initial_state = AgentState(
        messages=[HumanMessage(content=initial_message_content)],
        combine_flow_stage=None, # Will be set by supervisor
        action=action_type,
        current_ideas=[] # Start with empty ideas
    )

    # 5. Run the Workflow
    workflow_result = run_graph_workflow(initial_state)

    # 6. Process Result and Handle Side Effects (Deletion)
    if isinstance(workflow_result, (list, dict)):
        logger.info(f"Combine workflow successful for '{card_id1}' and '{card_id2}'. Result type: {type(workflow_result)}")

        # --- Deletion Logic ---
        logger.info(f"Attempting to delete input cards: '{card_id1}', '{card_id2}' from timeline...")
        try:
            # Load fresh data before modifying
            current_timeline_data = load_timeline()
            deleted1 = delete_card_from_timeline(current_timeline_data, card_id1)
            deleted2 = delete_card_from_timeline(current_timeline_data, card_id2)

            if deleted1 or deleted2:
                save_timeline(current_timeline_data)
                logger.info("Timeline saved after deleting input cards.")
            else:
                logger.warning("Neither input card was found for deletion; no changes saved.")
        except Exception as e:
            logger.error(f"Error during post-combine card deletion: {e}", exc_info=True)
            # Decide if this error should prevent returning the result
            # For now, log the error but still return the generated result

        return workflow_result # Return the Python list/dict

    else:
        # Workflow returned an error string or unexpected type
        logger.error(f"Combine workflow failed or returned unexpected result: {workflow_result}")
        # Return a 500 error with the message from the workflow
        raise HTTPException(status_code=500, detail=str(workflow_result))


@app.post("/combine-timeline/{custom_card_id}", status_code=200)
async def combine_custom_card_with_timeline(
    custom_card_id: str = Path(..., title="ID of the CustomCard to combine with the timeline")
):
    """
    Combines a specific CustomCard with all IdeaCards currently in the timeline.
    Runs the workflow (typically resulting in a 'plan'), returns the new plan,
    and replaces the old 'in_timeline' cards and deletes the input CustomCard
    upon success.
    """
    logger.info(f"Received request to combine timeline with CustomCard: '{custom_card_id}'")

    # 1. Load Timeline and Get Custom Card
    all_cards = load_timeline()
    custom_card = get_card(all_cards, custom_card_id)

    if not custom_card or custom_card.get("card_type") != "CustomCard":
        logger.error(f"Card '{custom_card_id}' not found or is not a CustomCard.")
        raise HTTPException(status_code=404, detail=f"Card ID '{custom_card_id}' not found or is not a CustomCard.")

    # 2. Extract IdeaCards (in_timeline)
    idea_cards = [card for card in all_cards.values() if card.get("card_type") == "IdeaCard"]
    logger.info(f"Found {len(idea_cards)} IdeaCards in the current timeline.")

    # 3. Format Cards as JSON Lists
    def format_card_as_list_item(card):
        return {
            "id": card.get("id", ""),
            "title": card.get("title", card.get("user_query", "Untitled")),
            "description": card.get("description", card.get("user_query", "No description")),
            "budget": card.get("budget", "N/A"),
            "time": card.get("time", "N/A")
        }

    idea_list = [format_card_as_list_item(card) for card in idea_cards]
    # Custom card formatted as a single-item list for the prompt structure
    custom_list = [format_card_as_list_item(custom_card)]

    # 4. Determine Action Type (Plan for timeline combination)
    action_type = "plan" # Combining timeline with a query usually implies planning
    logger.info(f"Setting action type to '{action_type}' for combining timeline.")

    # 5. Prepare Initial State
    # Use the same prompt format as the two-list combine
    initial_message_content = f"Combine the following two JSON lists:\n\nList 1:\n{json.dumps(idea_list, indent=2)}\n\nList 2:\n{json.dumps(custom_list, indent=2)}"
    logger.debug(f"Initial message for combine-timeline workflow: {initial_message_content}")

    initial_state = AgentState(
        messages=[HumanMessage(content=initial_message_content)],
        combine_flow_stage=None,
        action=action_type,
        current_ideas=[]
    )

    # 6. Run the Workflow
    workflow_result = run_graph_workflow(initial_state)

    # 7. Process Result and Handle Side Effects (Timeline Update)
    if isinstance(workflow_result, list): # Expecting a list for 'plan' action
        logger.info(f"Combine-timeline workflow successful for '{custom_card_id}'. Result type: list")

        # --- Timeline Update Logic ---
        logger.info(f"Attempting to update timeline: Replace 'in_timeline' with new plan and delete '{custom_card_id}'.")
        try:
            new_ideas_list = workflow_result # The result *is* the list of new ideas

            # Load the current timeline data again to get existing CustomCards
            current_timeline_data = load_timeline()
            logger.info(f"Loaded {len(current_timeline_data)} cards before update.")

            # Prepare the updated timeline dictionary: Start fresh
            updated_timeline_data: Dict[str, CardData] = {}

            # Add the NEW ideas (these become the new 'in_timeline')
            num_new_ideas = 0
            for idea in new_ideas_list:
                if isinstance(idea, dict) and "title" in idea: # Basic validation
                    # Ensure necessary fields and generate ID if missing from LLM output
                    idea['card_type'] = "IdeaCard" # Explicitly set type
                    idea_id = idea.get('id')
                    if not idea_id or not isinstance(idea_id, str) or not idea_id.startswith("card-idea-"):
                         # Generate a new ID if missing or invalid format
                         idea_id = f"card-idea-{uuid.uuid4().hex[:6]}"
                         idea['id'] = idea_id
                         logger.debug(f"Generated new ID for idea: {idea_id}")

                    if 'created_at' not in idea: # Add timestamp if missing
                         idea['created_at'] = datetime.datetime.now(datetime.timezone.utc).isoformat()

                    updated_timeline_data[idea_id] = idea # Add to new dictionary
                    num_new_ideas += 1
                else:
                    logger.warning(f"Skipping invalid idea structure in result: {idea}")
            logger.info(f"Added {num_new_ideas} new IdeaCards to the updated timeline data.")

            # Keep existing CustomCards (out_timeline), EXCLUDING the input one
            num_kept_custom = 0
            num_discarded_custom = 0
            for card_id, card_data in current_timeline_data.items():
                if card_data.get("card_type") == "CustomCard":
                    if card_id != custom_card_id:
                        updated_timeline_data[card_id] = card_data # Keep other custom cards
                        num_kept_custom += 1
                    else:
                        num_discarded_custom += 1 # Count the discarded input card

            logger.info(f"Kept {num_kept_custom} existing CustomCard(s). Discarded input CustomCard '{custom_card_id}' (count: {num_discarded_custom}).")

            # Save the completely rebuilt timeline
            logger.info(f"Saving updated timeline with {len(updated_timeline_data)} total cards...")
            save_timeline(updated_timeline_data)
            logger.info("Timeline saved successfully, replacing the old plan.")

        except Exception as e:
            logger.error(f"Error during post-combine_timeline update: {e}", exc_info=True)
            # Log the error but still return the generated plan
            # Consider adding a warning to the response if update fails

        return workflow_result # Return the new plan (list of dicts)

    elif isinstance(workflow_result, dict):
         logger.warning(f"Combine-timeline workflow returned a dict (expected list for plan): {workflow_result}")
         # Decide how to handle - maybe still update timeline? For now, treat as error.
         raise HTTPException(status_code=500, detail=f"Workflow returned unexpected dictionary for plan action: {workflow_result}")
    else:
        # Workflow returned an error string or unexpected type
        logger.error(f"Combine-timeline workflow failed or returned unexpected result: {workflow_result}")
        raise HTTPException(status_code=500, detail=str(workflow_result))


# --- How to Run ---
# Save this code as api.py
# Install dependencies: pip install fastapi uvicorn python-dotenv langchain-openai langgraph langchain-core langchain "pydantic>=2"
# Run from terminal: uvicorn api:app --reload --port 8000
# The API will be available at http://localhost:8000
