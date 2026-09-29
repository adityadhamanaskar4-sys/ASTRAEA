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
    Detect the rectangular image displayed
    on the laptop screen.
    """

    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (7, 7), 0)
    edges = cv2.Canny(blurred, 20, 100)

    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (15, 15))
    edges = cv2.morphologyEx(edges, cv2.MORPH_CLOSE, kernel)
    edges = cv2.dilate(edges, np.ones((5, 5), np.uint8), iterations=1)

    contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    image_area = image.shape[0] * image.shape[1]

    candidates = []

    for contour in contours:
        area = cv2.contourArea(contour)
        if area < image_area * 0.15:
            continue

        rectangle = cv2.minAreaRect(contour)
        width, height = rectangle[1]

        if width <= 0 or height <= 0:
            continue

        aspect_ratio = max(width, height) / min(width, height)
        if not (1.3 <= aspect_ratio <= 2.2):
            continue

        rectangle_area = width * height
        rectangularity = area / rectangle_area

        if rectangularity < 0.40:
            continue

        box = cv2.boxPoints(rectangle)
        candidates.append((area, np.array(box, dtype=np.float32)))

    if candidates:
        candidates.sort(key=lambda x: x[0], reverse=True)
        return candidates[0][1]

    # Brightness threshold fallback
    _, threshold = cv2.threshold(gray, 20, 255, cv2.THRESH_BINARY)
    threshold = cv2.morphologyEx(threshold, cv2.MORPH_CLOSE, kernel)
    contours, _ = cv2.findContours(threshold, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    candidates = []
    for contour in contours:
        area = cv2.contourArea(contour)
        if area < image_area * 0.15:
            continue

        rectangle = cv2.minAreaRect(contour)
        width, height = rectangle[1]
        if width <= 0 or height <= 0:
            continue

        aspect_ratio = max(width, height) / min(width, height)
        if not (1.3 <= aspect_ratio <= 2.2):
            continue

        box = cv2.boxPoints(rectangle)
        candidates.append((area, np.array(box, dtype=np.float32)))

    if candidates:
        candidates.sort(key=lambda x: x[0], reverse=True)
        return candidates[0][1]

    return None


def align_with_reference(photo: np.ndarray, reference: np.ndarray) -> np.ndarray:
    """
    Sub-pixel alignment of phone photograph using ORB feature homography
    against the reference document image.
    """
    orb = cv2.ORB_create(3000)
    kp1, des1 = orb.detectAndCompute(photo, None)
    kp2, des2 = orb.detectAndCompute(reference, None)

    if des1 is None or des2 is None or len(des1) < 10 or len(des2) < 10:
        return photo

    bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True)
    matches = sorted(bf.match(des1, des2), key=lambda x: x.distance)

    if len(matches) < 10:
        return photo

    src_pts = np.float32([kp1[m.queryIdx].pt for m in matches[:150]]).reshape(-1, 1, 2)
    dst_pts = np.float32([kp2[m.trainIdx].pt for m in matches[:150]]).reshape(-1, 1, 2)

    H, mask = cv2.findHomography(src_pts, dst_pts, cv2.RANSAC, 2.0)
    if H is None:
        return photo

    h, w = reference.shape[:2]
    unwarped = cv2.warpPerspective(photo, H, (w, h))
    return unwarped


def preprocess_photo(image: np.ndarray, reference: np.ndarray = None) -> np.ndarray:
    """
    Full physical-photo preprocessing pipeline:

        Phone photograph
              ↓
        Sub-pixel ORB Homography Alignment (if reference provided)
              ↓ OR (if no reference)
        Contour Artifact Detection & 4-Point Perspective Warp
              ↓
        Normalized 3840 × 2160 Output
    """

    if image is None:
        raise ValueError("Input image is None")

    if reference is not None:
        try:
            return align_with_reference(image, reference)
        except Exception:
            pass

    corners = detect_artifact(image)

    if corners is None:
        # Fallback to direct resize if detection fails on close-up photos
        return cv2.resize(image, (TARGET_WIDTH, TARGET_HEIGHT), interpolation=cv2.INTER_CUBIC)

    return four_point_transform(image, corners)