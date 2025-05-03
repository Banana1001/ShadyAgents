import getpass
import os
import random
import datetime
import json
import uuid
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
CARDS_FILE = "cards.json"


# --- 0. Environment Setup ---
load_dotenv()  # Load environment variables from .env file if it exists

# Attempt to get the API key from environment variables loaded from .env
openai_api_key = os.getenv('OPENAI_API_KEY')
# --- Card Data Structures (Conceptual) ---
# CustomCard: id (str), card_type (Literal["CustomCard"]), user_query (str), created_at (str)
# IdeaCard: id (str), card_type (Literal["IdeaCard"]), title (str), description (str), budget (str), time (str), created_at (str)
CardData = Dict[str, Any] # Generic type hint for card dictionaries

# --- Card Management (Updated) ---

def load_cards() -> Dict[str, CardData]:
    """Loads cards from the JSON file."""
    if not os.path.exists(CARDS_FILE):
        # Example: Create a default IdeaCard if file doesn't exist
        default_idea_card = {
            "card-idea-default": {
                "id": "card-idea-default",
                "card_type": "IdeaCard",
                "title": "Weekend Trip Example",
                "description": "A sample idea card for a weekend getaway.",
                "budget": "Medium",
                "time": "Weekend",
                "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat()
            }
        }
        save_cards(default_idea_card)
        print("Card file not found. Created default 'cards.json' with an example IdeaCard.")
        return default_idea_card
    try:
        with open(CARDS_FILE, 'r') as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError) as e:
        print(f"Error loading cards file: {e}. Starting with empty card list.")
        return {}

def save_cards(cards: Dict[str, CardData]):
    """Saves the cards dictionary to the JSON file."""
    try:
        with open(CARDS_FILE, 'w') as f:
            json.dump(cards, f, indent=4)
    except IOError as e:
        print(f"Error saving cards file: {e}")

def add_custom_card(cards: Dict[str, CardData], user_query: str) -> Tuple[str, CardData]:
    """Adds a new CustomCard with a unique ID and saves."""
    card_id = f"card-custom-{uuid.uuid4().hex[:6]}" # Distinguish custom card IDs
    new_card: CardData = {
        "id": card_id,
        "card_type": "CustomCard",
        "user_query": user_query.strip(),
        "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat()
    }
    cards[card_id] = new_card
    print(f"CustomCard created with ID: {card_id}")
    return card_id, new_card

# Function to add IdeaCards (Example - not tied to CLI command yet)
def add_idea_card(cards: Dict[str, CardData], title: str, description: str, budget: str, time: str) -> Tuple[str, CardData]:
    """Adds a new IdeaCard with a unique ID and saves."""
    card_id = f"card-idea-{uuid.uuid4().hex[:6]}" # Distinguish idea card IDs
    new_card: CardData = {
        "id": card_id,
        "card_type": "IdeaCard",
        "title": title.strip(),
        "description": description.strip(),
        "budget": budget.strip(),
        "time": time.strip(),
        "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat()
    }
    cards[card_id] = new_card
    print(f"IdeaCard created with ID: {card_id}")
    return card_id, new_card


def get_card(cards: Dict[str, CardData], card_id: str) -> Optional[CardData]:
    """Retrieves a card by its ID."""
    return cards.get(card_id)

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


def print_cards(cards: Dict[str, CardData]):
    """Prints the current list of cards, formatted by type."""
    if not cards:
        print("\n--- No cards yet. Use 'create <query>' to add a CustomCard. ---")
        return
    print("\n--- Current Cards ---")
    for card_id, card_data in sorted(cards.items()):
        card_type = card_data.get("card_type", "Unknown")
        print(f"  ID: {card_id} ({card_type})")
        if card_type == "CustomCard":
            print(f"    Query: {card_data.get('user_query', 'N/A')}")
        elif card_type == "IdeaCard":
            print(f"    Title: {card_data.get('title', 'N/A')}")
            print(f"    Desc: {card_data.get('description', 'N/A')}")
            print(f"    Budget: {card_data.get('budget', 'N/A')}")
            print(f"    Time: {card_data.get('time', 'N/A')}")
        else: # Fallback for unknown types
            print(f"    Data: {card_data}")
        print(f"    Created: {card_data.get('created_at', 'N/A')}")
        print("-" * 20)
    print("--- End of Cards ---")


