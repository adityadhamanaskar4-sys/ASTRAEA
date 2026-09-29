import time
import pytest
from fastapi.testclient import TestClient

from backend.main import app, pipeline_service
from backend.crypto_interface import CryptoWrapper

client = TestClient(app)

def test_incomplete_and_noisy_wid_audit_ranking():
    # 1. Distribute and decrypt for two different officers
    bc_res = client.post("/broadcast", json={
        "title": "TOP SECRET CODEWORD",
        "classification": "RESTRICTED",
        "body": "Operational coordinates: 37.7749N, 122.4194W",
        "recipient_uids": ["OFC-2291", "OFC-1187"]
    }).json()
    doc_id = bc_res["doc_id"]

    # Decrypt as OFC-2291
    ts_2291 = str(int(time.time()))
    receipt_2291 = f"OFC-2291 || {doc_id} || {ts_2291}"
    keys_2291 = pipeline_service._get_or_create_recipient_keys("OFC-2291")
    sig_2291 = CryptoWrapper.sign_receipt(keys_2291["sk_dsa"], receipt_2291)
    dec_2291 = client.post("/request_decryption", json={
        "uid": "OFC-2291",
        "doc_id": doc_id,
        "timestamp": ts_2291,
        "signature": sig_2291.hex(),
        "recipient_pk": keys_2291["pk_dsa"].hex()
    }).json()
    wid_2291 = dec_2291["w_id"]

    # Decrypt as OFC-1187
    ts_1187 = str(int(time.time()) + 1)
    receipt_1187 = f"OFC-1187 || {doc_id} || {ts_1187}"
    keys_1187 = pipeline_service._get_or_create_recipient_keys("OFC-1187")
    sig_1187 = CryptoWrapper.sign_receipt(keys_1187["sk_dsa"], receipt_1187)
    dec_1187 = client.post("/request_decryption", json={
        "uid": "OFC-1187",
        "doc_id": doc_id,
        "timestamp": ts_1187,
        "signature": sig_1187.hex(),
        "recipient_pk": keys_1187["pk_dsa"].hex()
    }).json()
    wid_1187 = dec_1187["w_id"]

    # --- Scenario 1: Exact W_ID match ---
    res_exact = client.post("/audit", json={"w_id": wid_2291})
    data_exact = res_exact.json()
    assert data_exact["attribution_status"] == "FOUND"
    assert data_exact["parsed_receipt"]["uid"] == "OFC-2291"
    assert len(data_exact["candidates"]) >= 2
    assert data_exact["candidates"][0]["officer_uid"] == "OFC-2291"
    assert data_exact["candidates"][0]["similarity_percentage"] == 100.0

    # --- Scenario 2: Incomplete W_ID (Prefix recovery, e.g. 16 hex chars) ---
    partial_prefix = wid_2291[:16]
    res_prefix = client.post("/audit", json={"w_id": partial_prefix})
    data_prefix = res_prefix.json()
    assert data_prefix["attribution_status"] == "PARTIAL_MATCH"
    assert data_prefix["parsed_receipt"]["uid"] == "OFC-2291"
    assert "PREFIX_MATCH" in data_prefix["candidates"][0]["match_type"]
    assert data_prefix["candidates"][0]["officer_uid"] == "OFC-2291"

    # --- Scenario 3: Corrupted / Noisy 64-char W_ID (e.g. 3 hex chars modified) ---
    # Invert a few characters at the end of wid_2291
    flipped_char = '0' if wid_2291[-1] != '0' else '1'
    noisy_wid = wid_2291[:-2] + flipped_char * 2
    res_noisy = client.post("/audit", json={"w_id": noisy_wid})
    data_noisy = res_noisy.json()
    assert data_noisy["attribution_status"] == "PARTIAL_MATCH"
    assert data_noisy["parsed_receipt"]["uid"] == "OFC-2291"
    assert data_noisy["candidates"][0]["officer_uid"] == "OFC-2291"
    assert data_noisy["candidates"][0]["similarity_percentage"] >= 95.0

    # --- Scenario 4: Unknown / Random 64-char hash ---
    res_unknown = client.post("/audit", json={"w_id": "0" * 64})
    data_unknown = res_unknown.json()
    assert data_unknown["attribution_status"] == "NOT_FOUND"
    assert len(data_unknown["candidates"]) >= 2
    # Candidates are still listed and ranked
    assert data_unknown["candidates"][0]["similarity_percentage"] < 80.0

    # --- Scenario 5: Scoped search with doc_id matching target document ---
    res_scoped = client.post("/audit", json={"w_id": wid_2291, "doc_id": doc_id})
    data_scoped = res_scoped.json()
    assert data_scoped["attribution_status"] == "FOUND"
    assert data_scoped["parsed_receipt"]["uid"] == "OFC-2291"
    # All candidates must belong to the specified doc_id
    assert len(data_scoped["candidates"]) >= 1
    assert all(c["doc_id"] == doc_id for c in data_scoped["candidates"])

    # --- Scenario 6: Scoped search with non-matching doc_id (reduces window to 0 blocks) ---
    res_mismatch = client.post("/audit", json={"w_id": wid_2291, "doc_id": "DOC-DIFFERENT-UNCOMMITTED"})
    data_mismatch = res_mismatch.json()
    assert data_mismatch["attribution_status"] == "NOT_FOUND"
    assert len(data_mismatch["candidates"]) == 0
