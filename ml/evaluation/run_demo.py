import sys
import os
import cv2
import numpy as np

sys.path.insert(0, ".")

from ml.embed import embed_watermark
from ml.extract import extract_from_photo
from ml.preprocessing.photo import preprocess_photo
from QuantumCrypto.fec_engine import FECStegoEngine


def run_full_forensic_demo(photo_path: str, reference_path: str = "ml/evaluation/watermarked_for_display.jpg"):
    print("=" * 70)
    print("      ASTRAEA — Forensic Watermark Extraction & Attribution Demo")
    print("=" * 70)

    if not os.path.exists(photo_path):
        print(f"Error: Photo path '{photo_path}' does not exist.")
        return

    print(f"[1/4] Loading leaked photograph: {photo_path}")
    photo = cv2.imread(photo_path)
    print(f"      Resolution: {photo.shape[1]} x {photo.shape[0]} px")

    reference = None
    if reference_path and os.path.exists(reference_path):
        reference = cv2.imread(reference_path)
        print(f"[2/4] Guided sub-pixel homography alignment active.")

    print(f"[3/4] Running DWT extraction engine...")
    preprocessed = preprocess_photo(photo, reference=reference)

    from ml.extract import extract_watermark, EMBED_W, EMBED_H
    ext_img = cv2.resize(preprocessed, (EMBED_W, EMBED_H), interpolation=cv2.INTER_AREA)
    extracted_payload = extract_watermark(ext_img, payload_size=50)

    print(f"      Raw extracted payload ({len(extracted_payload)} bytes):")
    print(f"      {extracted_payload.hex()}")

    print(f"[4/4] Executing Reed-Solomon Forward Error Correction (FEC)...")
    fec = FECStegoEngine()

    try:
        recovered_wid_hex = fec.decode_wid_from_dwt(extracted_payload)
        print("\n" + "=" * 70)
        print("  [SUCCESS] FORENSIC ATTRIBUTION SUCCESSFUL!")
        print(f"  Recovered Cryptographic Identifier (W_ID*): {recovered_wid_hex}")
        print("=" * 70)
    except Exception as e:
        print("\n" + "=" * 70)
        print("  [INFO] Raw payload recovered, decoding info:", e)
        print("=" * 70)


if __name__ == "__main__":
    if len(sys.argv) > 1:
        run_full_forensic_demo(sys.argv[1])
    else:
        # Default test photo
        run_full_forensic_demo("ml/evaluation/testthisimage.jpeg")
