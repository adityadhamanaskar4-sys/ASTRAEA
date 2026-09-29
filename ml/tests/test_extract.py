import cv2
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from ml.embed import embed_watermark
from ml.extract import extract_watermark


# Load original image
image = cv2.imread("ml/evaluation/test_image.jpg")

if image is None:
    raise FileNotFoundError("test_image.jpg not found")


# Original payload
payload = bytes(range(50))

print("Original payload:")
print(payload)


# Embed
watermarked = embed_watermark(
    image,
    payload,
    alpha=20.0
)

# Extract
extracted = extract_watermark(
    watermarked,
    payload_size=50,
    alpha=20.0
)

print("\nExtracted payload:")
print(extracted)


# Compare
if extracted == payload:
    print("\n✅ SUCCESS: Payload recovered exactly!")
else:
    print("\n❌ FAILED: Payload mismatch!")

    matching = sum(
        a == b
        for a, b in zip(payload, extracted)
    )

    print(
        f"Matching bytes: {matching}/{len(payload)}"
    )