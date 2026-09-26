# ASTRAEA — ML/CV & Digital Forensics

## Overview

This module implements the Machine Learning / Computer Vision layer
of Project ASTRAEA.

The primary responsibility of this module is to embed a forensic
payload into a visually identical document/image using 2D Discrete
Wavelet Transform (DWT), and recover the payload from a potentially
distorted physical photograph.

The module is responsible for recovering the forensic payload.
Attribution, ledger lookup, cryptographic verification, and FEC
decoding are handled outside this module.

---

# Current Status

| Component | Status |
|---|---|
| Repository / ML branch setup | ✅ Working |
| DWT watermark embedding | ✅ Working |
| YCrCb luminance processing | ✅ Working |
| HL/LH frequency-band embedding | ✅ Working |
| 50-byte test payload | ✅ Working |
| Digital DWT extraction | ✅ Working |
| Digital 50/50 payload recovery | ✅ Working |
| PSNR / SSIM evaluation | ✅ Working |
| 5× bit redundancy | ✅ Implemented |
| OpenCV artifact detection | ✅ Working on current test photo |
| Perspective correction | ✅ Working on current test photo |
| Physical smartphone-photo extraction | ⚠️ Not yet reliable |
| Robustness tuning | ⏳ Pending |
| Robustness matrix | ⏳ Pending |
| Zero-width text channel | ⏳ Pending |
| Failure analysis | ⏳ Pending |
| Final evaluation/report | ⏳ Pending |

---

# Current Working Pipeline

## Digital Test

The current digital pipeline is:

Image
→ YCrCb conversion
→ luminance channel
→ 2D Haar DWT
→ HL/LH coefficients
→ payload embedding
→ inverse DWT
→ watermarked image
→ DWT extraction
→ recovered payload

The current controlled digital test successfully recovers:

**50/50 bytes**

with exact payload equality.

---

# DWT Watermarking

## Input

The intended backend input is an FEC-protected byte array of approximately
50 bytes.

For current development and testing, a temporary 50-byte payload is used.

## Embedding

The image is converted from BGR to YCrCb.

The Y (luminance) channel is transformed using a 2D Haar DWT.

The payload is embedded into the HL and LH frequency bands.

The HH band is not currently used because it is more vulnerable to
camera and JPEG distortion.

## Current Embedding Parameters

```text
Wavelet: Haar
Color space: YCrCb
Working channel: Y / luminance
Frequency bands: HL + LH
Embedding strength (alpha): 20.0
Coefficient offset: 128
Bit repetition: 5×