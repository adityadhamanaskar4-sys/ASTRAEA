import io
import base64
import logging
import numpy as np
import cv2
from PIL import Image, ImageDraw, ImageFont

from backend.watermark_interface.wid import WatermarkIDService

logger = logging.getLogger("ASTRAEA.DWTWatermark")


class DWTWatermarkEngine:
    """
    Implementation of 2D Haar Discrete Wavelet Transform (DWT) Steganographic Watermarking
    with Reed-Solomon Error Correction and OpenCV Perspective Deskew Correction.
    
    Protects plaintext document presentations against photographic leak scenarios.
    """

    def __init__(self, alpha: float = 15.0):
        self.alpha = alpha  # Watermark embedding strength parameter
        self.wid_service = WatermarkIDService()

    @staticmethod
    def _haar_2d_forward(img_gray: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
        """Performs 1-level 2D Haar DWT transform."""
        h, w = img_gray.shape
        # Ensure even dimensions
        h_even = (h // 2) * 2
        w_even = (w // 2) * 2
        img = img_gray[:h_even, :w_even].astype(np.float64)

        a = img[0::2, 0::2]
        b = img[1::2, 0::2]
        c = img[0::2, 1::2]
        d = img[1::2, 1::2]

        LL = (a + b + c + d) / 2.0
        LH = (a - b + c - d) / 2.0
        HL = (a + b - c - d) / 2.0
        HH = (a - b - c + d) / 2.0
        return LL, LH, HL, HH

    @staticmethod
    def _haar_2d_inverse(LL: np.ndarray, LH: np.ndarray, HL: np.ndarray, HH: np.ndarray) -> np.ndarray:
        """Performs 1-level 2D Haar Inverse DWT transform."""
        h_sub, w_sub = LL.shape
        img_out = np.zeros((h_sub * 2, w_sub * 2), dtype=np.float64)

        img_out[0::2, 0::2] = (LL + LH + HL + HH) / 2.0
        img_out[1::2, 0::2] = (LL - LH + HL - HH) / 2.0
        img_out[0::2, 1::2] = (LL + LH - HL - HH) / 2.0
        img_out[1::2, 1::2] = (LL - LH - HL + HH) / 2.0

        return np.clip(img_out, 0, 255).astype(np.uint8)

    def embed_wid_in_image(self, base_image_np: np.ndarray, wid_hex: str) -> np.ndarray:
        """
        Embeds 256-bit W_ID into image using 2D Haar DWT HL sub-band coefficients.
        Input image: uint8 BGR or Grayscale numpy array.
        Returns: Watermarked uint8 BGR numpy array.
        """
        if len(base_image_np.shape) == 3:
            yuv = cv2.cvtColor(base_image_np, cv2.COLOR_BGR2YUV)
            Y = yuv[:, :, 0]
        else:
            Y = base_image_np.copy()
            yuv = None

        # 1. Obtain FEC-protected payload bytes (32 bytes W_ID + 18 bytes Reed-Solomon = 50 bytes = 400 bits)
        try:
            fec_bytes = self.wid_service.encode_wid_to_fec_bytes(wid_hex)
        except Exception as e:
            logger.warning(f"FEC encoding fallback to raw bytes: {e}")
            fec_bytes = bytes.fromhex(wid_hex)

        bitstream = []
        for byte in fec_bytes:
            for b in range(8):
                bitstream.append((byte >> (7 - b)) & 1)

        # 2. Forward DWT
        LL, LH, HL, HH = self._haar_2d_forward(Y)
        h_sub, w_sub = HL.shape

        total_bits = len(bitstream)
        idx = 0

        # Modulate HL coefficients
        for r in range(h_sub):
            for c in range(0, w_sub - 1, 2):
                if idx >= total_bits:
                    break
                bit = bitstream[idx]
                v1, v2 = HL[r, c], HL[r, c + 1]

                if bit == 1:
                    if v1 < v2 + self.alpha:
                        diff = (v2 + self.alpha - v1) / 2.0
                        HL[r, c] += diff
                        HL[r, c + 1] -= diff
                else:
                    if v1 > v2 - self.alpha:
                        diff = (v1 - (v2 - self.alpha)) / 2.0
                        HL[r, c] -= diff
                        HL[r, c + 1] += diff
                idx += 1
            if idx >= total_bits:
                break

        # 3. Inverse DWT
        Y_watermarked = self._haar_2d_inverse(LL, LH, HL, HH)

        if yuv is not None:
            # Resize if needed due to even dimension truncation
            h_orig, w_orig = base_image_np.shape[:2]
            Y_full = yuv[:, :, 0].copy()
            h_wm, w_wm = Y_watermarked.shape
            Y_full[:h_wm, :w_wm] = Y_watermarked
            yuv[:, :, 0] = Y_full
            watermarked_bgr = cv2.cvtColor(yuv, cv2.COLOR_YUV2BGR)
            return watermarked_bgr
        else:
            return Y_watermarked

    def extract_wid_from_image(self, img_np: np.ndarray, total_fec_bytes: int = 50) -> str:
        """
        Extracts embedded W_ID from image (with optional OpenCV perspective deskewing).
        Returns recovered 64-character hex W_ID string.
        """
        # 1. Perspective deskew correction
        corrected = self.correct_perspective_if_needed(img_np)

        if len(corrected.shape) == 3:
            yuv = cv2.cvtColor(corrected, cv2.COLOR_BGR2YUV)
            Y = yuv[:, :, 0]
        else:
            Y = corrected

        # 2. Forward DWT
        LL, LH, HL, HH = self._haar_2d_forward(Y)
        h_sub, w_sub = HL.shape

        total_bits = total_fec_bytes * 8
        extracted_bits = []
        idx = 0

        for r in range(h_sub):
            for c in range(0, w_sub - 1, 2):
                if idx >= total_bits:
                    break
                v1, v2 = HL[r, c], HL[r, c + 1]
                extracted_bits.append(1 if v1 >= v2 else 0)
                idx += 1
            if idx >= total_bits:
                break

        # Reconstruct byte payload
        byte_list = []
        for i in range(0, len(extracted_bits), 8):
            chunk = extracted_bits[i:i + 8]
            if len(chunk) < 8:
                break
            val = 0
            for b in chunk:
                val = (val << 1) | b
            byte_list.append(val)

        fec_payload = bytes(byte_list)

        # 3. Decode via Reed-Solomon FEC
        try:
            wid_hex = self.wid_service.decode_fec_bytes_to_wid(fec_payload)
            return wid_hex
        except Exception as ex:
            logger.warning(f"Reed-Solomon correction threshold exceeded, trying raw hex: {ex}")
            # Fallback to first 32 bytes hex representation
            return fec_payload[:32].hex()

    @staticmethod
    def correct_perspective_if_needed(img_np: np.ndarray) -> np.ndarray:
        """
        Applies OpenCV perspective correction / deskewing if image shows physical phone photograph distortion.
        """
        if len(img_np.shape) != 3:
            return img_np

        gray = cv2.cvtColor(img_np, cv2.COLOR_BGR2GRAY)
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)
        edged = cv2.Canny(blurred, 50, 150)

        contours, _ = cv2.findContours(edged.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if not contours:
            return img_np

        contours = sorted(contours, key=cv2.contourArea, reverse=True)
        doc_cnt = None

        for c in contours:
            peri = cv2.arcLength(c, True)
            approx = cv2.approxPolyDP(c, 0.02 * peri, True)
            if len(approx) == 4:
                doc_cnt = approx
                break

        if doc_cnt is None:
            return img_np

        pts = doc_cnt.reshape(4, 2)
        rect = np.zeros((4, 2), dtype="float32")

        s = pts.sum(axis=1)
        rect[0] = pts[np.argmin(s)]
        rect[2] = pts[np.argmax(s)]

        diff = np.diff(pts, axis=1)
        rect[1] = pts[np.argmin(diff)]
        rect[3] = pts[np.argmax(diff)]

        (tl, tr, br, bl) = rect
        widthA = np.sqrt(((br[0] - bl[0]) ** 2) + ((br[1] - bl[1]) ** 2))
        widthB = np.sqrt(((tr[0] - tl[0]) ** 2) + ((tr[1] - tl[1]) ** 2))
        maxWidth = max(int(widthA), int(widthB))

        heightA = np.sqrt(((tr[0] - br[0]) ** 2) + ((tr[1] - br[1]) ** 2))
        heightB = np.sqrt(((tl[0] - bl[0]) ** 2) + ((tl[1] - bl[1]) ** 2))
        maxHeight = max(int(heightA), int(heightB))

        if maxWidth < 100 or maxHeight < 100:
            return img_np

        dst = np.array([
            [0, 0],
            [maxWidth - 1, 0],
            [maxWidth - 1, maxHeight - 1],
            [0, maxHeight - 1]
        ], dtype="float32")

        M = cv2.getPerspectiveTransform(rect, dst)
        warped = cv2.warpPerspective(img_np, M, (maxWidth, maxHeight))
        return warped

    def create_watermarked_document_image(self, title: str, classification: str, text_content: str, wid_hex: str) -> str:
        """
        Renders document text onto an image canvas, embeds 2D Haar DWT W_ID watermark,
        and returns base64 PNG string for secure viewer presentation.
        """
        # Canvas dimensions
        width, height = 800, 600
        img = Image.new("RGB", (width, height), color=(248, 249, 250))
        draw = ImageDraw.Draw(img)

        # Header banner
        draw.rectangle([0, 0, width, 50], fill=(220, 53, 69) if classification == "RESTRICTED" else (255, 193, 7))
        draw.text((20, 15), f"[{classification}] ASTRAEA SECURE PROVENANCE SYSTEM", fill=(255, 255, 255))

        # Title and content
        draw.text((30, 80), f"DOCUMENT: {title}", fill=(33, 37, 41))
        draw.text((30, 110), "-" * 60, fill=(108, 117, 125))

        lines = text_content.split("\n")
        y_offset = 140
        for line in lines:
            draw.text((30, y_offset), line, fill=(33, 37, 41))
            y_offset += 25

        # Visual micro-watermark footer (subtle forensic signature tag)
        draw.text((30, height - 35), f"W_ID: {wid_hex[:16]}... (STWT-PROTECTED)", fill=(173, 181, 189))

        # Convert to numpy array
        np_img = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)

        # Embed DWT watermark
        watermarked_np = self.embed_wid_in_image(np_img, wid_hex)

        # Encode to Base64 PNG
        _, buffer = cv2.imencode(".png", watermarked_np)
        base64_str = base64.b64encode(buffer).decode("utf-8")
        return f"data:image/png;base64,{base64_str}"
