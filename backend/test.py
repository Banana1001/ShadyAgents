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

# --- Configuration ---
TIMELINE_FILE = "timeline.json"
TRANSACTIONS_FILE = "transactions.json"

# --- Environment Setup ---
load_dotenv()
openai_api_key = os.getenv('OPENAI_API_KEY')
if not openai_api_key:
    print("Warning: OPENAI_API_KEY not found in environment variables. LLM calls may fail.")

# --- Set up LLM ---
llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.7, api_key=openai_api_key)

# --- Data Structures ---
CardData = Dict[str, Any]

# --- Timeline/Card Management ---
# ... (load_timeline, save_timeline, add_custom_card, add_idea_card, get_card, format_card_for_prompt, print_timeline functions remain the same) ...
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
    except IOError as e:
        print(f"Error saving {TIMELINE_FILE}: {e}")

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

def add_idea_card(all_cards: Dict[str, CardData], title: str, description: str, budget: str, time: str) -> Tuple[str, CardData]:
    """Adds a new IdeaCard to the internal dictionary."""
    card_id = f"card-idea-{uuid.uuid4().hex[:6]}"
    new_card: CardData = {
        "id": card_id,
        "card_type": "IdeaCard",
        "title": title.strip(),
        "description": description.strip(),
        "budget": budget.strip(), # Ensure budget is stored as string
        "time": time.strip(),
        "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat()
    }
    all_cards[card_id] = new_card
    print(f"IdeaCard created with ID: {card_id} (will be saved to 'in_timeline')")
    return card_id, new_card

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
            raw = json.load(f)

        transactions = []
        for entry in raw:
            if "FromSugarDaddy" in entry:
                source = "income"
                amount = entry["FromSugarDaddy"]["amount"]
                desc = entry["FromSugarDaddy"]["description"]
            elif "ToPurchasePerson" in entry:
                source = "expense"
                amount = entry["ToPurchasePerson"]["amount"]
                desc = entry["ToPurchasePerson"]["description"]
            else:
                continue

            transactions.append({
                "type": source,
                "amount": amount,
                "description": desc
            })
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
    current_ideas: List[Dict[str, Any]] = []  # New: Track generated ideas
    action: Optional[Literal["plan", "idea"]] = None  # New: Track action type

