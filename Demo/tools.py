"""
Tool functions the Claude AI can call.
All data reads from the fake-customers.json file.
"""

import json
import os
from datetime import date, datetime

DATA_PATH = os.path.join(os.path.dirname(__file__), '..', 'data', 'fake-customers.json')

RETURN_WINDOW_DAYS = 30

def _load_data():
    with open(DATA_PATH, 'r') as f:
        return json.load(f)


# ─── Tool implementations ────────────────────────────────────────────────────

def get_customer(customer_id: str) -> dict:
    """Return customer profile by ID."""
    data = _load_data()
    for c in data['customers']:
        if c['id'] == customer_id:
            return c
    return {"error": f"No customer found with id {customer_id}"}


def get_orders_by_customer(customer_id: str) -> dict:
    """Return all orders for a given customer ID."""
    data = _load_data()
    orders = [o for o in data['orders'] if o['customer_id'] == customer_id]
    if not orders:
        return {"error": f"No orders found for customer {customer_id}"}
    return {"orders": orders}


def get_order(order_id: str) -> dict:
    """Return a single order by order ID."""
    data = _load_data()
    for o in data['orders']:
        if o['id'] == order_id:
            return o
    return {"error": f"No order found with id {order_id}"}


def get_invoices_by_customer(customer_id: str) -> dict:
    """Return all invoices for a given customer ID."""
    data = _load_data()
    invoices = [i for i in data['invoices'] if i['customer_id'] == customer_id]
    if not invoices:
        return {"error": f"No invoices found for customer {customer_id}"}
    return {"invoices": invoices}


def get_tickets_by_customer(customer_id: str) -> dict:
    """Return all support tickets for a given customer ID."""
    data = _load_data()
    tickets = [t for t in data['tickets'] if t['customer_id'] == customer_id]
    if not tickets:
        return {"error": f"No tickets found for customer {customer_id}"}
    return {"tickets": tickets}


def initiate_return(order_id: str, reason: str) -> dict:
    """
    Simulate initiating a return for a delivered order.
    Enforces a 30-day return window from delivered_date.
    Returns a return confirmation object or an ineligibility message.
    """
    data = _load_data()
    order = next((o for o in data['orders'] if o['id'] == order_id), None)

    if not order:
        return {"error": f"Order {order_id} not found"}

    if order['status'] not in ['delivered', 'out_for_delivery']:
        return {
            "eligible": False,
            "reason": "not_delivered",
            "message": f"Order {order_id} cannot be returned — it hasn't been delivered yet (status: {order['status']})."
        }

    # 30-day window check — use delivered_date if available, else placed_date
    date_str = order.get('delivered_date') or order.get('placed_date')
    if date_str:
        order_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        days_since = (date.today() - order_date).days
        if days_since > RETURN_WINDOW_DAYS:
            return {
                "eligible": False,
                "reason": "outside_return_window",
                "days_since_delivery": days_since,
                "return_window_days": RETURN_WINDOW_DAYS,
                "message": (
                    f"Order {order_id} was delivered {days_since} days ago. "
                    f"Returns are only accepted within {RETURN_WINDOW_DAYS} days of delivery. "
                    "This order is no longer eligible."
                )
            }

    return_id = f"R-{order_id[-4:]}21"
    refund_amount = order['total']

    return {
        "eligible": True,
        "success": True,
        "return_id": return_id,
        "order_id": order_id,
        "refund_amount": refund_amount,
        "refund_method": order.get('payment_method', 'original payment method'),
        "refund_eta": "3–5 business days after item received",
        "return_label": "Label emailed to customer — drop off at any FedEx within 14 days",
        "reason": reason
    }


def escalate_to_human(customer_id: str, reason: str, summary: str) -> dict:
    """Signal that this conversation should be handed off to a human agent."""
    return {
        "escalated": True,
        "customer_id": customer_id,
        "reason": reason,
        "summary": summary,
        "estimated_wait": "3–5 minutes",
        "agent": "Sarah Chen",
        "message": "You're being connected to a live agent who will have full context of this conversation."
    }


