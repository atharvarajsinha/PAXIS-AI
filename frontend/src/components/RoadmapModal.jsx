import { useEffect, useRef } from 'react';
import RoadmapPanel from './RoadmapPanel.jsx';
import { CloseIcon } from './icons.jsx';

/**
 * Dialog wrapper around RoadmapPanel. The chat now owns the full width, so the
 * roadmap opens over it on demand instead of permanently taking half the screen.
 */
export default function RoadmapModal({ open, onClose, roadmap, loading, statusText, onTrack, saveState }) {
  const closeRef = useRef(null);

  useEffect(() => {
    if (!open) return undefined;

    const onKeyDown = (event) => {
      if (event.key === 'Escape') onClose();
    };
    document.addEventListener('keydown', onKeyDown);

    // Stop the page behind the dialog from scrolling while it is open.
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    closeRef.current?.focus();

    return () => {
      document.removeEventListener('keydown', onKeyDown);
      document.body.style.overflow = previousOverflow;
    };
  }, [open, onClose]);

  if (!open) return null;

  return (
    <div
      className="modalBackdrop"
      onMouseDown={(event) => {
        if (event.target === event.currentTarget) onClose();
      }}
    >
      <div className="modalShell" role="dialog" aria-modal="true" aria-label="Your learning roadmap">
        <button
          ref={closeRef}
          className="modalClose"
          onClick={onClose}
          aria-label="Close roadmap"
          title="Close roadmap (Esc)"
        >
          <CloseIcon size={18} />
        </button>
        <RoadmapPanel
          roadmap={roadmap}
          loading={loading}
          statusText={statusText}
          onTrack={onTrack}
          saveState={saveState}
        />
      </div>
    </div>
  );
}
