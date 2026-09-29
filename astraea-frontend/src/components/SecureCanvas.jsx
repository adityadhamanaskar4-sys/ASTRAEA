import { forwardRef, useEffect, useImperativeHandle, useRef } from 'react';
import { renderDocument, embedWatermark } from '../services/watermark';

const SecureCanvas = forwardRef(function SecureCanvas(
  { doc, wId, watermarkedImageBase64, width = 800, height = 450 },
  ref
) {
  const canvasRef = useRef(null);

  useEffect(() => {
    if (!canvasRef.current || !doc) return;
    const canvas = canvasRef.current;
    const ctx = canvas.getContext('2d');

    if (watermarkedImageBase64) {
      const img = new Image();
      img.onload = () => {
        canvas.width = img.naturalWidth || 1600;
        canvas.height = img.naturalHeight || 900;
        ctx.drawImage(img, 0, 0);
      };
      img.src = watermarkedImageBase64;
    } else {
      canvas.width = width;
      canvas.height = height;
      renderDocument(canvas, {
        title: doc.title,
        docId: doc.docId,
        body: doc.body,
        classification: doc.classification,
      });
      if (wId) embedWatermark(canvas, wId);
    }
  }, [doc, wId, watermarkedImageBase64, width, height]);

  useImperativeHandle(ref, () => ({
    exportPng: () => {
      if (watermarkedImageBase64) return watermarkedImageBase64;
      return canvasRef.current?.toDataURL('image/png');
    },
    getCanvas: () => canvasRef.current,
  }));

  return (
    <canvas
      ref={canvasRef}
      style={{
        maxWidth: '100%',
        height: 'auto',
        borderRadius: '4px',
        boxShadow: '0 4px 16px rgba(0,0,0,0.18)',
        display: 'block'
      }}
      onContextMenu={(e) => e.preventDefault()}
      aria-label={doc ? `Secure view of ${doc.title}` : 'Secure document viewer'}
    />
  );
});

export default SecureCanvas;
