import { Link, Navigate, Route, Routes, useLocation } from "react-router-dom";
import { useAuth } from "./auth";
import AuthPage from "./pages/AuthPage";
import Dashboard from "./pages/Dashboard";
import NewRoadmap from "./pages/NewRoadmap";
import RoadmapView from "./pages/RoadmapView";

function Protected({ children }) {
  const { user, loading } = useAuth();
  const location = useLocation();
  if (loading) return <p className="center muted">Loading…</p>;
  if (!user) return <Navigate to="/login" replace state={{ from: location }} />;
  return children;
}

function Header() {
  const { user, logout } = useAuth();
  return (
    <header className="topbar">
      <Link to="/" className="brand">
        Roadmap Studio
      </Link>
      {user && (
        <nav>
          <Link to="/new" className="btn small">
            + New roadmap
          </Link>
          <span className="muted hide-sm">{user.email}</span>
          <button className="btn small ghost" onClick={logout}>
            Log out
          </button>
        </nav>
      )}
    </header>
  );
}

export default function App() {
  return (
    <>
      <Header />
      <main className="container">
        <Routes>
          <Route path="/login" element={<AuthPage mode="login" />} />
          <Route path="/register" element={<AuthPage mode="register" />} />
          <Route path="/" element={<Protected><Dashboard /></Protected>} />
          <Route path="/new" element={<Protected><NewRoadmap /></Protected>} />
          <Route path="/roadmaps/:id" element={<Protected><RoadmapView /></Protected>} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </main>
    </>
  );
}
