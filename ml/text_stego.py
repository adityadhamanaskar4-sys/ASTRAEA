"""
ASTRAEA Text Watermark / Forensic W_ID Steganography

Embeds the same 256-bit W_ID used by the visual watermark into
decrypted text using zero-width Unicode characters.

Visible text is preserved.

Encoding:
    0 -> U+200B ZERO WIDTH SPACE
    1 -> U+200C ZERO WIDTH NON-JOINER

The watermark is framed with:
    START marker
    VERSION
    256-bit W_ID
    CHECKSUM
    END marker

This is intentionally independent from the DWT watermarking system.
Both channels carry the same W_ID.
"""

import hashlib
import re


# ---------------------------------------------------------------------
# Zero-width characters
# ---------------------------------------------------------------------

ZERO = "\u200b"   # U+200B ZERO WIDTH SPACE
ONE = "\u200c"    # U+200C ZERO WIDTH NON-JOINER

# Additional characters are deliberately NOT used for the payload.
# This keeps the implementation simple and robust.

START_MARKER = "\u2060\u2060"   # WORD JOINER x2
END_MARKER = "\u2061\u2061"     # FUNCTION APPLICATION x2

VERSION = "01"

WID_BYTES = 32
WID_HEX_LENGTH = 64


# ---------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------

def _validate_wid(wid_hex: str) -> str:
    """
    Validate and normalize a 256-bit W_ID.

    Returns lowercase 64-character hexadecimal string.
    """

    if not isinstance(wid_hex, str):
        raise TypeError("W_ID must be a hexadecimal string.")

    wid_hex = wid_hex.strip().lower()

    if len(wid_hex) != WID_HEX_LENGTH:
        raise ValueError(
            "W_ID must be exactly 256 bits / 32 bytes / 64 hex characters."
        )

    if not re.fullmatch(r"[0-9a-f]{64}", wid_hex):
        raise ValueError(
            "W_ID must contain only hexadecimal characters."
        )

    return wid_hex


# ---------------------------------------------------------------------
# Bit conversion
# ---------------------------------------------------------------------

def _hex_to_bits(wid_hex: str) -> str:
    """
    Convert 64-character hexadecimal W_ID to 256-bit binary string.
    """

    wid_bytes = bytes.fromhex(wid_hex)

    return "".join(
        f"{byte:08b}"
        for byte in wid_bytes
    )


def _bits_to_hex(bits: str) -> str:
    """
    Convert 256-bit binary string back to hexadecimal W_ID.
    """

    if len(bits) != 256:
        raise ValueError(
            f"Expected 256 W_ID bits, received {len(bits)}."
        )

    output = bytearray()

    for i in range(0, len(bits), 8):
        output.append(int(bits[i:i + 8], 2))

    return bytes(output).hex()


# ---------------------------------------------------------------------
# Checksum
# ---------------------------------------------------------------------

def _checksum(wid_hex: str) -> str:
    """
    Short checksum used to detect accidental/corrupt extraction.

    SHA-256 is used only as an integrity check here.
    It is NOT the W_ID derivation mechanism.
    """

    digest = hashlib.sha256(
        bytes.fromhex(wid_hex)
    ).hexdigest()

    # 16 hex characters = 64 bits
    return digest[:16]


# ---------------------------------------------------------------------
# Watermark construction
# ---------------------------------------------------------------------

def _build_payload(wid_hex: str) -> str:
    """
    Build the textual zero-width payload.

    Layout:

        START_MARKER
        VERSION
        W_ID (256 bits)
        CHECKSUM (64 bits)
        END_MARKER
    """

    wid_hex = _validate_wid(wid_hex)

    wid_bits = _hex_to_bits(wid_hex)

    checksum_hex = _checksum(wid_hex)
    checksum_bits = _hex_to_bits(
        checksum_hex + ("0" * 48)
    )[:64]

    bits = wid_bits + checksum_bits

    encoded_bits = "".join(
        ZERO if bit == "0" else ONE
        for bit in bits
    )

    return (
        START_MARKER
        + VERSION
        + encoded_bits
        + END_MARKER
    )