# --- LangGraph Setup (Updated for Card Types) ---

# 1. State (Same)
class AgentState(MessagesState):
    rewritten_query_for_next_agent: Optional[str] = None

# 2. Supervisor (Updated Prompt)
members = ["CombinerAgent"]
options = members + ["FINISH"]

class Router(TypedDict):
    next: Literal[*options]
    reasoning: str
    rewritten_query: Optional[str]

llm = ChatOpenAI(model="gpt-4.1-mini", temperature=0)

# *** Supervisor Prompt (Updated for Card Types) ***
supervisor_system_prompt = (
    "You are a supervisor in a system triggered by a user command to combine two specific cards.\n"
    "Your role is to process the initial message, which details the types and contents of the cards being combined, and route it to the CombinerAgent.\n\n"
    "**Card Types:**\n"
    "- **CustomCard:** Contains a user-defined query (`user_query`).\n"
    "- **IdeaCard:** Contains structured fields: `title`, `description`, `budget`, `time`.\n\n"
    "**Input Format:**\n"
    "The input message will be structured like: 'Combine Card(Type: <Type1>, ID: <ID1>, <Field1>: '<Value1>', ...) and Card(Type: <Type2>, ID: <ID2>, <Field2>: '<Value2>', ...)'.\n\n"
    "**Your Tasks:**\n"
    "1.  **Verify Input:** Confirm the message follows the expected 'Combine Card(...) and Card(...)' format.\n"
    "2.  **Route:** Always route to **CombinerAgent** if the input format is correct.\n"
    "3.  **Provide Reasoning:** State that the routing is based on the explicit 'Combine Card' request.\n"
    "4.  **Formulate `rewritten_query`:** Create a concise instruction for the CombinerAgent, passing along the **full details** of both cards as presented in the input message. Example: 'Generate a new query/description by combining Card(Type: CustomCard, ID: card-abc, Query: 'shuffle') and Card(Type: IdeaCard, ID: card-xyz, Title: 'Paris Trip', ...)'\n\n"
    "**Error Handling:**\n"
    "- If the input message does NOT match the expected format, route to **FINISH** and provide reasoning that the input was malformed for a combine action.\n\n"
    "**RESPONSE FORMAT:**\n"
    "Respond with a JSON object containing 'next', 'reasoning', and 'rewritten_query':\n"
    "```json\n"
    "{{\n"
    "  \"next\": \"<CombinerAgent|FINISH>\",\n"
    "  \"reasoning\": \"<Explanation>\",\n"
    "  \"rewritten_query\": \"<Instruction for CombinerAgent including full card details, or null if FINISH>\"\n"
    "}}\n"
    "```"
)

# Supervisor Node function (supervisor_node) remains the same structure, uses new prompt.
def supervisor_node(state: AgentState) -> Command:
    """Routes the combine request to CombinerAgent or finishes if input is wrong."""
    print("\n--- SUPERVISOR ---")
    # Input message now contains detailed card info
    last_message = state['messages'][-1]
    print(f"Processing message: {last_message.content}")

    structured_llm = llm.with_structured_output(Router)
    supervisor_prompt_messages = [
        {"role": "system", "content": supervisor_system_prompt},
        {"role": "user", "content": last_message.content}
    ]

    try:
        print("Supervisor: Asking LLM to process combine request...")
        response = structured_llm.invoke(supervisor_prompt_messages)
        next_route = response['next']
        reasoning = response.get('reasoning', "No reasoning provided.")
        # rewritten_query now contains the detailed card info passed through
        rewritten_query = response.get('rewritten_query') if next_route == "CombinerAgent" else None

        print(f"Supervisor Decision (LLM): Route to '{next_route}'")
        print(f"Supervisor Reasoning (LLM): {reasoning}")
        if rewritten_query:
            print(f"Supervisor Rewritten Query for {next_route}: {rewritten_query}")
        elif next_route == "CombinerAgent":
             print(f"Supervisor Warning: Routing to {next_route} but no rewritten query provided by LLM.")
             next_route = "FINISH"
             reasoning += " (Error: Missing rewritten query for CombinerAgent)"
        else:
             print(f"Supervisor: No rewritten query needed for {next_route}.")

    except Exception as e:
        print(f"Error during supervisor LLM call: {e}")
        try:
            raw_response = llm.invoke(supervisor_prompt_messages)
            print(f"Raw LLM response on error: {raw_response.content}")
        except Exception as inner_e:
            print(f"Could not get raw LLM response: {inner_e}")
        print("Defaulting to FINISH due to error.")
        next_route = "FINISH"
        rewritten_query = None

    update_state = {"rewritten_query_for_next_agent": rewritten_query}
    goto = END if next_route == "FINISH" else next_route
    return Command(goto=goto, update=update_state)


