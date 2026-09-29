import cv2
import sys
import os

sys.path.append(
    os.path.abspath(
        os.path.join(os.path.dirname(__file__), "../..")
    )
)

from ml.extract import extract_watermark


# Load the perspective-corrected phone photo
image = cv2.imread(
    "ml/evaluation/preprocessed_test.jpg"
)

if image is None:
    raise FileNotFoundError(
        "preprocessed_test.jpg not found"
    )


# Original test payload
payload = bytes(range(50))


print("Corrected photo loaded")
print(
    "Image size:",
    image.shape[1],
    "x",
    image.shape[0]
)


# Extract watermark
extracted = extract_watermark(
    image,
    payload_size=50,
    alpha=20.0
)


# Compare
matching_bytes = sum(
    a == b
    for a, b in zip(payload, extracted)
)


print()
print("========== PHOTO EXTRACTION ==========")
print("Expected bytes :", len(payload))
print("Extracted bytes:", len(extracted))
print(
    "Matching bytes :",
    f"{matching_bytes}/{len(payload)}"
)

if extracted == payload:
    print("✅ EXACT PAYLOAD RECOVERY")
else:
    print("❌ PAYLOAD MISMATCH")

print("======================================")