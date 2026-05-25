import pytest


def test_healthz(client):
    resp = client.get("/healthz")
    assert resp.status_code == 200
    assert resp.get_json()["status"] == "ok"


def test_list_items_empty(client):
    resp = client.get("/items")
    assert resp.status_code == 200
    assert resp.get_json() == []


def test_create_item(client):
    resp = client.post("/items", json={"name": "widget"})
    assert resp.status_code == 201
    data = resp.get_json()
    assert data["name"] == "widget"
    assert "id" in data
    assert "created_at" in data


def test_create_item_missing_name(client):
    resp = client.post("/items", json={})
    assert resp.status_code == 400
    assert "error" in resp.get_json()


def test_create_item_no_body(client):
    resp = client.post("/items", content_type="application/json", data="")
    assert resp.status_code == 400


def test_list_items_returns_created(client):
    client.post("/items", json={"name": "alpha"})
    client.post("/items", json={"name": "beta"})
    resp = client.get("/items")
    assert resp.status_code == 200
    names = [i["name"] for i in resp.get_json()]
    assert "alpha" in names
    assert "beta" in names
