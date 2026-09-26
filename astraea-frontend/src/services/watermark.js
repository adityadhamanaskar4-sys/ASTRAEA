// ASTRAEA demo — forensic watermark simulation.
//
// The real ASTRAEA design embeds W_ID in the wavelet (DWT) domain so it
// survives print/photograph/re-compress cycles. Reproducing true DWT
// watermarking is out of scope for this demo frontend. Instead we embed
// W_ID in the least-significant bits of the rendered canvas, which is
// enough to demonstrate the *pipeline and the UI story* end to end
// (embed → export → re-upload → recover → look up on the ledger) without
// claiming camera-photograph robustness. The UI must never claim this
// stands in for camera-robust extraction — see SecureViewer's copy.

const MARKER = 'ASTW'; // 4-byte marker so extraction can find the payload

function stringToBits(str) {
  const bytes = new TextEncoder().encode(str);
  const bits = [];
  for (const byte of bytes) {
    for (let i = 7; i >= 0; i--) bits.push((byte >> i) & 1);
  }
  return bits;
}

function bitsToString(bits) {
  const bytes = [];
  for (let i = 0; i + 8 <= bits.length; i += 8) {
    let byte = 0;
    for (let j = 0; j < 8; j++) byte = (byte << 1) | bits[i + j];
    bytes.push(byte);
  }
  return new TextDecoder().decode(new Uint8Array(bytes));
}

export function renderDocument(canvas, { title, docId, body, classification }) {
  const ctx = canvas.getContext('2d');
  const w = canvas.width;
  const h = canvas.height;

  ctx.fillStyle = '#f4f1e8';
  ctx.fillRect(0, 0, w, h);

  ctx.strokeStyle = '#c9a227';
  ctx.lineWidth = 3;
  ctx.strokeRect(10, 10, w - 20, h - 20);

  ctx.fillStyle = '#8a1f1f';
  ctx.font = '600 13px "JetBrains Mono", monospace';
  ctx.fillText(classification || 'RESTRICTED', 28, 40);

  ctx.fillStyle = '#1b1b1b';
  ctx.font = '700 20px "Space Grotesk", sans-serif';
  ctx.fillText(title, 28, 74);

  ctx.font = '12px "JetBrains Mono", monospace';
  ctx.fillStyle = '#555';
  ctx.fillText(`REF ${docId}`, 28, 94);

  ctx.strokeStyle = '#d8d2bf';
  ctx.beginPath();
  ctx.moveTo(28, 106);
  ctx.lineTo(w - 28, 106);
  ctx.stroke();

  ctx.fillStyle = '#2a2a2a';
  ctx.font = '13px "Space Grotesk", sans-serif';
  const lines = body.split('\n');
  let y = 132;
  for (const line of lines) {
    ctx.fillText(line, 28, y);
    y += 22;
  }

  return canvas;
}

// Embeds a short id string into the blue channel LSBs of the first N
// pixels of the canvas. Visually imperceptible; recoverable only by a
// program that knows to look, which is the point of a forensic mark.
export function embedWatermark(canvas, wId) {
  const ctx = canvas.getContext('2d');
  const { width, height } = canvas;
  const imageData = ctx.getImageData(0, 0, width, height);
  const payload = MARKER + wId;
  const bits = stringToBits(payload);

  if (bits.length > imageData.data.length / 4) {
    throw new Error('Watermark payload too large for canvas');
  }

  for (let i = 0; i < bits.length; i++) {
    const pixelIndex = i * 4; // walk pixel by pixel, use blue channel
    const blueByteIndex = pixelIndex + 2;
    imageData.data[blueByteIndex] = (imageData.data[blueByteIndex] & 0xfe) | bits[i];
  }

  ctx.putImageData(imageData, 0, 0);
  return canvas;
}

// Attempts to recover a watermark from an uploaded image. Returns the
// recovered W_ID string, or null if no valid marker was found (this is
// the "extraction failed / no match" path the Investigator Portal uses).
export function extractWatermark(imageData, maxPayloadChars = 64) {
  const markerBitsLen = MARKER.length * 8;
  const totalBits = markerBitsLen + maxPayloadChars * 8;
  const bits = [];

  for (let i = 0; i < totalBits; i++) {
    const pixelIndex = i * 4;
    const blueByteIndex = pixelIndex + 2;
    if (blueByteIndex >= imageData.data.length) break;
    bits.push(imageData.data[blueByteIndex] & 1);
  }

  const markerBits = bits.slice(0, markerBitsLen);
  const marker = bitsToString(markerBits);
  if (marker !== MARKER) return null;

  // Decode the remainder until we hit a non-printable / null byte.
  const payloadBits = bits.slice(markerBitsLen);
  let out = '';
  for (let i = 0; i + 8 <= payloadBits.length; i += 8) {
    let byte = 0;
    for (let j = 0; j < 8; j++) byte = (byte << 1) | payloadBits[i + j];
    if (byte === 0 || byte < 32 || byte > 126) break;
    out += String.fromCharCode(byte);
  }
  return out || null;
}

export function canvasToImageData(canvas) {
  const ctx = canvas.getContext('2d');
  return ctx.getImageData(0, 0, canvas.width, canvas.height);
}
