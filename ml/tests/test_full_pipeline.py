import cv2
import sys
import os

sys.path.append(
    os.path.abspath(
        os.path.join(os.path.dirname(__file__), "../..")
    )
)

from ml.embed import embed_watermark
from ml.extract import extract_watermark
from ml.preprocessing.photo import preprocess_photo


# --------------------------------------------------
# 1. Load original image
# --------------------------------------------------

image = cv2.imread(
    "ml/evaluation/test_image.jpg"
)

if image is None:
    raise FileNotFoundError(
        "test_image.jpg not found"
    )


# --------------------------------------------------
# 2. Create test payload
# --------------------------------------------------

payload = bytes(range(50))

print("Original payload size:", len(payload), "bytes")


# --------------------------------------------------
# 3. Embed watermark
# --------------------------------------------------

watermarked = embed_watermark(
    image,
    payload,
    alpha=20.0
)

cv2.imwrite(
    "ml/evaluation/pipeline_watermarked.jpg",
    watermarked
)

print("✓ Watermark embedded")


# --------------------------------------------------
# 4. Preprocess watermarked image
# --------------------------------------------------

preprocessed = preprocess_photo(
    watermarked
)

cv2.imwrite(
    "ml/evaluation/pipeline_preprocessed.jpg",
    preprocessed
)

print("✓ Image preprocessed")


# --------------------------------------------------
# 5. Extract watermark
# --------------------------------------------------

extracted = extract_watermark(
    preprocessed,
    payload_size=50,
    alpha=20.0
)

print("✓ Watermark extracted")


# --------------------------------------------------
# 6. Compare
# --------------------------------------------------

matching_bytes = sum(
    a == b
    for a, b in zip(payload, extracted)
)

print()
print("========== RESULTS ==========")
print("Original bytes :", len(payload))
print("Extracted bytes:", len(extracted))
print(
    "Matching bytes :",
    f"{matching_bytes}/{len(payload)}"
)

if extracted == payload:
    print("✅ EXACT PAYLOAD RECOVERY")
else:
    print("❌ PAYLOAD MISMATCH")

print("=============================")