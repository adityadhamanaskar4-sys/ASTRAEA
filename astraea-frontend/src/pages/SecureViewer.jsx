import { useEffect, useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import { useAstraea } from '../context/AstraeaContext';
import SecureCanvas from '../components/SecureCanvas';
import StatusChip from '../components/StatusChip';

export default function SecureViewer() {
  const { activeSession } = useAstraea();
  const canvasRef = useRef(null);
  const [savedNote, setSavedNote] = useState('');

  useEffect(() => {
    const blockPrint = (e) => {
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'p') {
        e.preventDefault();
      }
    };
    window.addEventListener('keydown', blockPrint);
    return () => window.removeEventListener('keydown', blockPrint);
  }, []);

  const handleSimulatePhotograph = () => {
    const dataUrl = canvasRef.current?.exportPng();
    if (!dataUrl) return;
    const a = document.createElement('a');
    a.href = dataUrl;
    a.download = 'leaked-capture.png';
    a.click();
    setSavedNote('Saved a capture of this view — try uploading it to the Investigator Portal.');
  };

  return (
    <div>
      <div className="page-head">
        <div className="page-eyebrow mono">STAGE 03 — WATERMARKING</div>
        <h1 className="page-title">Secure Viewer</h1>
        <p className="page-desc">
          What the recipient actually sees: a normal-looking document. The forensic mark is
          embedded but invisible — nothing below reveals W_ID, signature bytes, or ledger state to
          the ordinary user.
        </p>
      </div>

      {!activeSession && (
        <div className="panel">
          <div className="panel-title">No active session</div>
          <p className="muted small" style={{ marginBottom: 14 }}>
            Nothing to show. This is the point: the viewer has nothing to render until the
            Recipient Terminal completes a ledger-committed decryption request.
          </p>
          <Link to="/recipient" className="btn btn-primary" style={{ textDecoration: 'none', width: 'fit-content', display: 'inline-block' }}>
            Go to Recipient Terminal
          </Link>
        </div>
      )}

      {activeSession && (
        <>
          <div className="panel spread">
            <StatusChip variant="verified">Verified secure session</StatusChip>
            <span className="small muted">Interface protections active</span>
          </div>

          <div className="panel">
            <div className="viewer-frame">
              <SecureCanvas ref={canvasRef} doc={activeSession.doc} wId={activeSession.wId} />
            </div>
            <p className="small muted" style={{ marginTop: 14, lineHeight: 1.6 }}>
              Right-click and Ctrl+P are blocked here as a basic deterrent. These do not stop a
              determined attacker from photographing the screen — that is exactly the case the
              forensic watermark is designed to survive, not the interface controls.
            </p>
          </div>

          <div className="panel">
            <div className="panel-title">Demo helper</div>
            <p className="small muted" style={{ marginBottom: 12 }}>
              For this demo, capture the current view as if it had been photographed, then trace it
              back in the Investigator Portal.
            </p>
            <button className="btn" onClick={handleSimulatePhotograph}>Simulate photograph</button>
            {savedNote && <p className="small" style={{ marginTop: 10, color: 'var(--teal)' }}>{savedNote}</p>}
          </div>
        </>
      )}
    </div>
  );
}