# --- Agent Prompts and Definitions ---
# ... (combiner_agent_prompt, idea_agent_prompt, supervisor_system_prompt remain the same) ...
# CombinerAgent Prompt
combiner_agent_prompt = (
    "You are the CombinerAgent. Your task is to analyze two cards provided in the user's request (the last message), considering their types and fields, and generate a *new, targeted query or description* based on their combination.\n\n"
    "**Card Types:**\n"
    "- **CustomCard:** Has an ID and a free-form `user_query` (string).\n"
    "- **IdeaCard:** Has an ID, `title`, `description`, `budget`, and `time`.\n\n"
    "**Input Format:**\n"
    "The input message will contain the details of both cards, structured similarly to: 'Generate a new query/description by combining Card(Type: <Type1>, ID: <ID1>, ...) and Card(Type: <Type2>, ID: <ID2>, ...)'\n\n"
    "**Your Process:**\n"
    "1.  **Parse Input:** Identify the two cards, their types (CustomCard or IdeaCard), and their respective fields from the input message.\n"
    "2.  **Check for Variation Keywords:** Examine if a `CustomCard` involved has a `user_query` that acts as a variation keyword (e.g., 'shuffle', 'alternatives', 'similar', 'variations', 'different', 'explore', 'like'). Normalize to lowercase for matching.\n"
    "3.  **Determine Intent & Generate Output Based on Combination:**\n"
    "    * **Variation Keyword + Any Card:** If a variation keyword is found in a `CustomCard`'s query, generate a request for alternatives/variations of the *other* card, referencing its key details.\n"
    "        * Example Input: Combine CustomCard(Query: 'shuffle') and IdeaCard(Title: 'Habo Hotel', Budget: 'High').\n"
    "        * Example Output: 'Generate 3 alternative hotel ideas similar to Habo Hotel (High budget).' OR 'Find variations of the Habo Hotel idea.'\n"
    "        * Example Input: Combine CustomCard(Query: 'find alternatives') and CustomCard(Query: 'weekend trip to mountains').\n"
    "        * Example Output: 'Suggest alternative ideas for a weekend trip to the mountains.'\n"
    "    * **CustomCard + CustomCard (No Variation Keyword):** Combine the intent of the two user queries.\n"
    "        * Example Input: Combine CustomCard(Query: 'cheap flights') and CustomCard(Query: 'Paris in Spring').\n"
    "        * Example Output: 'Find cheap flights to Paris for a trip in Spring.'\n"
    "    * **CustomCard + IdeaCard (No Variation Keyword):** Apply the `user_query` from the `CustomCard` as a modification or filter to the `IdeaCard`.\n"
    "        * Example Input: Combine CustomCard(Query: 'lower the budget') and IdeaCard(Title: 'Luxury Ski Trip', Budget: 'Very High').\n"
    "        * Example Output: 'Adapt the 'Luxury Ski Trip' idea for a lower budget.' OR 'Find ideas for a ski trip with a budget lower than Very High.'\n"
    "    * **IdeaCard + IdeaCard:** Find a meaningful connection or synthesis between the two ideas. Consider merging themes, finding common ground, or generating a new idea inspired by both.\n"
    "        * Example Input: Combine IdeaCard(Title: 'Beach Relaxation', Time: 'Summer') and IdeaCard(Title: 'Cultural City Tour', Budget: 'Medium').\n"
    "        * Example Output: 'Suggest ideas for a medium-budget summer trip combining beach relaxation and cultural city exploration.' OR 'Generate a plan for a trip that includes elements of both beach relaxation and a city tour.'\n\n"
    "**Output:**\n"
    "Respond ONLY with the newly generated query or description. Be concise and actionable, reflecting the specifics of the input cards. Do not add explanations or conversational text."
)

# IdeaAgent Prompt (From IdeaAgent.py, slightly modified)
idea_agent_prompt = (
    "Pretext: The user wants to plan and improve event activities, and you are their assistant.\n"
    "An event may contain multiple activities that has a title, a description and a budget.\n"
    "For a planned activity, you will be asked to update the activity creatively based on some given modifications.\n\n"

    "You will receive:\n"
    "- A query text that specifies what kind of activity to generate or how to modify an existing activity\n"
    "- A list of income and expense records, which you must take into consideration when making or updating activities\n"
    "- Any existing activities that might need to be updated\n\n"

    "The generated activities must be specific, realistic for the planned event, with consideration to the user's past transactions.\n\n"
    "To generate any activity, you must:\n"
    "1. Analyze the user's expenses and income, if provided:\n"
    "   - What they typically spend on (e.g., fashion, transportation, food)\n"
    "   - How much they typically spend per item (budget level)\n"
    "2. Based on this, suggest 1-3 creative activities appropriate for the event or modification.\n\n"
    "Return the result as a JSON array, where each object has:\n"
    "- idea_id: a number starting from 1\n"
    "- title: short and clear\n"
    "- description: plain language explanation\n"
    "- budget: a realistic cost estimate (number only)\n"
    "- time: approximate duration (e.g., 'Weekend', 'Day', 'Evening')\n\n"
    "Example output:\n"
    "[\n"
    "  {\n"
    "    \"idea_id\": 1,\n"
    "    \"title\": \"Pizza Brainstorm Night\",\n"
    "    \"description\": \"Teams share pizza and talk project ideas after dinner.\",\n"
    "    \"budget\": 180,\n"
    "    \"time\": \"Evening\"\n"
    "  }\n"
    "]"
)

