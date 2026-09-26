import cv2
import numpy as np
import pywt


COEFFICIENT_OFFSET = 128
REPETITIONS = 5


def bytes_to_bits(data):
    """Convert bytes to MSB-first bits."""
    return [
        (byte >> bit) & 1
        for byte in data
        for bit in range(7, -1, -1)
    ]


def embed_watermark(image, payload, alpha=20.0):
    """
    Embed payload into HL/LH DWT coefficients.

    Each bit is repeated multiple times to improve
    robustness against physical photo distortion.
    """

    if not isinstance(payload, bytes):
        raise TypeError("payload must be bytes")

    # BGR -> YCrCb
    ycrcb = cv2.cvtColor(
        image,
        cv2.COLOR_BGR2YCrCb
    )

    # Luminance
    y_channel = ycrcb[:, :, 0].astype(
        np.float32
    )

    # 2D Haar DWT
    LL, (LH, HL, HH) = pywt.dwt2(
        y_channel,
        "haar"
    )

    # Payload -> bits
    bits = bytes_to_bits(payload)

    # Repeat each bit
    repeated_bits = []

    for bit in bits:
        repeated_bits.extend(
            [bit] * REPETITIONS
        )

    # Combine HL + LH
    coefficients = np.concatenate([
        HL.flatten(),
        LH.flatten()
    ])

    required = (
        COEFFICIENT_OFFSET
        + len(repeated_bits)
    )

    if required > len(coefficients):
        raise ValueError(
            "Payload too large for image."
        )

    target = coefficients[
        COEFFICIENT_OFFSET:
    ]

    # Embed
    for i, bit in enumerate(
        repeated_bits
    ):

        coefficient = target[i]

        base = (
            np.floor(
                coefficient / alpha
            ) * alpha
        )

        if bit == 1:
            target[i] = (
                base + 0.75 * alpha
            )
        else:
            target[i] = (
                base + 0.25 * alpha
            )

    # Restore
    coefficients[
        COEFFICIENT_OFFSET:
    ] = target

    hl_size = HL.size

    HL = coefficients[
        :hl_size
    ].reshape(HL.shape)

    LH = coefficients[
        hl_size:
    ].reshape(LH.shape)

    # Inverse DWT
    watermarked_y = pywt.idwt2(
        (LL, (LH, HL, HH)),
        "haar"
    )

    watermarked_y = watermarked_y[
        :y_channel.shape[0],
        :y_channel.shape[1]
    ]

    # Replace luminance
    ycrcb[:, :, 0] = np.clip(
        watermarked_y,
        0,
        255
    ).astype(np.uint8)

    # YCrCb -> BGR
    watermarked = cv2.cvtColor(
        ycrcb,
        cv2.COLOR_YCrCb2BGR
    )

    return watermarked