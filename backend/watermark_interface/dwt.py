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

    @staticmethod
    def render_security_document_canvas(
        title: str,
        classification: str,
        text_content: str,
        wid_hex: Optional[str] = None
    ) -> np.ndarray:
        """
        Renders an ultra-high-fidelity security document format optimized for maximum bit extraction:
        1. Non-saturating paper luminance (236, 236, 236) and dark text (25, 25, 25) prevent
           saturation clipping at 0 and 255, preserving 100% of DWT differential perturbations (+/- 16).
        2. Corner Registration L-Brackets and heavy outer frame (8px) provide sub-pixel accuracy
           for OpenCV 4-corner perspective unwarping under camera skew.
        3. Subtle security micro-grid underlay prevents JPEG quantization from zeroing flat regions.
        """
        width, height = EMBED_W, EMBED_H  # 1600 x 900
        img = Image.new("RGB", (width, height), color=(236, 236, 236))
        draw = ImageDraw.Draw(img)

        # 1. Security micro-grid underlay (every 24px) for rich wavelet energy across HL2/LH2 subbands
        for x in range(24, width - 24, 24):
            draw.line([(x, 24), (x, height - 24)], fill=(230, 230, 230), width=1)
        for y in range(24, height - 24, 24):
            draw.line([(24, y), (width - 24, y)], fill=(230, 230, 230), width=1)

        # 2. Heavy outer registration border (8px) for 100% reliable contour detection
        draw.rectangle([8, 8, width - 8, height - 8], outline=(15, 15, 15), width=8)

        # 3. Precision Corner Registration L-Brackets at all 4 corners
        def draw_corner_bracket(x, y, dx, dy):
            x0, x1 = min(x, x + dx * 60), max(x, x + dx * 60)
            y0, y1 = min(y, y + dy * 12), max(y, y + dy * 12)
            draw.rectangle([x0, y0, x1, y1], fill=(15, 15, 15))
            x0, x1 = min(x, x + dx * 12), max(x, x + dx * 12)
            y0, y1 = min(y, y + dy * 60), max(y, y + dy * 60)
            draw.rectangle([x0, y0, x1, y1], fill=(15, 15, 15))

        draw_corner_bracket(16, 16, 1, 1)
        draw_corner_bracket(width - 16, 16, -1, 1)
        draw_corner_bracket(16, height - 16, 1, -1)
        draw_corner_bracket(width - 16, height - 16, -1, -1)

        # 4. Official Classification & Provenance Header block (non-saturating dark charcoal 28)
        draw.rectangle([28, 28, width - 28, 92], fill=(28, 28, 28))
        draw.text(
            (60, 42),
            f"[{classification.upper()}] ASTRAEA QUANTUM SECURE PROVENANCE SYSTEM",
            fill=(245, 245, 245)
        )
        draw.text(
            (width - 340, 42),
            "SECURITY LEVEL: ML-DSA-65 / DWT-L2",
            fill=(200, 200, 200)
        )
        draw.line([(28, 92), (width - 28, 92)], fill=(15, 15, 15), width=2)

        # 5. Document Title and Reference Control Bar
        draw.text((60, 118), f"DOCUMENT IDENTIFIER: {title.upper()}", fill=(20, 20, 20))
        draw.line([(60, 152), (width - 60, 152)], fill=(30, 30, 30), width=2)

        # 6. Ruled Document Body Text
        lines = text_content.split("\n")
        y_offset = 180
        for line in lines:
            draw.line([(60, y_offset + 24), (width - 60, y_offset + 24)], fill=(220, 220, 220), width=1)
            draw.text((60, y_offset), line, fill=(20, 20, 20))
            y_offset += 34

        # 7. Subtle Forensic Provenance Footer Bar
        draw.rectangle([28, height - 58, width - 28, height - 28], fill=(225, 225, 225), outline=(180, 180, 180), width=1)
        w_display = wid_hex[:16] if wid_hex else "REFERENCE-CANVAS"
        draw.text(
            (60, height - 47),
            f"FORENSIC SIGNATURE: W_ID={w_display}... | IMMUTABLE LEDGER COMMITTED | LEVEL-2 HAAR DWT EMBEDDED",
            fill=(80, 80, 80)
        )

        return cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)

    def create_watermarked_document_image(
        self,
        title: str,
        classification: str,
        text_content: str,
        wid_hex: str
    ) -> str:
        """
        Renders document text onto optimized security document canvas, embeds Level-2 DWT W_ID watermark,
        and returns base64 PNG string for secure viewer presentation.
        """
        np_img = self.render_security_document_canvas(
            title=title,
            classification=classification,
            text_content=text_content,
            wid_hex=wid_hex
        )

        # Embed Level-2 DWT watermark
        watermarked_np = self.embed_wid_in_image(np_img, wid_hex)

        # Encode to Base64 PNG
        _, buffer = cv2.imencode(".png", watermarked_np)
        base64_str = base64.b64encode(buffer).decode("utf-8")
        return f"data:image/png;base64,{base64_str}"
