from flask import Blueprint, jsonify, request
from .models import db, Item

bp = Blueprint("main", __name__)


@bp.get("/healthz")
def healthz():
    return jsonify({"status": "ok"})


@bp.get("/items")
def list_items():
    items = db.session.execute(db.select(Item).order_by(Item.created_at)).scalars().all()
    return jsonify([i.to_dict() for i in items])


@bp.post("/items")
def create_item():
    body = request.get_json(silent=True)
    if not body or not body.get("name"):
        return jsonify({"error": "name is required"}), 400
    item = Item(name=body["name"])
    db.session.add(item)
    db.session.commit()
    return jsonify(item.to_dict()), 201
