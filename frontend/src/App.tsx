import { useEffect, useState } from "react";
import * as api from "./api";
import type { User } from "./api";
import Layout, { type SectionId } from "./components/Layout";
import { Spinner } from "./components/ui";
import Login from "./pages/Login";
import DemoLogin from "./pages/DemoLogin";
import { isDemoLoginEnabled } from "./demoLogin";
import Dashboard from "./pages/Dashboard";
import Opportunities from "./pages/Opportunities";
import Applications from "./pages/Applications";
import AcademicReview from "./pages/AcademicReview";
import Policies from "./pages/Policies";
import Documents from "./pages/Documents";
import DocumentReview from "./pages/DocumentReview";
import Activation from "./pages/Activation";

const SECTIONS: SectionId[] = [
  "home",
  "opportunities",
  "applications",
  "academic",
  "policies",
  "documents",
  "docreview",
  "activation",
];

function sectionFromHash(): SectionId {
  const h = window.location.hash.replace(/^#\/?/, "");
  return (SECTIONS as string[]).includes(h) ? (h as SectionId) : "home";
}

function canAccessSection(user: User, section: SectionId): boolean {
  if (section === "home" || section === "opportunities") return true;
  const roles = user.roles.map((role) => role.role);
  if (section === "applications" || section === "documents") return roles.includes("STUDENT");
  if (section === "academic" || section === "policies") return roles.includes("PROGRAM_COORDINATOR");
  if (section === "docreview") return roles.includes("LEGAL_REVIEWER");
  if (section === "activation") return roles.includes("EXPERIENTIAL_COORDINATOR");
  return false;
}

export default function App() {
  const [user, setUser] = useState<User | null>(null);
  const [checking, setChecking] = useState(true);
  const [tab, setTab] = useState<SectionId>(sectionFromHash());
  const [showDemoLogin, setShowDemoLogin] = useState(window.location.hash === "#/demo-login");

  // Hash router: keeps sections addressable (#/opportunities, #/activation, …).
  useEffect(() => {
    const onHash = () => {
      setTab(sectionFromHash());
      setShowDemoLogin(window.location.hash === "#/demo-login");
    };
    window.addEventListener("hashchange", onHash);
    return () => window.removeEventListener("hashchange", onHash);
  }, []);

  useEffect(() => {
    if (user && !canAccessSection(user, tab)) {
      window.location.hash = "/home";
      setTab("home");
    }
  }, [user, tab]);

  // Session restore on refresh / direct access.
  useEffect(() => {
    api.me()
      .then(setUser)
      .catch(() => setUser(null))
      .finally(() => setChecking(false));
  }, []);

  function navigate(s: SectionId) {
    window.location.hash = `/${s}`;
    setTab(s);
  }

  async function logout() {
    try {
      await api.logout();
    } catch {
      // Always clear local UI state; the server-side cookie expires if the request failed.
    }
    setUser(null);
    window.location.hash = "/login";
  }

  if (checking) {
    return (
      <div className="auth-wrap">
        <Spinner />
      </div>
    );
  }

  if (!user) {
    if (isDemoLoginEnabled() && showDemoLogin) {
      return (
        <DemoLogin
          onBack={() => { window.location.hash = "/login"; }}
          onLoggedIn={(u) => {
            setUser(u);
            navigate("home");
          }}
        />
      );
    }

    return (
      <Login
        onLoggedIn={(u) => {
          setUser(u);
          navigate(sectionFromHash());
        }}
      />
    );
  }

  const visibleTab = canAccessSection(user, tab) ? tab : "home";

  return (
    <Layout user={user} active={visibleTab} onNavigate={navigate} onLogout={logout}>
      {visibleTab === "home" && <Dashboard user={user} onNavigate={navigate} />}
      {visibleTab === "opportunities" && <Opportunities user={user} />}
      {visibleTab === "applications" && <Applications onNavigate={navigate} />}
      {visibleTab === "academic" && <AcademicReview />}
      {visibleTab === "policies" && <Policies />}
      {visibleTab === "documents" && <Documents />}
      {visibleTab === "docreview" && <DocumentReview />}
      {visibleTab === "activation" && <Activation />}
    </Layout>
  );
}