# 3. Define CombinerAgent Node (Node creation function same, Prompt Updated)
# Agent Node function (create_agent_node) remains the same structure.
def create_agent_node(agent, agent_name: str):
    """Creates a graph node function for a given agent."""
    def agent_node(state: AgentState) -> Command:
        print(f"\n--- Running {agent_name} ---")
        # rewritten_query now contains structured card details
        rewritten_query = state.get('rewritten_query_for_next_agent')
        if not rewritten_query:
             print(f"Error: {agent_name} called without a rewritten query. Finishing.")
             return Command(update={"messages": [AIMessage(content="Error: CombinerAgent called without instructions.")]}, goto=END)

        print(f"Received query: '{rewritten_query}'")
        # The rewritten query IS the input for the agent
        input_for_agent = {"messages": [HumanMessage(content=rewritten_query)]}

        try:
            result = agent.invoke(input_for_agent)
            if not isinstance(result, dict) or "messages" not in result or not result["messages"]:
                raise ValueError(f"{agent_name} returned an invalid result structure: {result}")

            agent_response_message = result["messages"][-1]
            if not isinstance(agent_response_message, AIMessage):
                print(f"Warning: {agent_name} did not return AIMessage. Wrapping content.")
                content = getattr(agent_response_message, 'content', str(agent_response_message))
                agent_response_message = AIMessage(content=str(content))

            print(f"{agent_name} Response: {agent_response_message.content[:500]}...")

            update_state = {
                "messages": [agent_response_message],
                "rewritten_query_for_next_agent": None
            }
            return Command(update=update_state, goto=END)

        except Exception as e:
            print(f"Error invoking {agent_name}: {e}")
            error_message = AIMessage(content=f"Error encountered in {agent_name}: {str(e)}")
            return Command(update={"messages": [error_message], "rewritten_query_for_next_agent": None}, goto=END)
    return agent_node


# *** REVISED CombinerAgent Prompt (Aware of Card Types) ***
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


# Create the CombinerAgent with the REVISED type-aware prompt
combiner_agent = create_react_agent(
    llm,
    tools=[],
    prompt=combiner_agent_prompt
)
combiner_agent_node = create_agent_node(combiner_agent, "CombinerAgent")


# 4. Construct Graph (Same as before)
builder = StateGraph(AgentState)
builder.add_node("supervisor", supervisor_node)
builder.add_node("CombinerAgent", combiner_agent_node)
builder.add_edge(START, "supervisor")
builder.add_edge("supervisor", "CombinerAgent") # If supervisor routes here
builder.add_edge("CombinerAgent", END)
graph = builder.compile()
print("\nGraph compiled successfully.")


# --- Graph Invocation Function (Updated) ---

