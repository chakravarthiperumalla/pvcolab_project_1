import { Link, Navigate, Route, Routes } from "react-router-dom";
import Dashboard from "./pages/Dashboard";
import NewRoadmap from "./pages/NewRoadmap";
import RoadmapView from "./pages/RoadmapView";

function Header() {
  return (
    <header className="topbar">
      <Link to="/" className="brand">
        Roadmap Studio
      </Link>
      <nav>
        <Link to="/new" className="btn small">
          + New roadmap
        </Link>
      </nav>
    </header>
  );
}

export default function App() {
  return (
    <>
      <Header />
      <main className="container">
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/new" element={<NewRoadmap />} />
          <Route path="/roadmaps/:id" element={<RoadmapView />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </main>
    </>
  );
}
