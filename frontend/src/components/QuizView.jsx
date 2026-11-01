import { useState } from "react";

export default function QuizView({ quiz, onScore }) {
  const [answers, setAnswers] = useState({});
  const [submitted, setSubmitted] = useState(false);
  const questions = quiz.questions || [];

  if (!questions.length) {
    return <p className="muted">This quiz is still being written…</p>;
  }

  const score = questions.filter((q, i) => answers[i] === q.answer_index).length;
  const allAnswered = Object.keys(answers).length === questions.length;

  function submit() {
    setSubmitted(true);
    onScore(score, questions.length);
  }

  function reset() {
    setAnswers({});
    setSubmitted(false);
  }

  return (
    <article>
      <div className="row between wrap">
        <h2>
          Module {quiz.module_number} quiz <span className="muted">(days {quiz.day_range})</span>
        </h2>
        {quiz.last_score != null && (
          <span className="badge done">
            Last score: {quiz.last_score}/{quiz.last_total}
          </span>
        )}
      </div>

      {questions.map((q, i) => (
        <div key={i} className="card question">
          <p>
            <strong>
              {i + 1}. {q.question}
            </strong>
          </p>
          {q.options.map((opt, j) => {
            const picked = answers[i] === j;
            let state = "";
            if (submitted) state = j === q.answer_index ? "correct" : picked ? "wrong" : "";
            return (
              <label key={j} className={`option ${state}`}>
                <input
                  type="radio"
                  name={`q${i}`}
                  disabled={submitted}
                  checked={picked}
                  onChange={() => setAnswers({ ...answers, [i]: j })}
                />
                {opt}
              </label>
            );
          })}
          {submitted && <p className="explanation">{q.explanation}</p>}
        </div>
      ))}

      {submitted ? (
        <div className="row gap center-y">
          <strong>
            You scored {score} / {questions.length}
          </strong>
          <button className="btn small ghost" onClick={reset}>Try again</button>
        </div>
      ) : (
        <button className="btn" disabled={!allAnswered} onClick={submit}>
          Submit answers
        </button>
      )}
    </article>
  );
}
