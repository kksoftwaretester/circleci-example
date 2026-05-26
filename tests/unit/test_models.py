from datetime import datetime, timezone

from app.models import Item


def test_to_dict_format():
    item = Item(name="widget")
    item.id = 1
    item.created_at = datetime(2024, 1, 15, 12, 0, 0, tzinfo=timezone.utc)
    d = item.to_dict()
    assert d["id"] == 1
    assert d["name"] == "widget"
    assert "2024-01-15" in d["created_at"]


def test_to_dict_includes_required_keys():
    item = Item(name="test")
    item.id = 42
    item.created_at = datetime(2024, 6, 1, 0, 0, 0, tzinfo=timezone.utc)
    assert set(item.to_dict().keys()) == {"id", "name", "created_at"}


def test_item_name_set():
    item = Item(name="my-item")
    assert item.name == "my-item"