def run_combine_workflow(card1: CardData, card2: CardData) -> Optional[str]:
    """Runs the Supervisor -> Combiner workflow for two cards (any type)."""
    print(f"\n--- Starting Combine Workflow for {card1['id']} and {card2['id']} ---")

    # Format cards for the initial message using the helper function
    card1_str = format_card_for_prompt(card1)
    card2_str = format_card_for_prompt(card2)
    initial_message_content = f"Combine {card1_str} and {card2_str}"

    print(f"Initial message for Supervisor: {initial_message_content}") # Debug: Show formatted message
    initial_state = {"messages": [HumanMessage(content=initial_message_content)]}

    final_state = None
    try:
        events = graph.stream(
            initial_state,
            stream_mode="values",
            config={"recursion_limit": 10}
        )
        print("Workflow steps:")
        for step, value in enumerate(events):
            final_state = value

    except Exception as e:
        print(f"Error during graph execution: {e}")
        return "Error during graph execution."

    # Extract final response (same logic as before)
    if final_state and final_state.get('messages'):
        last_message = final_state['messages'][-1]
        if isinstance(last_message, AIMessage):
            print("--- Combine Workflow Finished ---")
            return last_message.content
        else:
            print("--- Combine Workflow Finished (Ended unexpectedly) ---")
            return f"Workflow ended with unexpected message type: {type(last_message)}"
    else:
        print("--- Combine Workflow Finished (No final state message) ---")
        return "Workflow finished without a final message."


# --- Main CLI Application Loop (Updated 'create' command) ---
# --- Main CLI Application Loop (Corrected 'create' command) ---

def print_help():
    print("\nAvailable Commands:")
    print("  create <query>        - Create a new CustomCard with the given query.")
    # print("  create_idea <...>   - (Not implemented) Create a new IdeaCard.") # Future
    print("  combine <id1> <id2>   - Combine two cards (Custom or Idea) by ID.")
    print("  list                  - Show all existing cards.")
    print("  show <id>             - Show details of a specific card.")
    print("  help                  - Show this help message.")
    print("  exit                  - Quit the application.")

def main():
    print("\n--- Idea & Custom Card Combiner CLI ---")
    cards = load_cards()
    # Optionally add a sample Idea card if none exist beyond the default
    # if not any(c.get("card_type") == "IdeaCard" and c.get("id") != "card-idea-default" for c in cards.values()):
    #     add_idea_card(cards, "Habo Hotel Example", "A high-end hotel.", "High", "Any")
    #     save_cards(cards) # Save if added

    print_cards(cards) # Show initial state

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
            elif command == "create": # This now specifically creates CustomCards
                if not args_str:
                    print("Error: 'create' command needs a query for the CustomCard.")
                    continue
                # Use add_custom_card
                add_custom_card(cards, args_str)
                # --- ADD THIS LINE ---
                save_cards(cards) # Persist the changes to the file
                # --- END OF ADDED LINE ---
                print_cards(cards) # Show updated state
            elif command == "list":
                print_cards(cards)
            elif command == "show":
                 if not args_str:
                     print("Error: 'show' command needs a card ID.")
                     continue
                 card_id_to_show = args_str.strip()
                 card = get_card(cards, card_id_to_show)
                 if card:
                     print("\n--- Card Details ---")
                     # Use the detailed print_cards logic for a single card
                     card_type = card.get("card_type", "Unknown")
                     print(f"  ID: {card['id']} ({card_type})")
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
                card1 = get_card(cards, id1)
                card2 = get_card(cards, id2)

                if not card1:
                    print(f"Error: Card with ID '{id1}' not found.")
                    continue
                if not card2:
                    print(f"Error: Card with ID '{id2}' not found.")
                    continue

                # Cards can be any type, the workflow handles it
                combination_result = run_combine_workflow(card1, card2)

                print("\n--- Combination Result ---")
                print(combination_result if combination_result else "No result generated.")
                print("--------------------------")

            else:
                print(f"Error: Unknown command '{command}'. Type 'help' for options.")

        except EOFError:
            print("\nExiting...")
            break
        except KeyboardInterrupt:
            print("\nExiting...")
            break
        except Exception as e:
            print(f"\nAn unexpected error occurred: {e}")
            # Consider adding logging for tracebacks in production
            # import traceback
            # traceback.print_exc()

    print("\nApplication finished.")

# Keep the rest of the code (imports, functions outside main) the same

if __name__ == "__main__":
    main()