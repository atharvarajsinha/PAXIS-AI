const SIZE = 132;
const STROKE = 12;
const RADIUS = (SIZE - STROKE) / 2;
const CIRCUMFERENCE = 2 * Math.PI * RADIUS;

export default function ProgressRing({ value = 0, label = 'complete' }) {
  const clamped = Math.max(0, Math.min(100, Number(value) || 0));

  return (
    <svg
      className="progressRing"
      width={SIZE}
      height={SIZE}
      viewBox={`0 0 ${SIZE} ${SIZE}`}
      role="img"
      aria-label={`${clamped}% ${label}`}
    >
      <defs>
        <linearGradient id="progressRingGradient" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0%" stopColor="#7c3aed" />
          <stop offset="100%" stopColor="#c026d3" />
        </linearGradient>
      </defs>
      <circle
        cx={SIZE / 2}
        cy={SIZE / 2}
        r={RADIUS}
        fill="none"
        stroke="currentColor"
        strokeOpacity="0.12"
        strokeWidth={STROKE}
      />
      <circle
        cx={SIZE / 2}
        cy={SIZE / 2}
        r={RADIUS}
        fill="none"
        stroke="url(#progressRingGradient)"
        strokeWidth={STROKE}
        strokeLinecap="round"
        strokeDasharray={CIRCUMFERENCE}
        strokeDashoffset={CIRCUMFERENCE * (1 - clamped / 100)}
        transform={`rotate(-90 ${SIZE / 2} ${SIZE / 2})`}
        style={{ transition: 'stroke-dashoffset 600ms ease' }}
      />
      <text x="50%" y="47%" textAnchor="middle" className="progressRingValue">
        {clamped}%
      </text>
      <text x="50%" y="63%" textAnchor="middle" className="progressRingLabel">
        {label}
      </text>
    </svg>
  );
}
