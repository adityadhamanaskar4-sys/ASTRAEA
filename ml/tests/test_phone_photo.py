import cv2
import sys
import os

sys.path.append(
    os.path.abspath(
        os.path.join(os.path.dirname(__file__), "../..")
    )
)

from ml.extract import extract_watermark


# Load the real phone photograph
photo = cv2.imread(
    "ml/evaluation/phone_photo.jpeg"
)

if photo is None:
    raise FileNotFoundError(
        "phone_photo.jpeg not found"
    )

print("Phone photo loaded")
print(
    "Photo size:",
    photo.shape[1],
    "x",
    photo.shape[0]
)


# Try extracting directly
extracted = extract_watermark(
    photo,
    payload_size=50,
    alpha=20.0
)

# Original test payload
payload = bytes(range(50))

matching_bytes = sum(
    a == b
    for a, b in zip(payload, extracted)
)

print()
print("========== PHONE PHOTO TEST ==========")
print("Expected bytes :", len(payload))
print("Extracted bytes:", len(extracted))
print(
    "Matching bytes :",
    f"{matching_bytes}/{len(payload)}"
)

if extracted == payload:
    print("✅ EXACT RECOVERY")
else:
    print("❌ PAYLOAD MISMATCH")

print("======================================")