from fastapi.testclient import TestClient
from src.api import app

client = TestClient(app)

def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"

def test_screen_basic():
    xml = "<Document><AppHdr/><Test>ok</Test></Document>"
    r = client.post("/screen", json={"xml": xml})
    assert r.status_code in (200, 400)
