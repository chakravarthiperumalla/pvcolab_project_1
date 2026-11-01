const LABELS = {
  queued: "Queued",
  planning: "Planning",
  generating: "Writing",
  done: "Ready",
  failed: "Failed",
};

export default function StatusBadge({ status }) {
  return <span className={`badge ${status}`}>{LABELS[status] || status}</span>;
}
