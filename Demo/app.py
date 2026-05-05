# -*- coding: utf-8 -*-
"""
CS Chatbot Prototype - Flask backend
Handles chat messages, Claude API calls with tool use, and conversation state.
"""

import json
import os
import re
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from dotenv import load_dotenv
import anthropic

from tools import TOOL_DEFINITIONS, run_tool
from prompt import SYSTEM_PROMPT

# Load .env from project root, override any existing env vars
_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(_root, '.env'), override=True)

FRONTEND_DIR = os.path.join(os.path.dirname(__file__), '..', 'frontend')

app = Flask(__name__, static_folder=FRONTEND_DIR)
CORS(app)

client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
MODEL = "claude-sonnet-4-5"

# In-memory conversation store keyed by session_id
# For prototype only — resets on server restart
conversations: dict[str, list] = {}


def ensure_end_conversation_option(text: str) -> str:
    """
    Guarantee 'End conversation' is the last chip in any [OPTIONS: ...] block.
    Runs on every final AI response so the survey is always reachable.
    Skips mid-flow confirmations (Confirm return / Cancel).
    """
    END_CHIP = "End conversation"
    MID_FLOW = re.compile(r'Confirm return|Cancel', re.IGNORECASE)

    def inject(match):
        content = match.group(1)  # everything inside [OPTIONS: ...]
        options = [o.strip() for o in content.split('|')]

        # Don't touch mid-flow confirmations
        if any(MID_FLOW.search(o) for o in options):
            return match.group(0)

        # Remove any existing variant so we don't duplicate
        options = [o for o in options if o.lower() != END_CHIP.lower()]
        options.append(END_CHIP)
        return f"[OPTIONS: {' | '.join(options)}]"

    return re.sub(r'\[OPTIONS:\s*([^\]]+)\]', inject, text)


def run_agent_loop(messages: list) -> tuple[str, list, bool]:
    """
    Run the Claude agent loop with tool use.
    Returns (final_text_response, updated_messages, escalated).
    """
    escalated = False
    current_messages = messages.copy()

    while True:
        response = client.messages.create(
            model=MODEL,
            max_tokens=1024,
            system=SYSTEM_PROMPT,
            tools=TOOL_DEFINITIONS,
            messages=current_messages
        )

        # Collect all text and tool_use blocks from this response
        text_blocks = []
        tool_use_blocks = []

        for block in response.content:
            if block.type == "text":
                text_blocks.append(block.text)
            elif block.type == "tool_use":
                tool_use_blocks.append(block)

        # Append the assistant's full response turn
        current_messages.append({
            "role": "assistant",
            "content": response.content
        })

        # If no tool calls — we have a final answer
        if response.stop_reason == "end_turn" or not tool_use_blocks:
            final_text = "\n".join(text_blocks).strip()
            final_text = ensure_end_conversation_option(final_text)
            return final_text, current_messages, escalated

        # Execute each tool call and collect results
        tool_results = []
        for tool_block in tool_use_blocks:
            tool_name = tool_block.name
            tool_input = tool_block.input

            safe_input = json.dumps(tool_input).encode('ascii', 'replace').decode()
            print(f"  -> Tool call: {tool_name}({safe_input})")
            result = run_tool(tool_name, tool_input)
            safe_result = result[:120].encode('ascii', 'replace').decode()
            print(f"  <- Result: {safe_result}...")

            # Detect escalation
            try:
                result_data = json.loads(result)
                if result_data.get("escalated"):
                    escalated = True
            except Exception:
                pass

            tool_results.append({
                "type": "tool_result",
                "tool_use_id": tool_block.id,
                "content": result
            })

        # Append all tool results as a single user turn
        current_messages.append({
            "role": "user",
            "content": tool_results
        })

        # Loop back — Claude will respond to the tool results


# ─── Routes ──────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return send_from_directory(FRONTEND_DIR, 'index.html')


@app.route("/api/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "model": MODEL})


@app.route("/api/chat", methods=["POST"])
def chat():
    """
    POST { session_id, message }
    Returns { response, escalated, session_id }
    """
    body = request.get_json()
    session_id = body.get("session_id", "default")
    user_message = body.get("message", "").strip()

    if not user_message:
        return jsonify({"error": "message is required"}), 400

    # Get or create conversation history
    if session_id not in conversations:
        conversations[session_id] = []

    # Append user message
    conversations[session_id].append({
        "role": "user",
        "content": user_message
    })

    print(f"\n[{session_id}] User: {user_message}")

    try:
        ai_text, updated_messages, escalated = run_agent_loop(conversations[session_id])
        conversations[session_id] = updated_messages

        print(f"[{session_id}] Aria: {ai_text[:100]}...")
        if escalated:
            print(f"[{session_id}] *** ESCALATED TO HUMAN ***")

        return jsonify({
            "response": ai_text,
            "escalated": escalated,
            "session_id": session_id
        })

    except anthropic.APIError as e:
        print(f"[{session_id}] API Error: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/reset", methods=["POST"])
def reset():
    """Reset a session's conversation history. Used by demo reset button."""
    body = request.get_json()
    session_id = body.get("session_id", "default")
    conversations[session_id] = []
    print(f"[{session_id}] Conversation reset")
    return jsonify({"reset": True, "session_id": session_id})


@app.route("/api/history", methods=["GET"])
def history():
    """Return raw conversation history for a session (for debugging)."""
    session_id = request.args.get("session_id", "default")
    msgs = conversations.get(session_id, [])
    # Serialize content blocks to dicts for JSON
    serializable = []
    for m in msgs:
        content = m["content"]
        if isinstance(content, list):
            content = [
                block.model_dump() if hasattr(block, "model_dump") else block
                for block in content
            ]
        serializable.append({"role": m["role"], "content": content})
    return jsonify({"session_id": session_id, "messages": serializable})


if __name__ == "__main__":
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("WARNING: ANTHROPIC_API_KEY not set — add it to your .env file")
    else:
        print("API key loaded OK")
    print("Model:", MODEL)
    print("")
    print("===========================================")
    print("  Server running — open your browser to:")
    print("  http://localhost:5000")
    print("===========================================")
    print("")
    app.run(debug=False, port=5000)
