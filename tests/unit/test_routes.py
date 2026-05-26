from unittest.mock import MagicMock, patch


def test_healthz(client):
    resp = client.get("/healthz")
    assert resp.status_code == 200
    assert resp.get_json()["status"] == "ok"


def test_list_items_empty(client):
    with patch("app.routes.db") as mock_db:
        mock_db.session.execute.return_value.scalars.return_value.all.return_value = []
        resp = client.get("/items")
    assert resp.status_code == 200
    assert resp.get_json() == []


def test_list_items_returns_items(client):
    mock_item = MagicMock()
    mock_item.to_dict.return_value = {"id": 1, "name": "widget", "created_at": "2024-01-01T00:00:00+00:00"}
    with patch("app.routes.db") as mock_db:
        mock_db.session.execute.return_value.scalars.return_value.all.return_value = [mock_item]
        resp = client.get("/items")
    assert resp.status_code == 200
    assert resp.get_json()[0]["name"] == "widget"


def test_create_item(client):
    mock_item = MagicMock()
    mock_item.to_dict.return_value = {"id": 1, "name": "widget", "created_at": "2024-01-01T00:00:00+00:00"}
    with patch("app.routes.Item", return_value=mock_item), patch("app.routes.db"):
        resp = client.post("/items", json={"name": "widget"})
    assert resp.status_code == 201
    assert resp.get_json()["name"] == "widget"


def test_create_item_missing_name(client):
    resp = client.post("/items", json={})
    assert resp.status_code == 400
    assert "error" in resp.get_json()


def test_create_item_no_body(client):
    resp = client.post("/items", content_type="application/json", data="")
    assert resp.status_code == 400