# Supervisor Prompt (Modified to include the IdeaAgent)
members = ["CombinerAgent", "IdeaAgent"]
options = members + ["FINISH"]

class Router(TypedDict):
    next: Literal[*options]
    reasoning: str
    rewritten_query: Optional[str]
supervisor_system_prompt = (
    "You are a supervisor in a system that helps users plan events and activities by manipulating 'cards'. "
    f"Your job is to route requests between agents: {', '.join(members)} and manage the final response. "
    "Based on the user's message, conversation history, and current state, you decide:\n"
    "1. Which agent to route to next (or FINISH)\n"
    "2. What specific instruction (rewritten_query) to give that agent\n"
    "3. Reasoning for your decision\n\n"
    
    "**Card Types:**\n"
    "- **CustomCard:** Contains a user-defined query (`user_query`).\n"
    "- **IdeaCard:** Contains structured fields: `title`, `description`, `budget`, `time`.\n\n"
    
    "**Agent Capabilities:**\n"
    "- **CombinerAgent:** Takes two cards and creates a new query by intelligently combining them. "
    "This agent also determines the 'action' type ('plan' or 'idea') based on the combination.\n"
    "- **IdeaAgent:** Generates creative event activity ideas based on a query. "
    "This agent populates the 'current_ideas' list with new ideas.\n\n"
    
    "**Special Workflow for 'Combine' Operations:**\n"
    "When processing a combine operation, follow this sequence:\n"
    "1. Route to **CombinerAgent** with the raw combine request\n"
    "2. When CombinerAgent responds, route to **IdeaAgent** with the output from CombinerAgent\n"
    "3. When IdeaAgent completes, examine the 'action' state value:\n"
    "   - If action is 'idea': Select ONE BEST IDEA from the 'current_ideas' list based on relevance to the original query. "
    "   Format your response as a summary of just that one selected idea, focusing on the idea's title, description, budget, and time.\n"
    "   - If action is 'plan': Route to FINISH with the normal output.\n\n"
    
    "**Final Response Selection:**\n"
    "When the IdeaAgent has completed (combine_flow_stage is 'idea_complete') and action is 'idea', your task is to:\n"
    "1. Review all ideas in 'current_ideas'\n"
    "2. Choose the SINGLE BEST idea that matches the user's intention from the original combine request\n"
    "3. Respond ONLY with a well-formatted description of that single chosen idea, including its title, description, budget, and time\n"
    "4. Do NOT list all ideas or mention that you selected from multiple options\n\n"
    
    "**Response Format:**\n"
    "Respond with a JSON object containing 'next', 'reasoning', and 'rewritten_query':\n"
    "```json\n"
    "{{\n"
    "  \"next\": \"<CombinerAgent|IdeaAgent|FINISH>\",\n"
    "  \"reasoning\": \"<Explanation>\",\n"
    "  \"rewritten_query\": \"<Instruction for the next agent, or null if FINISH>\"\n"
    "}}\n"
    "```"
)
def supervisor_node(state: AgentState) -> Command:
    """Routes the request based on combine flow state or LLM decision."""
    print("\n--- SUPERVISOR ---")
    combine_flow_stage = state.get('combine_flow_stage')
    action = state.get('action')
    current_ideas = state.get('current_ideas', [])
    last_message = state['messages'][-1] if state['messages'] else None

    print(f"Combine Flow Stage: {combine_flow_stage}")
    print(f"Action: {action}")
    print(f"Current Ideas Count: {len(current_ideas)}")
    print("Last Message:", last_message.pretty_repr() if hasattr(last_message, 'pretty_repr') else last_message)

    # --- Special handling for final idea selection ---
    if combine_flow_stage == "idea_complete" and action == "idea" and current_ideas:
        print("Supervisor: Processing final idea selection")
        
        # Select the best idea (in a real system, this could use an LLM for selection)
        # For now, just take the first idea as a simple implementation
        selected_idea = current_ideas[0]
        
        # Format a response about just this one idea
        title = selected_idea.get('title', 'Untitled Idea')
        description = selected_idea.get('description', 'No description provided')
        budget = selected_idea.get('budget', 'Unknown')
        time = selected_idea.get('time', 'Anytime')
        
        response_text = (
            f"# {title}\n\n"
            f"{description}\n\n"
            f"**Budget**: {budget}\n"
            f"**Time**: {time}"
        )
        
        final_message = AIMessage(content=response_text)
        
        # Clear state and finish
        return Command(
            goto=END,
            update={
                "messages": [final_message],
                "combine_flow_stage": None,
                "rewritten_query_for_next_agent": None,
                "action": None,
                "current_ideas": []
            }
        )

    # --- Rest of the existing supervisor_node function remains the same ---
    # 1. Start Combine Flow
    if isinstance(last_message, HumanMessage) and 'Combine Card' in last_message.content and not combine_flow_stage:
        print("Supervisor: Starting combine flow -> CombinerAgent")
        return Command(
            goto="CombinerAgent",
            update={
                "combine_flow_stage": "combiner_started", 
                "rewritten_query_for_next_agent": last_message.content,
                "current_ideas": [],  # Initialize empty ideas list
                "action": None  # Clear any previous action
            }
        )

    # 2. After CombinerAgent completes
    if combine_flow_stage == "combiner_complete" and isinstance(last_message, AIMessage):
        combiner_output = last_message.content
        print(f"Supervisor: Combine flow step 2 (Combiner complete) -> IdeaAgent with query: '{combiner_output}'")

        # Prepare query for IdeaAgent (including transactions)
        tx_summary = ""
        try:
            transactions = load_transactions(TRANSACTIONS_FILE)
            if transactions:
                tx_summary = "\n".join(
                    f"{tx['type'].capitalize()} - ${tx['amount']} - {tx['description']}"
                    for tx in transactions
                )
                tx_summary = f"\n\nHere are my past transactions:\n\n{tx_summary}"
        except Exception as e:
            print(f"Warning: Could not load transactions for IdeaAgent query: {e}")

        idea_query = f"{combiner_output}{tx_summary}"

        return Command(
            goto="IdeaAgent",
            update={"combine_flow_stage": "idea_started", "rewritten_query_for_next_agent": idea_query}
        )

    # --- Fallback to LLM Router ---
    print("Supervisor: No active combine flow step or special handling, using LLM router.")
    structured_llm = llm.with_structured_output(Router)
    supervisor_prompt_messages = [{"role": "system", "content": supervisor_system_prompt}]
    for msg in state['messages']:
        if isinstance(msg, HumanMessage):
            supervisor_prompt_messages.append({"role": "user", "content": msg.content})
        elif isinstance(msg, AIMessage):
            supervisor_prompt_messages.append({"role": "assistant", "content": msg.content})

    try:
        print("Supervisor: Asking LLM for routing decision...")
        response = structured_llm.invoke(supervisor_prompt_messages)
        next_route = response['next']
        reasoning = response.get('reasoning', "No reasoning provided.")
        rewritten_query = response.get('rewritten_query')

        print(f"Supervisor Decision (LLM): Route to '{next_route}'")
        print(f"Supervisor Reasoning (LLM): {reasoning}")
        if rewritten_query:
            print(f"Supervisor Rewritten Query for {next_route}: {rewritten_query}")

        # Prepare state update based ONLY on LLM decision
        update_state = {"rewritten_query_for_next_agent": rewritten_query}
        goto = END if next_route == "FINISH" else next_route
        return Command(goto=goto, update=update_state)

    except Exception as e:
        print(f"Error during supervisor LLM call: {e}")
        # Default behavior on error: Finish
        return Command(goto=END, update={
            "rewritten_query_for_next_agent": None, 
            "combine_flow_stage": None,
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
                
                # Set the action type based on the combination
                # For now, always set to "idea" as per requirements
                # Later can be enhanced to detect "plan" actions
                update_state["action"] = "idea"
                print(f"Agent Node ({agent_name}): Set action to 'idea'")
                
                # In the future, parse the response to determine if it's a plan or idea
                # Example logic (placeholder):
                # if "plan" in agent_response.content.lower():
                #     update_state["action"] = "plan"
                # else:
                #     update_state["action"] = "idea"
                
            elif agent_name == "IdeaAgent" and current_combine_stage == "idea_started":
                update_state["combine_flow_stage"] = "idea_complete"
                print(f"Agent Node ({agent_name}): Updated combine stage to 'idea_complete'")

                # Process IdeaAgent output to populate current_ideas
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
                                    # Store ideas in current_ideas state
                                    update_state["current_ideas"] = ideas
                                    print(f"Agent Node ({agent_name}): Added {len(ideas)} ideas to current_ideas")
                                    
                                    # Still process and save ideas to timeline
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
def run_combine_workflow(card1: CardData, card2: CardData) -> Optional[str]:
    """Runs the Supervisor -> Combiner -> Idea workflow for two cards (any type)."""
    print(f"\n--- Starting Combine Workflow for {card1['id']} and {card2['id']} ---")

    # Format cards for the initial message
    card1_str = format_card_for_prompt(card1)
    card2_str = format_card_for_prompt(card2)
    initial_message_content = f"Combine {card1_str} and {card2_str}"

    print(f"Initial message for Supervisor: {initial_message_content}")
    # Ensure initial state has combine_flow_stage as None
    initial_state = {"messages": [HumanMessage(content=initial_message_content)], "combine_flow_stage": None}

    # Stream the workflow execution
    final_state = None
    try:
        # Increased recursion limit slightly, just in case
        events = graph.stream(
            initial_state,
            stream_mode="values",
            config={"recursion_limit": 15}
        )
        print("Workflow steps:")
        for step, value in enumerate(events):
            print(f"Step {step+1} completed. Current state keys: {value.keys()}")
            # You could print more state details here if needed for debugging
            # print(f"  Messages: {value.get('messages')}")
            # print(f"  Combine Stage: {value.get('combine_flow_stage')}")
            final_state = value # Keep track of the latest state

    except Exception as e:
        print(f"\nError during graph execution: {e}")
        # Optionally print traceback for more details
        # import traceback
        # traceback.print_exc()
        return f"Error during graph execution: {e}"

    # Extract and return the final response
    if final_state and final_state.get('messages'):
        last_message = final_state['messages'][-1]
        print("\n--- Combine Workflow Finished ---")
        if isinstance(last_message, AIMessage):
            return last_message.content
        else:
            # If the last message isn't AI, it might be the user input or an error state
            return f"Workflow ended. Last message: {last_message.pretty_repr() if hasattr(last_message, 'pretty_repr') else last_message}"
    else:
        print("\n--- Combine Workflow Finished (No final state message found) ---")
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
                # Get from the internal dict
                card1 = get_card(timeline_cards, id1)
                card2 = get_card(timeline_cards, id2)

                if not card1:
                    print(f"Error: Card with ID '{id1}' not found.")
                    continue
                if not card2:
                    print(f"Error: Card with ID '{id2}' not found.")
                    continue

                # Run the combine workflow
                combination_result = run_combine_workflow(card1, card2)

                print("\n--- Combination Result ---")
                # The result here is the final AI message content or an error/status message
                print(combination_result if combination_result else "No result generated.")
                print("--------------------------")

                # Refresh timeline after combine operation as IdeaAgent might have added cards
                print("\nRefreshing timeline after combine operation...")
                timeline_cards = load_timeline()
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

            else:
                print(f"Error: Unknown command '{command}'. Type 'help' for options.")

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
