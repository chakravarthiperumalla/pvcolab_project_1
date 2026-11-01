import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../api";

export default function NewRoadmap() {
  const navigate = useNavigate();
  const [form, setForm] = useState({
    topic: "",
    duration: 30,
    level: "Beginner",
    hours_per_day: 2,
    email_when_done: false,
  });
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const set = (key) => (e) =>
    setForm({ ...form, [key]: e.target.type === "checkbox" ? e.target.checked : e.target.value });

  async function submit(e) {
    e.preventDefault();
    setError("");
    setBusy(true);
    try {
      const roadmap = await api.createRoadmap({
        ...form,
        topic: form.topic.trim(),
        duration: Number(form.duration),
        hours_per_day: Number(form.hours_per_day),
      });
      navigate(`/roadmaps/${roadmap.id}`);
    } catch (err) {
      setError(err.message);
      setBusy(false);
    }
  }

  return (
    <div className="card narrow">
      <h1>New roadmap</h1>
      <p className="muted">
        You'll get a day-by-day handbook with lessons, practice, assignments and module quizzes. Longer plans take
        longer to write — you can watch it fill in live.
      </p>
      <form onSubmit={submit} className="form">
        <label>
          Topic
          <input required minLength={2} maxLength={200} placeholder="e.g. Machine Learning with Python" value={form.topic} onChange={set("topic")} />
        </label>
        <div className="row gap">
          <label className="grow">
            Duration (days)
            <input type="number" required min={1} max={180} value={form.duration} onChange={set("duration")} />
          </label>
          <label className="grow">
            Hours per day
            <input type="number" required min={0.5} max={12} step={0.5} value={form.hours_per_day} onChange={set("hours_per_day")} />
          </label>
        </div>
        <label>
          Level
          <select value={form.level} onChange={set("level")}>
            <option>Beginner</option>
            <option>Intermediate</option>
            <option>Advanced</option>
          </select>
        </label>
        <label className="check">
          <input type="checkbox" checked={form.email_when_done} onChange={set("email_when_done")} />
          Email me the PDF when it's ready
        </label>
        {error && <p className="error">{error}</p>}
        <button className="btn" disabled={busy}>
          {busy ? "Starting…" : "Generate roadmap"}
        </button>
      </form>
    </div>
  );
}
