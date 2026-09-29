import sys
sys.path.insert(0, ".")
import io
import base64
import cv2
import numpy as np
from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)

print("=== STEP 1: Broadcast confidential document to Officer OFC-2291 and OFC-1187 ===")
b_res = client.post("/broadcast", json={
    "title": "TOP SECRET OPERATION ASTRAEA",
    "classification": "RESTRICTED",
    "body": "Phase 4 tactical maneuver coordinates: Sector 7G. Authorization code: DELTA-9.",
    "recipient_uids": ["OFC-2291", "OFC-1187"]
})
assert b_res.status_code == 200, b_res.text
doc_data = b_res.json()
doc_id = doc_data["doc_id"]
print(f"Document created: {doc_id}")

print("\n=== STEP 2: Officer OFC-2291 requests decryption and signs receipt ===")
timestamp = "1774880000"
receipt_str = f"OFC-2291 || {doc_id} || {timestamp}"
sign_res = client.post("/users/OFC-2291/sign", json={
    "receipt": receipt_str,
    "doc_id": doc_id,
    "timestamp": timestamp
})
assert sign_res.status_code == 200, sign_res.text
sign_data = sign_res.json()
sig_hex = sign_data["signature"]
pk_hex = sign_data["recipient_pk"]

dec_res = client.post("/request_decryption", json={
    "uid": "OFC-2291",
    "doc_id": doc_id,
    "timestamp": timestamp,
    "signature": sig_hex,
    "recipient_pk": pk_hex
})
assert dec_res.status_code == 200, dec_res.text
dec_data = dec_res.json()
wid = dec_data["w_id"]
wm_b64 = dec_data["watermarked_image_base64"]
print(f"Decryption successful!")
print(f"Committed W_ID: {wid}")
print(f"Watermarked image base64 length: {len(wm_b64)}")

print("\n=== STEP 3: Simulate leaked photograph (Decode image, add JPEG compression) ===")
clean_b64 = wm_b64.split(",")[-1]
img_bytes = base64.b64decode(clean_b64)
nparr = np.frombuffer(img_bytes, np.uint8)
img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

# Re-encode as JPEG with quality 65 (simulating phone camera / transmission compression)
_, jpg_buf = cv2.imencode(".jpg", img, [cv2.IMWRITE_JPEG_QUALITY, 65])
jpg_bytes = jpg_buf.tobytes()

print("\n=== STEP 4: Investigator uploads leaked photo to /audit/upload ===")
audit_res = client.post(
    "/audit/upload",
    files={"file": ("leaked_screen_photo.jpg", io.BytesIO(jpg_bytes), "image/jpeg")}
)
assert audit_res.status_code == 200, audit_res.text
audit_data = audit_res.json()

print(f"Attribution Status    : {audit_data['attribution_status']}")
print(f"Extracted W_ID*       : {audit_data['extracted_wid']}")
print(f"W_ID Exact Match      : {audit_data['extracted_wid'] == wid}")
print(f"Attributed Officer UID: {audit_data['parsed_receipt']['uid']}")
print(f"Attributed Document ID: {audit_data['parsed_receipt']['doc_id']}")
print(f"Committed Block ID    : #{audit_data['block_id']}")
print(f"Signature Verified    : {audit_data['signature_verified']}")
print(f"Forensic Message      : {audit_data['message']}")

assert audit_data["attribution_status"] == "FOUND"
assert audit_data["extracted_wid"] == wid
assert audit_data["parsed_receipt"]["uid"] == "OFC-2291"
assert audit_data["parsed_receipt"]["doc_id"] == doc_id
assert audit_data["signature_verified"] is True
print("\n>>> FULL FORENSIC LEAK ATTRIBUTION VERIFIED 100% SUCCESSFUL! <<<")
