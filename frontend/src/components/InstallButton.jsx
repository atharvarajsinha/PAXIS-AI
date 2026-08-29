import { useEffect, useRef, useState, useSyncExternalStore } from 'react';
import { APP_NAME } from './BrandMark.jsx';
import { CloseIcon, DownloadIcon, ShareIcon } from './icons.jsx';
import {
  getInstallState,
  promptInstall,
  subscribeToInstallState,
} from '../services/pwa.js';

/**
 * Shows only when the app can actually be installed. On iOS, where there is no
 * prompt API, it explains the Share > Add to Home Screen route instead.
 */
export default function InstallButton({ compact = false }) {
  const state = useSyncExternalStore(subscribeToInstallState, getInstallState, () => 'unavailable');
  const [showHelp, setShowHelp] = useState(false);
  const wrapRef = useRef(null);

  useEffect(() => {
    if (!showHelp) return undefined;
    const close = (event) => {
      if (wrapRef.current && !wrapRef.current.contains(event.target)) setShowHelp(false);
    };
    document.addEventListener('mousedown', close);
    return () => document.removeEventListener('mousedown', close);
  }, [showHelp]);

  if (state === 'installed' || state === 'unavailable') return null;

  const handleClick = async () => {
    if (state === 'manual') {
      setShowHelp((open) => !open);
      return;
    }
    await promptInstall();
  };

  return (
    <div className="installWrap" ref={wrapRef}>
      <button
        className={`ghostBtn installBtn ${compact ? 'iconBtn' : ''}`}
        onClick={handleClick}
        title={`Install ${APP_NAME} on this device`}
        aria-label={`Install ${APP_NAME}`}
      >
        <DownloadIcon size={16} />
        {!compact && <span>Install</span>}
      </button>

      {showHelp && (
        <div className="installHelp" role="dialog" aria-label={`Install ${APP_NAME} on iOS`}>
          <button
            className="installHelpClose"
            onClick={() => setShowHelp(false)}
            aria-label="Close"
          >
            <CloseIcon size={14} />
          </button>
          <strong>Add to your Home Screen</strong>
          <ol>
            <li>
              Tap <ShareIcon size={14} /> <em>Share</em> in Safari&apos;s toolbar.
            </li>
            <li>
              Choose <em>Add to Home Screen</em>.
            </li>
            <li>
              Tap <em>Add</em>.
            </li>
          </ol>
        </div>
      )}
    </div>
  );
}
