import { forwardRef, useEffect, useImperativeHandle, useRef } from 'react';
import { renderDocument, embedWatermark } from '../services/watermark';

const SecureCanvas = forwardRef(function SecureCanvas({ doc, wId, width = 480, height = 340 }, ref) {
  const canvasRef = useRef(null);

  useEffect(() => {
    if (!canvasRef.current || !doc) return;
    renderDocument(canvasRef.current, {
      title: doc.title,
      docId: doc.docId,
      body: doc.body,
      classification: doc.classification,
    });
    if (wId) embedWatermark(canvasRef.current, wId);
  }, [doc, wId]);

  useImperativeHandle(ref, () => ({
    exportPng: () => canvasRef.current?.toDataURL('image/png'),
    getCanvas: () => canvasRef.current,
  }));

  return (
    <canvas
      ref={canvasRef}
      width={width}
      height={height}
      onContextMenu={(e) => e.preventDefault()}
      aria-label={doc ? `Secure view of ${doc.title}` : 'Secure document viewer'}
    />
  );
});

export default SecureCanvas;