# ─── Tool definitions for Claude API ─────────────────────────────────────────

TOOL_DEFINITIONS = [
    {
        "name": "get_customer",
        "description": "Retrieve a customer's profile including their name, email, account plan, membership status, and payment info.",
        "input_schema": {
            "type": "object",
            "properties": {
                "customer_id": {
                    "type": "string",
                    "description": "The customer's unique ID (e.g. cust-001)"
                }
            },
            "required": ["customer_id"]
        }
    },
    {
        "name": "get_orders_by_customer",
        "description": "Retrieve all orders placed by a customer. Returns order IDs, items, statuses, totals, and tracking info.",
        "input_schema": {
            "type": "object",
            "properties": {
                "customer_id": {
                    "type": "string",
                    "description": "The customer's unique ID"
                }
            },
            "required": ["customer_id"]
        }
    },
    {
        "name": "get_order",
        "description": "Retrieve a single order by its order ID. Returns full order detail including items, shipping, tracking, and refunds.",
        "input_schema": {
            "type": "object",
            "properties": {
                "order_id": {
                    "type": "string",
                    "description": "The order ID (e.g. ORD-4471)"
                }
            },
            "required": ["order_id"]
        }
    },
    {
        "name": "get_invoices_by_customer",
        "description": "Retrieve all invoices for a customer, including payment status, amounts, and any flagged duplicate charges.",
        "input_schema": {
            "type": "object",
            "properties": {
                "customer_id": {
                    "type": "string",
                    "description": "The customer's unique ID"
                }
            },
            "required": ["customer_id"]
        }
    },
    {
        "name": "get_tickets_by_customer",
        "description": "Retrieve all past and open support tickets for a customer, including contact history, notes, and resolution status.",
        "input_schema": {
            "type": "object",
            "properties": {
                "customer_id": {
                    "type": "string",
                    "description": "The customer's unique ID"
                }
            },
            "required": ["customer_id"]
        }
    },
    {
        "name": "initiate_return",
        "description": "Initiate a return for a delivered order. Only call this AFTER the customer has explicitly confirmed they want to proceed with the return. Returns a return ID, refund amount, and label details.",
        "input_schema": {
            "type": "object",
            "properties": {
                "order_id": {
                    "type": "string",
                    "description": "The order ID to return"
                },
                "reason": {
                    "type": "string",
                    "description": "The reason for the return (e.g. 'doesnt_fit', 'damaged', 'wrong_item', 'not_as_described')"
                }
            },
            "required": ["order_id", "reason"]
        }
    },
    {
        "name": "escalate_to_human",
        "description": "Hand off the conversation to a human agent when the issue is too complex, the customer is frustrated, or the AI cannot resolve it. Always call this instead of guessing at an answer you don't know.",
        "input_schema": {
            "type": "object",
            "properties": {
                "customer_id": {
                    "type": "string",
                    "description": "The customer's unique ID"
                },
                "reason": {
                    "type": "string",
                    "description": "Short reason for escalation (e.g. 'billing_dispute', 'complex_issue', 'customer_frustrated', 'outside_ai_scope')"
                },
                "summary": {
                    "type": "string",
                    "description": "2-3 sentence summary of the issue so the human agent doesn't need to re-read the full conversation"
                }
            },
            "required": ["customer_id", "reason", "summary"]
        }
    }
]


# ─── Tool dispatcher ──────────────────────────────────────────────────────────

TOOL_MAP = {
    "get_customer": get_customer,
    "get_orders_by_customer": get_orders_by_customer,
    "get_order": get_order,
    "get_invoices_by_customer": get_invoices_by_customer,
    "get_tickets_by_customer": get_tickets_by_customer,
    "initiate_return": initiate_return,
    "escalate_to_human": escalate_to_human,
}


def run_tool(name: str, inputs: dict) -> str:
    """Execute a tool by name and return its result as a JSON string."""
    fn = TOOL_MAP.get(name)
    if not fn:
        return json.dumps({"error": f"Unknown tool: {name}"})
    result = fn(**inputs)
    return json.dumps(result)
