from bunq.sdk.context.api_context import ApiContext
from bunq.sdk.context.bunq_context import BunqContext
from bunq.sdk.context.session_context import SessionContext
from bunq.sdk.context.api_environment_type import ApiEnvironmentType
from bunq.sdk.model.generated import endpoint
from bunq.sdk.model.generated.endpoint import MonetaryAccountBankApiObject
from bunq.sdk.model.generated.endpoint import RequestInquiryApiObject
from bunq.sdk.model.generated.endpoint import PaymentApiObject
from bunq.sdk.model.generated.object_ import AmountObject, PointerObject
from bunq.sdk.model.generated.object_ import MonetaryAccountReference, PaymentArrivalExpectedObject

import os
import inspect
import json
from dotenv import load_dotenv

# ========== Config ========== #
SANDBOX_ENV = ApiEnvironmentType.SANDBOX
DEVICE_DESCRIPTION = "My Bunq User App"
API_CONTEXT_FILE_PATH = "bunq_context.json" 

load_dotenv()

# User self
API_KEY = os.getenv("API_KEY_1")
MAIL = os.getenv("MAIL_1")
PHONE = os.getenv("PHONE_1")

# User Purchase
API_KEY_PURCHASE = os.getenv("API_KEY_PURCHASE")
MAIL_PURCHASE = os.getenv("MAIL_PURCHASE")
PHONE_PURCHASE = os.getenv("PHONE_PURCHASE")

# Sugar Daddy
SD_EMAIL = os.geten("SD_EMAIL")

# ========== Functions to set up and make payment ========== #
def set_up_bunq_context():
    apiContext = ApiContext.create(SANDBOX_ENV, API_KEY, DEVICE_DESCRIPTION)
    apiContext.save(API_CONTEXT_FILE_PATH)
    BunqContext.load_api_context(apiContext)

# Lists account balances
def get_account_info():
    accounts = MonetaryAccountBankApiObject.list().value
    for account in accounts: 
        print(account.balance.value)
        print(account.balance.currency)
    return None

# Request payment from sugar daddy
def request_payment_from_sd(money, description): 
    counter_party = PointerObject("EMAIL", SD_EMAIL)
    amount = AmountObject(money, "EUR")
    RequestInquiryApiObject.create(
        amount_inquired=amount,
        counterparty_alias=counter_party,
        description=description,
        allow_bunqme=True
    )
    print("request created")

# Request payment from super sugar daddy
def request_payment_from_pv(): 
    counter_party = PointerObject("PHONE_NUMBER", "+31610468353")
    amount = AmountObject("50000.00", "EUR")
    amount._value = "50000.00"
    amount._currency = "EUR"
    print(amount.value, amount.currency)
    RequestInquiryApiObject.create(
        amount_inquired=amount,
        counterparty_alias=counter_party,
        description="Please make me rich",
        allow_bunqme=True
    )

# Make a payment to user purchase
def send_payment_to_shop(amount, description):
    counter_party = PointerObject("EMAIL", MAIL_PURCHASE)
    amount = AmountObject(amount, "EUR")
    PaymentApiObject.create(
        amount=amount, 
        counterparty_alias=counter_party,
        description=description
    )

# ========== Functions to show history ========== #

# Convert any object to JSON
def to_json(obj):
    result = {}
    for name, method in inspect.getmembers(obj.__class__, predicate=inspect.isdatadescriptor):
        if isinstance(getattr(obj.__class__, name, None), property):
            try:
                result[name] = getattr(obj, name)
            except Exception:
                result[name] = None  
    return result

# Convert a PaymentApiObject to JSON
def payment_to_json(obj : PaymentApiObject):
    result = {}
    for name, method in inspect.getmembers(obj.__class__, predicate=inspect.isdatadescriptor):
        if isinstance(getattr(PaymentApiObject, name, None), property):
            try:
                if name == "alias" or name == "counterparty_alias":
                    result[name] = to_json(getattr(obj, name).pointer)
                elif name == "amount" or name == "balance_after_mutation" or name == "payment_arrival_expected":
                    result[name] = to_json(getattr(obj, name))
                else: 
                    result[name] = getattr(obj, name)
            except Exception:
                result[name] = None 
    return json.dumps(result, default=str, indent=2)

# Shows payment history up to limit
def get_account_history(limit=10): 
    return PaymentApiObject.list().value[:limit]

# Shows the last number of payments
def get_account_last_history(last=1):
    return PaymentApiObject.list().value[:last]

# Shows a simplified version of the last number of payments
def get_account_last_history_simplified(last=1):
    simple_transaction_list = []
    for payment in PaymentApiObject.list().value[:last]:
        simple_transaction = {
            "amount": payment.amount.value,
            "description": payment.description,
        }
        json_transaction = json.dumps(simple_transaction, default=str, indent=2)
        simple_transaction_list.append(json_transaction)
        simple_transaction_list.reverse()
    return simple_transaction_list 

# ========== Function Calls ========== #

set_up_bunq_context()

# ========== Hypothetical payments ========= #

def get_trasactions(file_path): 
    # Open and parse transactions.json
    with open(file_path, 'r', encoding='utf-8') as f: 
        transactions = json.load(f)

    return transactions

def perform_transactions(transactions): 
    for tx in transactions:
        amount = str(tx["amount"])
        description = str(tx["description"])
        send_payment_to_shop(amount, description)
    return len(transactions)

# transactions = get_trasactions("transactions.json")
# last_trans = perform_transactions(transactions)

# ========== Check the last relevant payments ========== #

payments = get_account_last_history_simplified(8)
for payment in payments:
    print(payment)
    print("========================================")

