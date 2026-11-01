import ReactMarkdown from "react-markdown";

const Md = ({ children }) => <ReactMarkdown>{children || ""}</ReactMarkdown>;

function Section({ title, children }) {
  if (!children) return null;
  return (
    <section className="lesson-section">
      <h3>{title}</h3>
      {children}
    </section>
  );
}

function QuestionList({ title, items }) {
  if (!items?.length) return null;
  return (
    <div className="qlist">
      <h4>{title}</h4>
      <ol>
        {items.map((q, i) => (
          <li key={i}>
            <Md>{q}</Md>
          </li>
        ))}
      </ol>
    </div>
  );
}

export default function DayView({ day, onToggle }) {
  const c = day.content;
  return (
    <article>
      <div className="row between wrap">
        <h2>
          Day {day.day_number}: {day.title}
        </h2>
        <button className={`btn small ${day.completed ? "" : "ghost"}`} onClick={onToggle}>
          {day.completed ? "✓ Completed" : "Mark complete"}
        </button>
      </div>
      {!c ? (
        <p className="muted">This day is still being written…</p>
      ) : (
        <>
          <p className="goal">
            <strong>Goal:</strong> {c.goal}
          </p>
          <Section title="Theory"><Md>{c.theory}</Md></Section>
          <Section title="Examples"><Md>{c.examples}</Md></Section>
          <Section title="Real-world use case"><Md>{c.real_world_use_case}</Md></Section>
          <Section title="Common mistakes"><Md>{c.common_mistakes}</Md></Section>
          <Section title="Summary"><Md>{c.summary}</Md></Section>
          <Section title="Practice">
            <QuestionList title="Multiple choice" items={c.practice.mcqs} />
            <QuestionList title="Coding" items={c.practice.coding_questions} />
            <QuestionList title="Debugging" items={c.practice.debugging_questions} />
            <QuestionList title="Interview" items={c.practice.interview_questions} />
          </Section>
          <Section title="Assignment">
            <div className="assignment">
              <p><strong>Mini assignment</strong></p><Md>{c.assignment.mini_assignment}</Md>
              <p><strong>Homework</strong></p><Md>{c.assignment.homework}</Md>
              <p><strong>Challenge</strong></p><Md>{c.assignment.challenge}</Md>
              <details>
                <summary>Hints</summary>
                <Md>{c.assignment.hints}</Md>
              </details>
              <details>
                <summary>Expected output</summary>
                <Md>{c.assignment.expected_output}</Md>
              </details>
            </div>
          </Section>
        </>
      )}
    </article>
  );
}
