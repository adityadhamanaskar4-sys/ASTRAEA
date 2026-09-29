import cv2
import numpy as np
import pywt


# -------------------------------------------------------------------
# ASTRAEA DWT Embedding Engine — Level-2 Differential Pair DWT
#
# Key Design Architecture:
# =========================
# 1. Resolution Matching:
#    Embeds payload into a 1600 × 900 effective capture grid, then
#    upscales using cv2.INTER_LANCZOS4 for 4K screen rendering.
#
# 2. Pairwise Differential DWT (Camera Exposure Invariance):
#    Instead of quantising absolute coefficient values (which shift
#    under camera auto-exposure, contrast gain, and lighting),
#    bits are embedded into the DIFFERENCE between adjacent coefficient
#    pairs (c1, c2):
#      - bit == 1 : (c1 - c2) > +ALPHA
#      - bit == 0 : (c1 - c2) < -ALPHA
#    This relative sign relationship is 100% invariant to camera
#    brightness, contrast, and gamma shifts!
# -------------------------------------------------------------------

EMBED_W = 1600
EMBED_H = 900

ALPHA = 32.0
REPETITIONS = 7
COEFFICIENT_OFFSET = 64


def bytes_to_bits(data: bytes) -> list:
    """Convert bytes to MSB-first bit list."""
    return [
        (byte >> bit) & 1
        for byte in data
        for bit in range(7, -1, -1)
    ]


def embed_watermark(
    image: np.ndarray,
    payload: bytes,
    alpha: float = ALPHA,
    return_display: bool = True
) -> np.ndarray:
    """
    Embed payload bytes into Level-2 DWT HL2/LH2 coefficient pairs.

    Parameters
    ----------
    image          : BGR image as numpy array (any resolution)
    payload        : raw bytes to embed (up to 50 bytes)
    alpha          : differential step size (default ALPHA = 32.0)
    return_display : if True, return upscaled image for display rendering;
                     if False, return 1600x900 embedded image.

    Returns
    -------
    watermarked BGR image
    """

    if not isinstance(payload, (bytes, bytearray)):
        raise TypeError("payload must be bytes or bytearray")

    original_h, original_w = image.shape[:2]

    # Downscale to embed resolution
    small = cv2.resize(image, (EMBED_W, EMBED_H), interpolation=cv2.INTER_AREA)

    # BGR → YCrCb → luminance
    ycrcb = cv2.cvtColor(small, cv2.COLOR_BGR2YCrCb)
    y = ycrcb[:, :, 0].astype(np.float64)

    # Level-1 Haar DWT
    LL1, (LH1, HL1, HH1) = pywt.dwt2(y, "haar")

    # Level-2 Haar DWT on LL1
    LL2, (LH2, HL2, HH2) = pywt.dwt2(LL1, "haar")

    # Payload → repeated bits
    bits = bytes_to_bits(payload)
    repeated_bits = []
    for bit in bits:
        repeated_bits.extend([bit] * REPETITIONS)

    # Combine HL2 + LH2 coefficient arrays
    coeffs = np.concatenate([HL2.flatten(), LH2.flatten()])

    required_coeffs = COEFFICIENT_OFFSET + len(repeated_bits) * 2
    if required_coeffs > len(coeffs):
        raise ValueError(
            f"Payload too large. Need {required_coeffs} coefficients, have {len(coeffs)}."
        )

    # Differential Pair Embedding: (c1, c2)
    for i, bit in enumerate(repeated_bits):
        idx1 = COEFFICIENT_OFFSET + 2 * i
        idx2 = COEFFICIENT_OFFSET + 2 * i + 1

        c1, c2 = coeffs[idx1], coeffs[idx2]
        avg = (c1 + c2) / 2.0

        if bit == 1:
            coeffs[idx1] = avg + alpha / 2.0
            coeffs[idx2] = avg - alpha / 2.0
        else:
            coeffs[idx1] = avg - alpha / 2.0
            coeffs[idx2] = avg + alpha / 2.0

    # Restore modified HL2 and LH2
    hl2_size = HL2.size
    HL2_mod = coeffs[:hl2_size].reshape(HL2.shape)
    LH2_mod = coeffs[hl2_size:].reshape(LH2.shape)

    # Inverse Level-2 DWT → reconstruct LL1
    LL1_mod = pywt.idwt2((LL2, (LH2_mod, HL2_mod, HH2)), "haar")
    LL1_mod = LL1_mod[:LL1.shape[0], :LL1.shape[1]]

    # Inverse Level-1 DWT → reconstruct Y channel
    y_watermarked = pywt.idwt2((LL1_mod, (LH1, HL1, HH1)), "haar")
    y_watermarked = y_watermarked[:y.shape[0], :y.shape[1]]

    # Reconstruct small watermarked image
    ycrcb[:, :, 0] = np.clip(y_watermarked, 0, 255).astype(np.uint8)
    watermarked_small = cv2.cvtColor(ycrcb, cv2.COLOR_YCrCb2BGR)

    if return_display:
        return cv2.resize(
            watermarked_small,
            (original_w, original_h),
            interpolation=cv2.INTER_LANCZOS4
        )
    else:
        return watermarked_small