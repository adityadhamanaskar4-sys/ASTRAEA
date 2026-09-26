import pytest
import time
from fastapi.testclient import TestClient

from backend.main import app, pipeline_service
from backend.crypto_interface import CryptoWrapper
from backend.models.requests import BroadcastRequest, DecryptionRequest, AuditRequest

client = TestClient(app)


def test_system_status():
    """Test GET /status endpoint."""
    response = client.get("/status")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ONLINE"
    assert "ledger_status" in data
    assert "crypto_status" in data


def test_broadcast_document():
    """Test POST /broadcast endpoint."""
    payload = {
        "title": "TOP SECRET MAP",
        "classification": "RESTRICTED",
        "body": "Coordinates for sector 9 rendezvous.",
        "recipient_uids": ["OFC-2291", "OFC-1187"]
    }
    response = client.post("/broadcast", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["doc_id"].startswith("DOC-")
    assert data["title"] == "TOP SECRET MAP"
    assert len(data["recipients"]) == 2
    assert data["recipients"][0]["uid"] == "OFC-2291"


def test_decryption_flow_success():
    """Test end-to-end decryption request with valid ML-DSA signature and DLT committal."""
    # 1. Broadcast document
    bc_res = client.post("/broadcast", json={
        "title": "TACTICAL BRIEFING",
        "classification": "CONFIDENTIAL",
        "body": "Operational deployment at 0600 hours.",
        "recipient_uids": ["OFC-2291"]
    }).json()

    doc_id = bc_res["doc_id"]
    timestamp = str(int(time.time()))
    uid = "OFC-2291"
    m_receipt = f"{uid} || {doc_id} || {timestamp}"

    # 2. Generate valid ML-DSA signature
    keys = pipeline_service._get_or_create_recipient_keys(uid)
    sig_bytes = CryptoWrapper.sign_receipt(keys["sk_dsa"], m_receipt)

    dec_req = {
        "uid": uid,
        "doc_id": doc_id,
        "timestamp": timestamp,
        "signature": sig_bytes.hex(),
        "recipient_pk": keys["pk_dsa"].hex()
    }

    # 3. Submit request_decryption
    response = client.post("/request_decryption", json=dec_req)
    assert response.status_code == 200
    data = response.json()

    assert data["doc_id"] == doc_id
    assert data["current_stage"] == "DELIVERED"
    assert len(data["w_id"]) == 64
    assert data["decrypted_content"] == "Operational deployment at 0600 hours."
    assert data["watermarked_image_base64"].startswith("data:image/png;base64,")
    assert data["ledger_record"]["status"] == "committed"


def test_negative_invalid_signature():
    """Negative Test: Invalid ML-DSA signature must block decryption."""
    bc_res = client.post("/broadcast", json={
        "title": "CLASSIFIED DISPATCH",
        "classification": "RESTRICTED",
        "body": "Sensitive message.",
        "recipient_uids": ["OFC-2291"]
    }).json()

    doc_id = bc_res["doc_id"]
    timestamp = str(int(time.time()))

    # Invalid bogus signature
    bogus_sig = "A" * 128

    dec_req = {
        "uid": "OFC-2291",
        "doc_id": doc_id,
        "timestamp": timestamp,
        "signature": bogus_sig
    }

    response = client.post("/request_decryption", json=dec_req)
    assert response.status_code in [400, 422]
    assert "INVALID_SIGNATURE" in response.text or "SIGNATURE_VERIFICATION_FAILED" in response.text


def test_negative_unknown_doc_id():
    """Negative Test: Requesting non-existent document must fail."""
    dec_req = {
        "uid": "OFC-2291",
        "doc_id": "DOC-NONEXISTENT",
        "timestamp": str(int(time.time())),
        "signature": "00" * 64
    }
    response = client.post("/request_decryption", json=dec_req)
    assert response.status_code == 400
    assert "UNKNOWN_DOC_ID" in response.text


def test_audit_flow():
    """Test POST /audit for existing and non-existing W_ID."""
    # 1. Complete decryption to generate a valid W_ID in ledger
    bc_res = client.post("/broadcast", json={
        "title": "INTEL MEMO",
        "classification": "RESTRICTED",
        "body": "Intel payload.",
        "recipient_uids": ["OFC-3305"]
    }).json()

    doc_id = bc_res["doc_id"]
    timestamp = str(int(time.time()))
    uid = "OFC-3305"
    m_receipt = f"{uid} || {doc_id} || {timestamp}"

    keys = pipeline_service._get_or_create_recipient_keys(uid)
    sig_bytes = CryptoWrapper.sign_receipt(keys["sk_dsa"], m_receipt)

    dec_res = client.post("/request_decryption", json={
        "uid": uid,
        "doc_id": doc_id,
        "timestamp": timestamp,
        "signature": sig_bytes.hex(),
        "recipient_pk": keys["pk_dsa"].hex()
    }).json()

    w_id = dec_res["w_id"]

    # 2. Audit existing W_ID
    audit_res = client.post("/audit", json={"w_id": w_id})
    assert audit_res.status_code == 200
    audit_data = audit_res.json()
    assert audit_data["attribution_status"] == "FOUND"
    assert audit_data["parsed_receipt"]["uid"] == uid

    # 3. Audit unknown W_ID
    unknown_wid = "f" * 64
    audit_unknown = client.post("/audit", json={"w_id": unknown_wid})
    assert audit_unknown.status_code == 200
    assert audit_unknown.json()["attribution_status"] == "NOT_FOUND"
