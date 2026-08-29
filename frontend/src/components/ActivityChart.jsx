/** Bar chart of stages completed per week. Bars are relative to the busiest week. */
export default function ActivityChart({ buckets = [] }) {
  if (!buckets.length) return <p className="sidebarNote">No activity recorded yet.</p>;

  const peak = Math.max(1, ...buckets.map((bucket) => bucket.completed));
  const total = buckets.reduce((sum, bucket) => sum + bucket.completed, 0);

  const weekLabel = (iso) => {
    const date = new Date(iso);
    return Number.isNaN(date.getTime())
      ? ''
      : date.toLocaleDateString(undefined, { month: 'short', day: 'numeric' });
  };

  return (
    <div className="activityChart">
      <div className="activityBars">
        {buckets.map((bucket, index) => (
          <div className="activityColumn" key={bucket.week_start}>
            <div
              className={`activityBar ${bucket.completed ? '' : 'empty'}`}
              style={{ height: `${Math.max(4, (bucket.completed / peak) * 100)}%` }}
              title={`Week of ${weekLabel(bucket.week_start)}: ${bucket.completed} completed`}
            >
              {bucket.completed > 0 && <span>{bucket.completed}</span>}
            </div>
            <small>{index === buckets.length - 1 ? 'now' : weekLabel(bucket.week_start)}</small>
          </div>
        ))}
      </div>
      <p className="activityTotal">
        {total} {total === 1 ? 'stage' : 'stages'} completed in the last 8 weeks
      </p>
    </div>
  );
}
