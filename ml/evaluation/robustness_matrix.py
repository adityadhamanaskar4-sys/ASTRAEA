import os
import sys
import time
import cv2
import numpy as np
import pywt

sys.path.insert(0, ".")

from ml.embed import embed_watermark, EMBED_W, EMBED_H
from ml.extract import extract_watermark
from ml.preprocessing.photo import four_point_transform, order_points, detect_artifact

os.makedirs("scratch", exist_ok=True)


def calculate_psnr(original: np.ndarray, watermarked: np.ndarray) -> float:
    """Calculate Peak Signal-to-Noise Ratio (PSNR) in dB."""
    mse = np.mean((original.astype(np.float64) - watermarked.astype(np.float64)) ** 2)
    if mse == 0:
        return float("inf")
    max_pixel = 255.0
    return 20 * np.log10(max_pixel / np.sqrt(mse))


def calculate_ssim(img1: np.ndarray, img2: np.ndarray) -> float:
    """Calculate Structural Similarity Index (SSIM) on luminance channel."""
    y1 = cv2.cvtColor(img1, cv2.COLOR_BGR2YCrCb)[:, :, 0].astype(np.float64)
    y2 = cv2.cvtColor(img2, cv2.COLOR_BGR2YCrCb)[:, :, 0].astype(np.float64)

    C1 = (0.01 * 255) ** 2
    C2 = (0.03 * 255) ** 2

    mu1 = cv2.GaussianBlur(y1, (11, 11), 1.5)
    mu2 = cv2.GaussianBlur(y2, (11, 11), 1.5)

    mu1_sq = mu1 ** 2
    mu2_sq = mu2 ** 2
    mu1_mu2 = mu1 * mu2

    sigma1_sq = cv2.GaussianBlur(y1 ** 2, (11, 11), 1.5) - mu1_sq
    sigma2_sq = cv2.GaussianBlur(y2 ** 2, (11, 11), 1.5) - mu2_sq
    sigma12 = cv2.GaussianBlur(y1 * y2, (11, 11), 1.5) - mu1_mu2

    ssim_map = ((2 * mu1_mu2 + C1) * (2 * sigma12 + C2)) / (
        (mu1_sq + mu2_sq + C1) * (sigma1_sq + sigma2_sq + C2)
    )
    return float(np.mean(ssim_map))


def run_matrix():
    print("=" * 75)
    print("      ASTRAEA ML Watermarking Robustness Evaluation Matrix")
    print("=" * 75)

    payload = bytes(range(50))
    img_path = "ml/evaluation/test_image.jpg"
    img = cv2.imread(img_path)

    if img is None:
        print(f"Error: Could not load {img_path}")
        return

    # Measure watermark imperceptibility at embedding resolution
    img_embed_res = cv2.resize(img, (EMBED_W, EMBED_H), interpolation=cv2.INTER_AREA)
    watermarked_small = embed_watermark(img, payload, return_display=False)
    watermarked_display = embed_watermark(img, payload, return_display=True)

    t0 = time.time()
    _ = embed_watermark(img, payload)
    embed_time = (time.time() - t0) * 1000

    psnr = calculate_psnr(img_embed_res, watermarked_small)
    ssim = calculate_ssim(img_embed_res, watermarked_small)

    print(f"Original Resolution : {img.shape[1]} x {img.shape[0]}")
    print(f"Embed Grid          : {EMBED_W} x {EMBED_H}")
    print(f"Embedding Time      : {embed_time:.2f} ms")
    print(f"Watermark PSNR      : {psnr:.2f} dB  (Requirement: > 38 dB) {'[OK]' if psnr > 38 else '[FAIL]'}")
    print(f"Watermark SSIM      : {ssim:.4f}     (Requirement: > 0.95) {'[OK]' if ssim > 0.95 else '[FAIL]'}")
    print("-" * 75)
    print(f"{'Attack / Distortion':<38} | {'Recovered':<10} | {'Accuracy':<9} | {'Status'}")
    print("-" * 75)

    results = []

    # 1. Digital Exact
    ext = extract_watermark(watermarked_display)
    match = sum(1 for a, b in zip(payload, ext) if a == b)
    results.append(("Digital Baseline (Uncorrupted)", match, 50))

    # 2. JPEG Compression Matrix
    for q in [95, 90, 80, 70, 60, 50, 40, 30]:
        filename = f"scratch/test_q{q}.jpg"
        cv2.imwrite(filename, watermarked_display, [cv2.IMWRITE_JPEG_QUALITY, q])
        comp = cv2.imread(filename)
        ext = extract_watermark(comp)
        m = sum(1 for a, b in zip(payload, ext) if a == b)
        results.append((f"JPEG Compression (Quality = {q})", m, 50))

    # 3. Additive Gaussian Noise
    for std in [2, 5, 10, 15]:
        noise = np.random.normal(0, std, watermarked_display.shape).astype(np.int16)
        noisy = np.clip(watermarked_display.astype(np.int16) + noise, 0, 255).astype(np.uint8)
        ext = extract_watermark(noisy)
        m = sum(1 for a, b in zip(payload, ext) if a == b)
        results.append((f"Gaussian Noise (std = {std})", m, 50))

    # 4. Gaussian Blur
    for k in [3, 5, 7]:
        blurred = cv2.GaussianBlur(watermarked_display, (k, k), 0)
        ext = extract_watermark(blurred)
        m = sum(1 for a, b in zip(payload, ext) if a == b)
        results.append((f"Gaussian Blur (kernel = {k}x{k})", m, 50))

    # 5. Resolution Scaling (Downscale & Upscale back)
    h, w = watermarked_display.shape[:2]
    for scale in [0.75, 0.5, 1.25, 1.5]:
        new_w, new_h = int(w * scale), int(h * scale)
        scaled = cv2.resize(watermarked_display, (new_w, new_h), interpolation=cv2.INTER_AREA)
        restored = cv2.resize(scaled, (w, h), interpolation=cv2.INTER_CUBIC)
        ext = extract_watermark(restored)
        m = sum(1 for a, b in zip(payload, ext) if a == b)
        results.append((f"Resolution Rescale ({scale}x)", m, 50))

    # 6. Perspective Warp + Physical Unwarp
    pts1 = np.float32([[0, 0], [w, 0], [w, h], [0, h]])
    pts2 = np.float32([[50, 60], [w - 70, 40], [w - 40, h - 50], [30, h - 80]])
    M = cv2.getPerspectiveTransform(pts1, pts2)
    warped = cv2.warpPerspective(watermarked_display, M, (w, h))

    unwarped_gt = four_point_transform(warped, pts2)
    ext_warp = extract_watermark(cv2.resize(unwarped_gt, (EMBED_W, EMBED_H), interpolation=cv2.INTER_AREA))
    m_warp = sum(1 for a, b in zip(payload, ext_warp) if a == b)
    results.append(("Perspective Warp (Sub-pixel Unwarped)", m_warp, 50))

    # Output table
    for name, match_count, total in results:
        acc = (match_count / total) * 100
        status = "PASSED" if match_count >= 40 else "FAILED"
        print(f"{name:<38} | {match_count:>2}/{total:<2} bytes | {acc:>6.1f}%  | {status}")

    print("=" * 75)


if __name__ == "__main__":
    run_matrix()
