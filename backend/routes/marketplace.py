from flask import Blueprint, jsonify

marketplace_bp = Blueprint("marketplace", __name__)

MARKETPLACE_TOOLS = [
    {"name": "ChatGPT Pro", "category": "Productivity", "price": "₹1,615/mo"},
    {"name": "Midjourney Studio", "category": "Design", "price": "₹850/mo"},
    {"name": "Notion AI", "category": "Productivity", "price": "₹680/mo"},
    {"name": "GitHub Copilot", "category": "Development", "price": "₹850/mo"},
    {"name": "Perplexity AI", "category": "Research", "price": "₹1,700/mo"},
]


@marketplace_bp.get("/api/marketplace")
def list_marketplace_tools():
    return jsonify(name="MYRA", tools=MARKETPLACE_TOOLS)