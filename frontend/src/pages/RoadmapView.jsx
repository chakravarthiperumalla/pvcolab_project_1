import { useCallback, useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { api } from "../api";
import DayView from "../components/DayView";
import QuizView from "../components/QuizView";
import StatusBadge from "../components/StatusBadge";

const ACTIVE = ["queued", "planning", "generating"];

export default function RoadmapView() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [roadmap, setRoadmap] = useState(null);
  const [selected, setSelected] = useState({ type: "day", n: 1 });
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  const load = useCallback(async () => {
    try {
      setRoadmap(await api.getRoadmap(id));
      return true;
    } catch (e) {
      setError(e.message);
      return false;
    }
  }, [id]);

  useEffect(() => {
    load();
  }, [load]);

  // Poll only while generation is running, so lessons appear as they're written.
  const isActive = roadmap ? ACTIVE.includes(roadmap.status) : false;
  useEffect(() => {
    if (!isActive) return;
    const timer = setInterval(load, 3000);
    return () => clearInterval(timer);
  }, [isActive, load]);

  if (error) return <p className="error">{error}</p>;
  if (!roadmap) return <p className="center muted">Loading…</p>;

  const active = ACTIVE.includes(roadmap.status);
  const doneDays = roadmap.days.filter((d) => d.completed).length;
  const currentDay = selected.type === "day" ? roadmap.days.find((d) => d.day_number === selected.n) : null;
  const currentQuiz = selected.type === "quiz" ? roadmap.quizzes.find((q) => q.module_number === selected.n) : null;

  async function toggleDay(day) {
    const completed = !day.completed;
    setRoadmap({
      ...roadmap,
      days: roadmap.days.map((d) => (d.day_number === day.day_number ? { ...d, completed } : d)),
    });
    try {
      await api.setDayProgress(roadmap.id, day.day_number, completed);
    } catch (e) {
      setNotice(e.message);
      load();
    }
  }

  async function saveScore(module, score, total) {
    try {
      await api.saveQuizScore(roadmap.id, module, score, total);
      setRoadmap({
        ...roadmap,
        quizzes: roadmap.quizzes.map((q) =>
          q.module_number === module ? { ...q, last_score: score, last_total: total } : q
        ),
      });
    } catch (e) {
      setNotice(e.message);
    }
  }

  async function action(fn, okMessage) {
    setNotice("");
    try {
      await fn();
      if (okMessage) setNotice(okMessage);
    } catch (e) {
      setNotice(e.message);
    }
  }

  return (
    <>
      <div className="row between wrap">
        <div>
          <h1>{roadmap.topic}</h1>
          <p className="muted">
            {roadmap.duration} days · {roadmap.level} · {roadmap.hours_per_day}h/day ·{" "}
            <StatusBadge status={roadmap.status} />
          </p>
        </div>
        <div className="row gap wrap">
          {roadmap.status === "done" && (
            <>
              <button className="btn small" onClick={() => action(() => api.downloadPdf(roadmap.id, roadmap.topic))}>
                Download PDF
              </button>
              <button
                className="btn small ghost"
                onClick={() => action(() => api.emailRoadmap(roadmap.id), "Check your inbox in a minute.")}
              >
                Email me a copy
              </button>
            </>
          )}
          {roadmap.status === "failed" && (
            <button
              className="btn small"
              onClick={() =>
                action(async () => {
                  await api.retryRoadmap(roadmap.id);
                  await load();
                })
              }
            >
              Retry
            </button>
          )}
          {!active && (
            <button
              className="btn small danger"
              onClick={() => {
                if (confirm("Delete this roadmap?"))
                  action(async () => {
                    await api.deleteRoadmap(roadmap.id);
                    navigate("/");
                  });
              }}
            >
              Delete
            </button>
          )}
        </div>
      </div>

      {notice && <p className="notice">{notice}</p>}
      {roadmap.status === "failed" && (
        <p className="error">
          {roadmap.error || "Generation failed."} Finished days are kept — press Retry to resume.
        </p>
      )}
      {active && (
        <div className="card">
          <p>
            <strong>{roadmap.status === "planning" ? "Planning your roadmap…" : "Writing your handbook…"}</strong>{" "}
            <span className="muted">
              {roadmap.done_steps}/{roadmap.total_steps || "…"} sections done. You can start reading finished days now.
            </span>
          </p>
          <progress value={roadmap.done_steps} max={roadmap.total_steps || 1} />
        </div>
      )}

      {roadmap.days.length > 0 && (
        <div className="layout">
          <aside className="sidebar">
            <p className="muted small-text">
              Progress: {doneDays}/{roadmap.days.length} days
            </p>
            <progress value={doneDays} max={roadmap.days.length} />
            <ul className="nav-list">
              {roadmap.days.map((d) => (
                <li key={d.day_number}>
                  <button
                    className={selected.type === "day" && selected.n === d.day_number ? "active" : ""}
                    onClick={() => setSelected({ type: "day", n: d.day_number })}
                  >
                    <span className="check-mark">{d.completed ? "✓" : d.content ? "○" : "…"}</span>
                    Day {d.day_number}: {d.title}
                  </button>
                </li>
              ))}
              {roadmap.quizzes.length > 0 && <li className="nav-heading">Quizzes</li>}
              {roadmap.quizzes.map((q) => (
                <li key={`q${q.module_number}`}>
                  <button
                    className={selected.type === "quiz" && selected.n === q.module_number ? "active" : ""}
                    onClick={() => setSelected({ type: "quiz", n: q.module_number })}
                  >
                    <span className="check-mark">{q.last_score != null ? "✓" : "?"}</span>
                    Module {q.module_number} quiz
                  </button>
                </li>
              ))}
            </ul>
          </aside>
          <section className="content card">
            {currentDay && <DayView key={currentDay.day_number} day={currentDay} onToggle={() => toggleDay(currentDay)} />}
            {currentQuiz && (
              <QuizView
                key={`${currentQuiz.module_number}-${currentQuiz.questions?.length}`}
                quiz={currentQuiz}
                onScore={(s, t) => saveScore(currentQuiz.module_number, s, t)}
              />
            )}
            {!currentDay && !currentQuiz && <p className="muted">Pick a day from the list.</p>}
          </section>
        </div>
      )}
    </>
  );
}
