import cv2
import sys
import os

sys.path.append(
    os.path.abspath(
        os.path.join(os.path.dirname(__file__), "../..")
    )
)

from ml.preprocessing.photo import preprocess_photo


# Load image
image = cv2.imread(
    "ml/evaluation/PhonePhoto.jpeg"
)

if image is None:
    raise FileNotFoundError(
        "test_image.jpg not found"
    )


# Run preprocessing
corrected = preprocess_photo(image)


# Save result
cv2.imwrite(
    "ml/evaluation/preprocessed_test.jpg",
    corrected
)


print("Preprocessing successful!")
print(
    "Original size:",
    image.shape[1],
    "x",
    image.shape[0]
)

print(
    "Processed size:",
    corrected.shape[1],
    "x",
    corrected.shape[0]
)

print(
    "Output:",
    "ml/evaluation/preprocessed_test.jpg"
)