# ---------------------------------------------------------------------
# Embed
# ---------------------------------------------------------------------

def embed_wid_in_text(text: str, wid_hex: str) -> str:
    """
    Invisibly embed a 256-bit W_ID into text.

    Parameters
    ----------
    text:
        Plain/decrypted text.

    wid_hex:
        64-character hexadecimal W_ID.

    Returns
    -------
    str
        Same visible text with invisible watermark appended.

    Important:
        The visible characters of the original text are unchanged.
    """

    if not isinstance(text, str):
        raise TypeError("text must be a string.")

    payload = _build_payload(wid_hex)

    # Put the watermark at the END of the plaintext.
    #
    # This avoids modifying the actual visible content and makes
    # extraction deterministic.
    return text + payload


# ---------------------------------------------------------------------
# Extract
# ---------------------------------------------------------------------

def extract_wid_from_text(text: str) -> str:
    """
    Extract and validate the W_ID from watermarked text.

    Raises
    ------
    ValueError
        If the watermark is missing, malformed, or corrupted.

    Returns
    -------
    str
        64-character lowercase hexadecimal W_ID.
    """

    if not isinstance(text, str):
        raise TypeError("text must be a string.")

    start = text.rfind(START_MARKER)

    if start == -1:
        raise ValueError(
            "ASTRAEA text watermark not found."
        )

    end = text.find(
        END_MARKER,
        start + len(START_MARKER)
    )

    if end == -1:
        raise ValueError(
            "ASTRAEA text watermark is incomplete."
        )

    # Everything between START and END
    payload = text[
        start + len(START_MARKER):end
    ]

    # VERSION is currently two visible characters: "01"
    if not payload.startswith(VERSION):
        raise ValueError(
            "Unsupported ASTRAEA text watermark version."
        )

    encoded = payload[len(VERSION):]

    # Expected:
    # 256 W_ID bits + 64 checksum bits
    expected_length = 256 + 64

    if len(encoded) != expected_length:
        raise ValueError(
            "ASTRAEA text watermark has invalid payload length."
        )

    # Decode zero-width characters
    bits = []

    for char in encoded:

        if char == ZERO:
            bits.append("0")

        elif char == ONE:
            bits.append("1")

        else:
            raise ValueError(
                "ASTRAEA text watermark contains invalid characters."
            )

    bits = "".join(bits)

    # First 256 bits = W_ID
    wid_bits = bits[:256]

    # Remaining 64 bits = checksum
    checksum_bits = bits[256:]

    wid_hex = _bits_to_hex(wid_bits)

    expected_checksum = _checksum(wid_hex)

    expected_checksum_bits = _hex_to_bits(
        expected_checksum + ("0" * 48)
    )[:64]

    if checksum_bits != expected_checksum_bits:
        raise ValueError(
            "ASTRAEA text watermark checksum verification failed."
        )

    return wid_hex


# ---------------------------------------------------------------------
# Visible-text verification
# ---------------------------------------------------------------------

def visible_text(text: str) -> str:
    """
    Remove Unicode formatting/invisible characters.

    Useful for proving that watermarking did not change visible text.
    """

    return "".join(
        char
        for char in text
        if not (
            0x200B <= ord(char) <= 0x200F
            or 0x2060 <= ord(char) <= 0x206F
        )
    )


# ---------------------------------------------------------------------
# Self-test
# ---------------------------------------------------------------------

if __name__ == "__main__":

    test_text = (
        "ASTRAEA confidential forensic document.\n"
        "This is the decrypted plaintext that will be delivered."
    )

    test_wid = (
        "5a4fdbc8fda6112d529b717c43be5d5e"
        "124dc95276847e6de729d9247516d645"
    )

    watermarked = embed_wid_in_text(
        test_text,
        test_wid
    )

    recovered = extract_wid_from_text(
        watermarked
    )

    print("Original W_ID :", test_wid)
    print("Recovered W_ID:", recovered)
    print("W_ID MATCH    :", test_wid == recovered)

    print(
        "VISIBLE TEXT MATCH:",
        visible_text(watermarked) == test_text
    )
