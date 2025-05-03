<<<<<<< HEAD
import os
import json
from dotenv import load_dotenv
from langgraph.prebuilt import create_react_agent
from langgraph.graph import StateGraph
from langgraph.graph import MessagesState, START, END
from langgraph.types import Command
from langchain_core.messages import HumanMessage, AIMessage
from langchain_openai import ChatOpenAI

# Setup
load_dotenv()
openai_api_key = os.getenv("API_KEY_GPT")
os.environ["OPENAI_API_KEY"] = openai_api_key
llm = ChatOpenAI(model="gpt-4.1-mini", temperature=0.7)

# Load and Parse JSON
def load_transactions(file_path: str):
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

# idea system prompt
event_agent_prompt = (
    "You are an AI assistant that generates specific, realistic activities for a planned event using the user's past transactions.\n\n"
    "You will receive:\n"
    "- A type of event (e.g., 'hackathon')\n"
    "- A list of income and expense records\n\n"
    "Steps:\n"
    "1. Analyze the user's expenses and income:\n"
    "   - What they typically spend on (e.g., fashion, transportation, food)\n"
    "   - How much they typically spend per item (budget level)\n"
    "2. Based on this, suggest 3–5 creative activities appropriate for the event.\n\n"
    "Return the result as a JSON array, where each object has:\n"
    "- idea_id: a number starting from 1\n"
    "- title: short and clear\n"
    "- description: plain language explanation\n"
    "- budget: a realistic cost estimate (number only)\n\n"
    "Example output:\n"
    "[\n"
    "  {\n"
    "    \"idea_id\": 1,\n"
    "    \"title\": \"Pizza Brainstorm Night\",\n"
    "    \"description\": \"Teams share pizza and talk project ideas after dinner.\",\n"
    "    \"budget\": 180\n"
    "  }\n"
    "]"
)

# LangGraph Agent
event_agent = create_react_agent(
    llm,
    tools=[],
    prompt=event_agent_prompt
)

class AgentState(MessagesState):
    pass

# Create the node function for the agent
def create_agent_node(agent, agent_name: str):
    """Creates a node function for a given agent with rewritten query injection."""
    def agent_node(state: dict) -> Command:
        print(f"\n--- Running {agent_name} ---")

        input_for_agent = state  # Default to original state
        rewritten_query = state.get('rewritten_query_for_next_agent')

        if rewritten_query:
            print(f"Injecting rewritten query into agent input: '{rewritten_query}'")
            try:
                modified_input_state = state.copy()
            except AttributeError:
                modified_input_state = {key: state.get(key) for key in state}

            current_messages = modified_input_state.get('messages', [])
            if not isinstance(current_messages, list):
                current_messages = []

            modified_input_state['messages'] = list(current_messages) + [HumanMessage(content=rewritten_query)]
            input_for_agent = modified_input_state

        # --- Run the agent ---
        messages = input_for_agent.get("messages", [])
        result = agent.invoke({"messages": messages})
        agent_response = result["messages"][-1] if result["messages"] else AIMessage(content="No response.")
        return Command(update={"messages": [agent_response]}, goto=END)

    return agent_node

# Build the LangGraph
builder = StateGraph(AgentState)
builder.add_node("EventIdeaAgent", create_agent_node(event_agent, "EventIdeaAgent"))
builder.set_entry_point("EventIdeaAgent")
builder.add_edge("EventIdeaAgent", END)
graph = builder.compile()

# Run a Query
def run_query(event_type: str, transaction_file_path: str):
    transactions = load_transactions(transaction_file_path)

    # Format transactions for the prompt
    tx_summary = "\n".join(
        f"{tx['type'].capitalize()} - ${tx['amount']} - {tx['description']}"
        for tx in transactions
    )

    user_prompt = (
        f"I'm planning a {event_type}.\n"
        f"Here are my past transactions:\n\n{tx_summary}"
    )

    events = graph.stream({"messages": [HumanMessage(content=user_prompt)]}, stream_mode="values")
    final_state = list(events)[-1]
    for msg in final_state.get("messages", []):
        print("\nAssistant:", msg.content)



if __name__ == "__main__":
    run_query("hackathon", "transactions.json")
=======
import os
import json
from dotenv import load_dotenv
from langgraph.prebuilt import create_react_agent
from langgraph.graph import StateGraph
from langgraph.graph import MessagesState, START, END
from langgraph.types import Command
from langchain_core.messages import HumanMessage, AIMessage
from langchain_openai import ChatOpenAI

# Setup
load_dotenv()
openai_api_key = os.getenv("API_KEY_GPT")
os.environ["OPENAI_API_KEY"] = openai_api_key
llm = ChatOpenAI(model="gpt-4.1-mini", temperature=0.7)

