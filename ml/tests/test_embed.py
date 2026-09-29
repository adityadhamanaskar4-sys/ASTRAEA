import cv2
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from ml.embed import embed_watermark
from skimage.metrics import structural_similarity as ssim


# Original image
image = cv2.imread("ml/evaluation/test_image.jpg")

if image is None:
    raise FileNotFoundError("test_image.jpg not found")


# Temporary 50-byte payload
payload = bytes(range(50))


# Embed watermark
watermarked = embed_watermark(image, payload)

# Save result
cv2.imwrite("watermarked_test.jpg", watermarked)


# Calculate PSNR
psnr_value = cv2.PSNR(image, watermarked)


# Calculate SSIM
original_gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
watermarked_gray = cv2.cvtColor(watermarked, cv2.COLOR_BGR2GRAY)

ssim_value = ssim(original_gray, watermarked_gray)


print("\n===== WATERMARK QUALITY =====")
print(f"Payload size : {len(payload)} bytes")
print(f"PSNR         : {psnr_value:.2f} dB")
print(f"SSIM         : {ssim_value:.6f}")
print("=============================")
print("Watermarked image: watermarked_test.jpg")