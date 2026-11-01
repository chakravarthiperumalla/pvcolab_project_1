import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api";
import StatusBadge from "../components/StatusBadge";

const ACTIVE = ["queued", "planning", "generating"];

export default function Dashboard() {
  const [roadmaps, setRoadmaps] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    let cancelled = false;
    let timer;
    async function load() {
      try {
        const data = await api.listRoadmaps();
        if (cancelled) return;
        setRoadmaps(data);
        if (data.some((r) => ACTIVE.includes(r.status))) timer = setTimeout(load, 4000);
      } catch (e) {
        if (!cancelled) setError(e.message);
      }
    }
    load();
    return () => {
      cancelled = true;
      clearTimeout(timer);
    };
  }, []);

  if (error) return <p className="error">{error}</p>;
  if (!roadmaps) return <p className="center muted">Loading…</p>;

  return (
    <>
      <div className="row between">
        <h1>Your roadmaps</h1>
        <Link to="/new" className="btn">+ New roadmap</Link>
      </div>
      {roadmaps.length === 0 ? (
        <div className="card center">
          <h2>No roadmaps yet</h2>
          <p className="muted">Pick a topic, a duration and your level — we'll build the whole handbook.</p>
          <Link to="/new" className="btn">Create your first roadmap</Link>
        </div>
      ) : (
        <div className="grid">
          {roadmaps.map((r) => (
            <Link key={r.id} to={`/roadmaps/${r.id}`} className="card link-card">
              <div className="row between">
                <h3>{r.topic}</h3>
                <StatusBadge status={r.status} />
              </div>
              <p className="muted">
                {r.duration} days · {r.level} · {r.hours_per_day}h/day
              </p>
              {r.status !== "done" && r.total_steps > 0 && (
                <progress value={r.done_steps} max={r.total_steps} />
              )}
            </Link>
          ))}
        </div>
      )}
    </>
  );
}