# Load and Parse Transactions JSON
def load_transactions(file_path: str):
    with open(file_path, "r") as f:
        transactions = json.load(f)
    return transactions

# Load and Parse Cards JSON
def load_cards(file_path: str):
    with open("cards.json", "r") as f:
        cards = json.load(f)
    return cards

# idea system prompt
event_agent_prompt = (
    "Pretext: The user wants to plan and improve event activities, and you are their assistant.\n"
    "An event may contain multiple activities that has a title, a description and a budget.\n"
    "For a planned activity, you will be asked to update the acitivity creatively based on some given modifications.\n\n"

    "You will receive:\n"
    "- A query text mentioning the title of the acitivity to udate, and how you should update it (e.g. Lower Birthday Dinner's budget)\n"
    "- A list of income and expense records, which you must take into consideration when making or updateing activities (e.g. spending pattern, budgets)\n\n"
    "- The current event activities, where you would find the activity which you are requested to change.\n\n"

    "The generated activities must be specific, realistic for the planned event, with consideration to the user's past transactions.\n\n"
    "To generate any activity, you must:\n"
    "1. Analyze the user's expenses and income:\n"
    "   - What they typically spend on (e.g., fashion, transportation, food)\n"
    "   - How much they typically spend per item (budget level)\n"
    "2. Based on this, suggest 3–5 creative activities appropriate for the event.\n\n"
    "Return the result as a JSON array, where each object has:\n"
    "- idea_id: a number starting from 1\n"
    "- title: short and clear\n"
    "- description: plain language explanation\n"
    "- budget: a realistic cost estimate (number only)\n\n"
    "Example output:\n"
    "[\n"
    "  {\n"
    "    \"idea_id\": 1,\n"
    "    \"title\": \"Pizza Brainstorm Night\",\n"
    "    \"description\": \"Teams share pizza and talk project ideas after dinner.\",\n"
    "    \"budget\": 180\n"
    "  }\n"
    "]"
)

# LangGraph Agent
event_agent = create_react_agent(
    llm,
    tools=[],
    prompt=event_agent_prompt
)

class AgentState(MessagesState):
    pass

# Create the node function for the agent
def create_agent_node(agent, agent_name: str):
    """Creates a node function for a given agent with rewritten query injection."""
    def agent_node(state: dict) -> Command:
        print(f"\n--- Running {agent_name} ---")

        input_for_agent = state  # Default to original state
        rewritten_query = state.get('rewritten_query_for_next_agent')

        if rewritten_query:
            print(f"Injecting rewritten query into agent input: '{rewritten_query}'")
            try:
                modified_input_state = state.copy()
            except AttributeError:
                modified_input_state = {key: state.get(key) for key in state}

            current_messages = modified_input_state.get('messages', [])
            if not isinstance(current_messages, list):
                current_messages = []

            modified_input_state['messages'] = list(current_messages) + [HumanMessage(content=rewritten_query)]
            input_for_agent = modified_input_state

        # --- Run the agent ---
        messages = input_for_agent.get("messages", [])
        result = agent.invoke({"messages": messages})
        agent_response = result["messages"][-1] if result["messages"] else AIMessage(content="No response.")
        return Command(update={"messages": [agent_response]}, goto=END)

    return agent_node

# Build the LangGraph
builder = StateGraph(AgentState)
builder.add_node("EventIdeaAgent", create_agent_node(event_agent, "EventIdeaAgent"))
builder.set_entry_point("EventIdeaAgent")
builder.add_edge("EventIdeaAgent", END)
graph = builder.compile()

# Run a Query
def run_query(prompt: str, transaction_file_path: str, cards_file_path: str):
    transactions = load_transactions(transaction_file_path)
    cards = load_cards(cards_file_path)

    # Format transactions for the prompt
    tx_summary = "\n".join(
        f"{tx['type'].capitalize()} - ${tx['amount']} - {tx['description']}"
        for tx in transactions
    )

    card_summary = "\n".join(
        ", ".join(f"{k}: {v}" for k, v in card.items())
        for card in cards.values()
    )

    user_prompt = (
        f"{prompt}\n"
        f"Here are the current acitvities:\n\n{card_summary}\n\n"
        f"Here are my past transactions:\n\n{tx_summary}"
    )

    events = graph.stream({"messages": [HumanMessage(content=user_prompt)]}, stream_mode="values")
    final_state = list(events)[-1]
    for msg in final_state.get("messages", []):
        print("\nAssistant:", msg.content)



if __name__ == "__main__":
    run_query("Adapt the 'Weekend Trip Example' idea for an increased budget.", "transactions.json", "cards.json")
>>>>>>> origin/combiner
