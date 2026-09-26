import cv2
import numpy as np


TARGET_WIDTH = 3840
TARGET_HEIGHT = 2160


def order_points(points):
    """
    Order four points as:
    top-left, top-right, bottom-right, bottom-left
    """

    points = np.array(points, dtype=np.float32)

    ordered = np.zeros((4, 2), dtype=np.float32)

    point_sum = points.sum(axis=1)
    point_diff = np.diff(points, axis=1).reshape(-1)

    ordered[0] = points[np.argmin(point_sum)]   # top-left
    ordered[2] = points[np.argmax(point_sum)]   # bottom-right
    ordered[1] = points[np.argmin(point_diff)]  # top-right
    ordered[3] = points[np.argmax(point_diff)]  # bottom-left

    return ordered


def four_point_transform(image, points):
    """
    Perspective-correct the detected artifact
    and normalize it to 3840 x 2160.
    """

    rect = order_points(points)

    destination = np.array([
        [0, 0],
        [TARGET_WIDTH - 1, 0],
        [TARGET_WIDTH - 1, TARGET_HEIGHT - 1],
        [0, TARGET_HEIGHT - 1]
    ], dtype=np.float32)

    matrix = cv2.getPerspectiveTransform(
        rect,
        destination
    )

    corrected = cv2.warpPerspective(
        image,
        matrix,
        (TARGET_WIDTH, TARGET_HEIGHT)
    )

    return corrected


def detect_artifact(image):
    """
    Detect the large rectangular image displayed
    on the laptop screen.
    """

    gray = cv2.cvtColor(
        image,
        cv2.COLOR_BGR2GRAY
    )

    # Slight blur removes camera noise
    blurred = cv2.GaussianBlur(
        gray,
        (7, 7),
        0
    )

    # Edge detection
    edges = cv2.Canny(
        blurred,
        20,
        100
    )

    # Join broken edges
    kernel = cv2.getStructuringElement(
        cv2.MORPH_RECT,
        (15, 15)
    )

    edges = cv2.morphologyEx(
        edges,
        cv2.MORPH_CLOSE,
        kernel
    )

    # Dilate slightly so the border becomes continuous
    edges = cv2.dilate(
        edges,
        np.ones((5, 5), np.uint8),
        iterations=1
    )

    contours, _ = cv2.findContours(
        edges,
        cv2.RETR_EXTERNAL,
        cv2.CHAIN_APPROX_SIMPLE
    )

    image_area = image.shape[0] * image.shape[1]

    candidates = []

    for contour in contours:

        area = cv2.contourArea(contour)

        # Ignore small regions
        if area < image_area * 0.15:
            continue

        rectangle = cv2.minAreaRect(contour)

        width, height = rectangle[1]

        if width <= 0 or height <= 0:
            continue

        # Normalize orientation
        aspect_ratio = max(width, height) / min(width, height)

        # Our artifact is approximately 16:9
        if not (1.4 <= aspect_ratio <= 2.1):
            continue

        rectangle_area = width * height

        rectangularity = area / rectangle_area

        # Reject very irregular contours
        if rectangularity < 0.45:
            continue

        box = cv2.boxPoints(rectangle)

        box = np.array(
            box,
            dtype=np.float32
        )

        candidates.append(
            (
                area,
                box
            )
        )

    # If candidates were found, use the largest
    if candidates:

        candidates.sort(
            key=lambda x: x[0],
            reverse=True
        )

        return candidates[0][1]

    # --------------------------------------------------
    # Fallback detector
    # --------------------------------------------------
    # Use brightness threshold because the displayed
    # image is surrounded by a relatively dark border.
    # --------------------------------------------------

    _, threshold = cv2.threshold(
        gray,
        20,
        255,
        cv2.THRESH_BINARY
    )

    threshold = cv2.morphologyEx(
        threshold,
        cv2.MORPH_CLOSE,
        kernel
    )

    contours, _ = cv2.findContours(
        threshold,
        cv2.RETR_EXTERNAL,
        cv2.CHAIN_APPROX_SIMPLE
    )

    candidates = []

    for contour in contours:

        area = cv2.contourArea(contour)

        if area < image_area * 0.20:
            continue

        rectangle = cv2.minAreaRect(contour)

        width, height = rectangle[1]

        if width <= 0 or height <= 0:
            continue

        aspect_ratio = max(width, height) / min(width, height)

        if not (1.4 <= aspect_ratio <= 2.1):
            continue

        box = cv2.boxPoints(rectangle)

        box = np.array(
            box,
            dtype=np.float32
        )

        candidates.append(
            (
                area,
                box
            )
        )

    if candidates:

        candidates.sort(
            key=lambda x: x[0],
            reverse=True
        )

        return candidates[0][1]

    return None


def preprocess_photo(image):
    """
    Full physical-photo preprocessing:

        Phone photograph
              ↓
        Artifact detection
              ↓
        Four corner estimation
              ↓
        Perspective correction
              ↓
        3840 x 2160 normalization
    """

    if image is None:
        raise ValueError(
            "Input image is None"
        )

    corners = detect_artifact(image)

    if corners is None:
        raise ValueError(
            "Could not detect the watermarked artifact."
        )

    corrected = four_point_transform(
        image,
        corners
    )

    return corrected