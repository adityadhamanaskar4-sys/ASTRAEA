import cv2
import numpy as np
import pywt


COEFFICIENT_OFFSET = 128
REPETITIONS = 5


def bits_to_bytes(bits):
    """Convert MSB-first bits into bytes."""

    output = bytearray()

    for i in range(
        0,
        len(bits),
        8
    ):

        chunk = bits[i:i + 8]

        if len(chunk) < 8:
            break

        value = 0

        for bit in chunk:
            value = (
                value << 1
            ) | bit

        output.append(value)

    return bytes(output)


def extract_watermark(
    image,
    payload_size=50,
    alpha=20.0
):
    """
    Extract payload from HL/LH DWT coefficients.

    Repeated bits are recovered using majority voting.
    """

    # BGR -> YCrCb
    ycrcb = cv2.cvtColor(
        image,
        cv2.COLOR_BGR2YCrCb
    )

    # Luminance
    y_channel = ycrcb[:, :, 0].astype(
        np.float32
    )

    # DWT
    LL, (LH, HL, HH) = pywt.dwt2(
        y_channel,
        "haar"
    )

    # Same coefficient order
    coefficients = np.concatenate([
        HL.flatten(),
        LH.flatten()
    ])

    total_bits = (
        payload_size * 8
    )

    required = (
        COEFFICIENT_OFFSET
        + total_bits * REPETITIONS
    )

    if required > len(coefficients):
        raise ValueError(
            "Payload too large for image."
        )

    recovered_bits = []

    for bit_index in range(
        total_bits
    ):

        votes = []

        for repetition in range(
            REPETITIONS
        ):

            coefficient_index = (
                COEFFICIENT_OFFSET
                + bit_index * REPETITIONS
                + repetition
            )

            coefficient = coefficients[
                coefficient_index
            ]

            remainder = (
                coefficient % alpha
            )

            distance_to_0 = abs(
                remainder
                - 0.25 * alpha
            )

            distance_to_1 = abs(
                remainder
                - 0.75 * alpha
            )

            if distance_to_1 < distance_to_0:
                votes.append(1)
            else:
                votes.append(0)

        # Majority vote
        recovered_bit = (
            1
            if sum(votes) >= 3
            else 0
        )

        recovered_bits.append(
            recovered_bit
        )

    return bits_to_bytes(
        recovered_bits
    )