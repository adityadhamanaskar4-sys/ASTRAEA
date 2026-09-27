import pytest
import time
from fastapi.testclient import TestClient

from backend.main import app, pipeline_service
from backend.models.requests import BroadcastRequest, DecryptionRequest, AuditRequest

client = TestClient(app)

def test_frontend_backend_airgapped_integration():
    """
    Simulates the exact HTTP flow executed by the React Frontend in airgapped mode:
    1. Frontend loads user roster from SQLite (GET /users)
    2. Officer distributes classified document (POST /broadcast)
    3. Recipient Officer requests hardware token signature (POST /users/{uid}/sign)
    4. Recipient Terminal submits signed receipt to DLT consensus (POST /request_decryption)
    5. Decryption key released & watermarked image generated
    6. Forensic Investigator queries ledger with extracted W_ID (POST /audit)
    """
    # Step 1: Frontend loads users from SQLite
    users_res = client.get("/users")
    assert users_res.status_code == 200
    users = users_res.json()
    assert len(users) >= 5
    officer_uid = users[0]["uid"]  # OFC-2291

    # Step 2: Distribution Page broadcasts document
    bc_res = client.post("/broadcast", json={
        "title": "OPERATION DESERT EAGLE",
        "classification": "TOP SECRET",
        "body": "Strike package authorization details for sector 4.",
        "recipient_uids": [officer_uid, users[1]["uid"]]
    })
    assert bc_res.status_code == 200
    bc_data = bc_res.json()
    doc_id = bc_data["doc_id"]
    assert doc_id.startswith("DOC-")

    # Step 3: Recipient Terminal requests Hardware Token Signature
    timestamp = str(int(time.time()))
    receipt_str = f"{officer_uid} || {doc_id} || {timestamp}"
    sign_res = client.post(f"/users/{officer_uid}/sign", json={
        "receipt": receipt_str
    })
    assert sign_res.status_code == 200
    sign_data = sign_res.json()
    signature_hex = sign_data["signature"]
    recipient_pk_hex = sign_data["recipient_pk"]

    # Step 4: Recipient Terminal submits decryption request
    dec_res = client.post("/request_decryption", json={
        "uid": officer_uid,
        "doc_id": doc_id,
        "timestamp": timestamp,
        "signature": signature_hex,
        "recipient_pk": recipient_pk_hex
    })
    assert dec_res.status_code == 200
    dec_data = dec_res.json()
    assert dec_data["current_stage"] == "DELIVERED"
    assert dec_data["ledger_record"]["status"] == "committed"
    assert "agreeing_nodes" in dec_data["ledger_record"] or "consensusNodes" in dec_data["ledger_record"]
    w_id = dec_data["w_id"]
    assert len(w_id) == 64
    assert dec_data["watermarked_image_base64"].startswith("data:image/png;base64,")

    # Step 5: Investigator Portal uploads leak or queries W_ID against SQLite ledger
    audit_res = client.post("/audit", json={"w_id": w_id})
    assert audit_res.status_code == 200
    audit_data = audit_res.json()
    assert audit_data["attribution_status"] == "FOUND"
    assert audit_data["signature_verified"] is True
    assert audit_data["parsed_receipt"]["uid"] == officer_uid
    assert audit_data["parsed_receipt"]["doc_id"] == doc_id
