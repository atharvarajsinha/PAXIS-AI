/**
 * Single source of truth for the app's name and mark.
 *
 * The artwork lives at /paxis-icon.svg so the favicon, the manifest and every
 * in-app placement all render the same file; swapping that one file rebrands
 * the whole UI.
 */
export const APP_NAME = 'PAXIS AI';
export const APP_FULL_NAME = 'Personalized AI Exploration and Intelligent Strategy';
export const APP_TAGLINE = 'Explore what to learn. Follow a strategy that fits you.';
export const BRAND_ICON = '/paxis-icon.svg';

export default function BrandMark({ size = 40, className = '', withGlow = false }) {
  return (
    <img
      src={BRAND_ICON}
      alt=""
      aria-hidden="true"
      width={size}
      height={size}
      className={`brandMark ${withGlow ? 'glow' : ''} ${className}`.trim()}
      draggable="false"
    />
  );
}

/** The mark plus the wordmark, used in the header, footer and auth pages. */
export function BrandLockup({ size = 44, subtitle = APP_FULL_NAME, compact = false }) {
  return (
    <div className={`brandLockup ${compact ? 'compact' : ''}`}>
      <BrandMark size={size} />
      <div className="brandLockupText">
        <strong>{APP_NAME}</strong>
        {subtitle && <span>{subtitle}</span>}
      </div>
    </div>
  );
}
