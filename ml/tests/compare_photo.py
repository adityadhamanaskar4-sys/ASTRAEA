import cv2
import numpy as np


original = cv2.imread(
    "ml/evaluation/pipeline_watermarked.jpg"
)

corrected = cv2.imread(
    "ml/evaluation/preprocessed_test.jpg"
)

if original is None:
    raise FileNotFoundError(
        "pipeline_watermarked.jpg not found"
    )

if corrected is None:
    raise FileNotFoundError(
        "preprocessed_test.jpg not found"
    )


print("Original:", original.shape)
print("Corrected:", corrected.shape)


# Mean absolute pixel difference
difference = cv2.absdiff(
    original,
    corrected
)

mean_difference = np.mean(difference)

print()
print("========== PHOTO DISTORTION ==========")
print(
    "Mean pixel difference:",
    round(float(mean_difference), 2)
)

print(
    "Maximum pixel difference:",
    int(np.max(difference))
)

print("======================================")