import { describe, it, expect } from 'vitest';
import { embedWatermark, extractWatermark, canvasToImageData } from '../services/watermark';

// A minimal fake <canvas> whose 2d context stores pixel data in a plain
// buffer, just enough surface area for embedWatermark/extractWatermark.
function makeFakeCanvas(width, height) {
  const buffer = new Uint8ClampedArray(width * height * 4).fill(200);
  const ctx = {
    getImageData: () => ({ data: new Uint8ClampedArray(buffer), width, height }),
    putImageData: (imageData) => {
      buffer.set(imageData.data);
    },
  };
  return { width, height, getContext: () => ctx };
}

describe('watermark embed/extract', () => {
  it('recovers the exact id that was embedded', () => {
    const canvas = makeFakeCanvas(200, 150);
    embedWatermark(canvas, 'ABCDEF1234567890');
    const imageData = canvasToImageData(canvas);
    expect(extractWatermark(imageData)).toBe('ABCDEF1234567890');
  });

  it('returns null when no watermark marker is present', () => {
    const canvas = makeFakeCanvas(200, 150);
    const imageData = canvasToImageData(canvas);
    expect(extractWatermark(imageData)).toBeNull();
  });

  it('rejects a payload too large for the canvas', () => {
    const canvas = makeFakeCanvas(4, 4); // 16 pixels only
    expect(() => embedWatermark(canvas, 'this id is far too long for 16 pixels')).toThrow();
  });
});
