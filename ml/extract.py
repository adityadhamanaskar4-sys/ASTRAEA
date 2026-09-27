import cv2
import numpy as np
import pywt


# -------------------------------------------------------------------
# ASTRAEA DWT Extraction Engine — Level-2 Differential Pair DWT
#
# Must mirror embed.py exactly.
# Extract bits by evaluating differential sign (c1 - c2 > 0).
# -------------------------------------------------------------------

EMBED_W = 1600
EMBED_H = 900

ALPHA = 32.0
REPETITIONS = 7
COEFFICIENT_OFFSET = 64


def bits_to_bytes(bits: list) -> bytes:
    """Convert MSB-first bit list to bytes."""
    output = bytearray()
    for i in range(0, len(bits), 8):
        chunk = bits[i:i + 8]
        if len(chunk) < 8:
            break
        value = 0
        for bit in chunk:
            value = (value << 1) | bit
        output.append(value)
    return bytes(output)


def extract_watermark(
    image: np.ndarray,
    payload_size: int = 50,
    alpha: float = ALPHA
) -> bytes:
    """
    Extract payload from Level-2 DWT HL2/LH2 coefficient pairs.

    Parameters
    ----------
    image        : BGR image (any resolution, auto-resizes to 1600x900)
    payload_size : number of bytes to recover (default 50)
    alpha        : threshold parameter

    Returns
    -------
    Recovered raw payload bytes
    """

    if image.shape[1] != EMBED_W or image.shape[0] != EMBED_H:
        image = cv2.resize(image, (EMBED_W, EMBED_H), interpolation=cv2.INTER_AREA)

    # BGR → YCrCb → Y
    ycrcb = cv2.cvtColor(image, cv2.COLOR_BGR2YCrCb)
    y = ycrcb[:, :, 0].astype(np.float64)

    # Level-1 Haar DWT
    LL1, (LH1, HL1, HH1) = pywt.dwt2(y, "haar")

    # Level-2 Haar DWT on LL1
    LL2, (LH2, HL2, HH2) = pywt.dwt2(LL1, "haar")

    coeffs = np.concatenate([HL2.flatten(), LH2.flatten()])

    total_bits = payload_size * 8
    recovered_bits = []

    for bit_index in range(total_bits):
        votes = []
        for rep in range(REPETITIONS):
            global_rep_idx = bit_index * REPETITIONS + rep
            idx1 = COEFFICIENT_OFFSET + 2 * global_rep_idx
            idx2 = COEFFICIENT_OFFSET + 2 * global_rep_idx + 1

            diff = coeffs[idx1] - coeffs[idx2]
            votes.append(1 if diff > 0 else 0)

        # Majority voting across 7 redundancy votes
        threshold = REPETITIONS // 2 + 1
        recovered_bits.append(1 if sum(votes) >= threshold else 0)

    return bits_to_bytes(recovered_bits)


def extract_from_photo(
    photo: np.ndarray,
    payload_size: int = 50,
    alpha: float = ALPHA
) -> bytes:
    """
    Full physical-photo extraction pipeline.

    Primary API entry point for backend.
    """
    from ml.preprocessing.photo import preprocess_photo

    preprocessed = preprocess_photo(photo)
    extract_img = cv2.resize(preprocessed, (EMBED_W, EMBED_H), interpolation=cv2.INTER_AREA)

    return extract_watermark(extract_img, payload_size, alpha)