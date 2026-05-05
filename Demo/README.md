# ShopFlow CS Chatbot — Prototype Demo

An AI-powered customer service chatbot prototype built with Claude (Anthropic) and Flask. Demonstrates an agentic support assistant that handles order tracking, returns, and billing questions for a fictional e-commerce brand.

---

## Prerequisites

- Python 3.10 or higher — [download](https://www.python.org/downloads/)
- An Anthropic API key — [get one here](https://console.anthropic.com)

---

## Setup

**1. Clone the repo**
```bash
git clone https://github.com/YOUR_USERNAME/cs-chatbot-prototype.git
cd cs-chatbot-prototype
```

**2. Install dependencies**
```bash
pip install -r requirements.txt
```

**3. Add your API key**

Copy the example env file and add your key:
```bash
cp .env.example .env
```
Open `.env` and replace `your-api-key-here` with your actual Anthropic API key.

**4. Run the server**
```bash
python backend/app.py
```

**5. Open the demo**

Go to [http://localhost:5000](http://localhost:5000) in your browser.

---

## Demo Scenarios

The demo is pre-loaded with a fictional customer, **Maya Patel**. Try asking:

- *"Where is my order?"*
- *"I want to return something"*
- *"I have a question about a charge on my bill"*
