import cv2
import sys

sys.path.insert(0, ".")

from QuantumCrypto.fec_engine import FECStegoEngine
from ml.embed import embed_watermark


def generate_display_artifact(
    wid_hex: str = "a1b2c3d4e5f67890123456789abcdef0123456789abcdef0123456789abcdef0",
    output_path: str = "ml/evaluation/watermarked_for_display.jpg",
):
    print(f"Generating Watermarked Artifact for W_ID: {wid_hex[:16]}...")

    fec = FECStegoEngine()
    protected_payload = bytes(fec.encode_wid_for_dwt(wid_hex))

    img = cv2.imread("ml/evaluation/test_image.jpg")
    watermarked = embed_watermark(img, protected_payload, return_display=True)

    cv2.imwrite(output_path, watermarked)
    print(f"[OK] Successfully saved watermarked display image to: {output_path}")


if __name__ == "__main__":
    generate_display_artifact()
