import io
import base64
import logging
from typing import Optional
import numpy as np
import cv2
from PIL import Image, ImageDraw, ImageFont

from backend.watermark_interface.wid import WatermarkIDService
from ml.embed import embed_watermark, EMBED_W, EMBED_H, ALPHA as DEFAULT_ALPHA
from ml.extract import extract_watermark, extract_from_photo
from ml.preprocessing.photo import preprocess_photo
from QuantumCrypto.fec_engine import FECStegoEngine

logger = logging.getLogger("ASTRAEA.DWTWatermark")


class DWTWatermarkEngine:
    """
    Unified 2D Haar Discrete Wavelet Transform (DWT) Steganographic Watermarking
    and Digital Forensics Engine (integrating ronak_ml_cv pipeline).
    
    Uses Level-2 Differential Pair DWT Modulation with Reed-Solomon Error Correction,
    Resolution Matching (1600x900), and OpenCV Physical Photo Perspective Deskewing.
    """

    def __init__(self, alpha: float = DEFAULT_ALPHA):
        self.alpha = float(alpha)  # Default ALPHA = 32.0 from ml.embed
        self.wid_service = WatermarkIDService()
        self.fec = FECStegoEngine()

    def embed_wid_in_image(self, base_image_np: np.ndarray, wid_hex: str) -> np.ndarray:
        """
        Embeds 256-bit W_ID into image using Level-2 Differential Pair DWT (from ml.embed).
        """
        fec_bytes = self.fec.encode_wid_for_dwt(wid_hex)
        return embed_watermark(base_image_np, fec_bytes, alpha=self.alpha, return_display=True)

    def extract_wid_from_image(
        self,
        img_np: np.ndarray,
        total_fec_bytes: int = 50,
        reference_np: Optional[np.ndarray] = None
    ) -> str:
        """
        Extracts embedded W_ID from an image or leaked smartphone photograph (from ml.extract & ml.preprocessing).
        Applies multi-stage detection:
          1. Direct Level-2 DWT extraction (optimal for screenshots / digital exports)
          2. Physical photo preprocessing (OpenCV contour detection & 4-point perspective warp)
          3. Sub-pixel feature homography alignment against reference (if available)
        Returns: Recovered 64-character hex W_ID string.
        """
        if img_np is None or img_np.size == 0:
            return ""

        # Stage 1: Direct extraction (fastest, lossless on digital captures / screenshots)
        try:
            raw_payload = extract_watermark(img_np, payload_size=total_fec_bytes, alpha=self.alpha)
            wid_hex = self.fec.decode_wid_from_dwt(raw_payload)
            if wid_hex and len(wid_hex) == 64:
                logger.info(f"DWT Extraction succeeded via Stage 1 (Direct): {wid_hex[:16]}...")
                return wid_hex
        except Exception as e:
            logger.debug(f"Direct extraction stage bypassed: {e}")

        # Stage 2: Physical photo preprocessing pipeline (from ronak_ml_cv)
        try:
            raw_payload = extract_from_photo(img_np, payload_size=total_fec_bytes, alpha=self.alpha)
            wid_hex = self.fec.decode_wid_from_dwt(raw_payload)
            if wid_hex and len(wid_hex) == 64:
                logger.info(f"DWT Extraction succeeded via Stage 2 (Physical photo pipeline): {wid_hex[:16]}...")
                return wid_hex
        except Exception as e:
            logger.debug(f"Photo pipeline extraction bypassed: {e}")

        # Stage 3: Guided sub-pixel homography alignment (if reference image is provided)
        if reference_np is not None:
            try:
                preprocessed = preprocess_photo(img_np, reference=reference_np)
                ext_img = cv2.resize(preprocessed, (EMBED_W, EMBED_H), interpolation=cv2.INTER_AREA)
                raw_payload = extract_watermark(ext_img, payload_size=total_fec_bytes, alpha=self.alpha)
                wid_hex = self.fec.decode_wid_from_dwt(raw_payload)
                if wid_hex and len(wid_hex) == 64:
                    logger.info(f"DWT Extraction succeeded via Stage 3 (Guided alignment): {wid_hex[:16]}...")
                    return wid_hex
            except Exception as e:
                logger.debug(f"Guided alignment extraction bypassed: {e}")

        logger.warning("All DWT extraction stages exhausted; unable to decode W_ID.")
        return ""

    def create_watermarked_document_image(
        self,
        title: str,
        classification: str,
        text_content: str,
        wid_hex: str
    ) -> str:
        """
        Renders document text onto a 1600x900 canvas, embeds Level-2 DWT W_ID watermark,
        and returns base64 PNG string for secure viewer presentation.
        """
        width, height = EMBED_W, EMBED_H  # 1600 x 900
        img = Image.new("RGB", (width, height), color=(248, 249, 250))
        draw = ImageDraw.Draw(img)

        # Header banner
        header_color = (
            (185, 28, 28) if classification == "RESTRICTED"
            else ((217, 119, 6) if classification == "CONFIDENTIAL"
            else (30, 41, 59))
        )
        draw.rectangle([0, 0, width, 80], fill=header_color)
        draw.text(
            (40, 26),
            f"[{classification}] ASTRAEA QUANTUM SECURE PROVENANCE SYSTEM",
            fill=(255, 255, 255)
        )

        # Title and header divider
        draw.text((50, 115), f"DOCUMENT: {title}", fill=(20, 20, 20))
        draw.line([(50, 155), (width - 50, 155)], fill=(200, 200, 200), width=2)

        # Text lines
        lines = text_content.split("\n")
        y_offset = 185
        for line in lines:
            draw.text((50, y_offset), line, fill=(35, 35, 35))
            y_offset += 32

        # Subtle forensic footer
        draw.text(
            (50, height - 45),
            f"W_ID: {wid_hex[:16]}... (2D HAAR DWT FORENSICALLY EMBEDDED)",
            fill=(180, 180, 180)
        )

        # Convert to numpy array (BGR)
        np_img = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)

        # Embed Level-2 DWT watermark
        watermarked_np = self.embed_wid_in_image(np_img, wid_hex)

        # Encode to Base64 PNG
        _, buffer = cv2.imencode(".png", watermarked_np)
        base64_str = base64.b64encode(buffer).decode("utf-8")
        return f"data:image/png;base64,{base64_str}"
