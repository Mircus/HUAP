"""
Specialist Squad E-commerce Demo Nodes.

Six specialist nodes demonstrating the model router with different
capabilities. All nodes are stub-safe — they work with HUAP_LLM_MODE=stub.
"""
from __future__ import annotations

import json
from typing import Any, Dict


def sam_strip_background(state: Dict[str, Any]) -> Dict[str, Any]:
    """SAM — strip background from a product image (stub: marks done)."""
    image_url = state.get("image_url", "product.jpg")
    return {
        "background_stripped": True,
        "processed_image": f"processed_{image_url}",
        "sam_note": "Background removed (stub)",
    }


def vlm_write_description(state: Dict[str, Any]) -> Dict[str, Any]:
    """VLM — write a product description (capability=vision or chat)."""
    product = state.get("product_name", "Widget")
    image = state.get("processed_image", "product.jpg")
    return {
        "description": f"Premium {product}: high-quality craftsmanship, modern design. Image: {image}",
        "vlm_model_used": "stub_chat",
    }


def moe_route_ticket(state: Dict[str, Any]) -> Dict[str, Any]:
    """MoE — route a support ticket (capability=classify)."""
    ticket = state.get("ticket_text", "I need help with my order")
    text_lower = ticket.lower()
    if "refund" in text_lower or "return" in text_lower:
        category = "returns"
    elif "order" in text_lower or "shipping" in text_lower:
        category = "order_status"
    elif "complaint" in text_lower or "angry" in text_lower:
        category = "complaint"
    else:
        category = "general"
    return {
        "ticket_category": category,
        "confidence": 0.92,
        "moe_model_used": "stub_chat",
    }


def lam_process_order(state: Dict[str, Any]) -> Dict[str, Any]:
    """LAM — process an order, update inventory (uses fs_sandbox pattern)."""
    order_id = state.get("order_id", "ORD-001")
    product = state.get("product_name", "Widget")
    qty = state.get("quantity", 1)

    # Deterministic inventory update (no actual file I/O in stub mode)
    inventory = state.get("inventory", {product: 100})
    current = inventory.get(product, 0)
    new_qty = max(0, current - qty)
    inventory[product] = new_qty

    return {
        "order_processed": True,
        "order_id": order_id,
        "product": product,
        "quantity_ordered": qty,
        "inventory_remaining": new_qty,
        "inventory": inventory,
    }


def slm_local_search(state: Dict[str, Any]) -> Dict[str, Any]:
    """SLM — local product search (simple, no cloud needed)."""
    query = state.get("search_query", "")
    catalog = state.get("catalog", [
        {"id": "P001", "name": "Widget", "price": 9.99},
        {"id": "P002", "name": "Gadget", "price": 19.99},
        {"id": "P003", "name": "Doohickey", "price": 4.99},
    ])
    results = [p for p in catalog if query.lower() in p.get("name", "").lower()]
    return {
        "search_results": results or catalog[:2],
        "result_count": len(results) if results else 2,
    }


def llm_handle_complaint(state: Dict[str, Any]) -> Dict[str, Any]:
    """LLM — handle a customer complaint (capability=chat)."""
    ticket = state.get("ticket_text", "")
    category = state.get("ticket_category", "general")
    return {
        "response": f"Thank you for contacting us about your {category} issue. "
                    f"We take your feedback seriously and will resolve this promptly.",
        "resolution_status": "pending_review",
        "llm_model_used": "stub_chat",
    }
