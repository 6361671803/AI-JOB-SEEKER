import { useState } from "react";
import { ToastProvider } from "./context/ToastContext";
import TopNav from "./components/shared/TopNav";
import EmptyState from "./components/shared/EmptyState";
import Dashboard from "./components/pages/Dashboard";
import ResumeUpload from "./components/ResumeUpload";
import CandidateProfileView from "./components/CandidateProfileView";
import PreferencesForm from "./components/PreferencesForm";
import PreferencesSummary from "./components/PreferencesSummary";
import CompanyDiscovery from "./components/CompanyDiscovery";
import CompanyResults from "./components/CompanyResults";
import JobDiscovery from "./components/JobDiscovery";
import JobResults from "./components/JobResults";
import ApplicationApproval from "./components/ApplicationApproval";
import ApplicationPreparation from "./components/ApplicationPreparation";
import ApplicationTracker from "./components/ApplicationTracker";
import "./App.css";

const VIEW = {
  DASHBOARD: "DASHBOARD",
  UPLOAD: "UPLOAD",
  PROFILE_VIEW: "PROFILE_VIEW",
  PREFERENCES_WIZARD: "PREFERENCES_WIZARD",
  PREFERENCES_SAVED: "PREFERENCES_SAVED",
  DISCOVER_COMPANIES: "DISCOVER_COMPANIES",
  COMPANIES_FOUND: "COMPANIES_FOUND",
  DISCOVER_JOBS: "DISCOVER_JOBS",
  JOBS_FOUND: "JOBS_FOUND",
  APPLICATION_APPROVAL: "APPLICATION_APPROVAL",
  APPLICATION_PREPARATION: "APPLICATION_PREPARATION",
  APPLICATIONS_TRACKER: "APPLICATIONS_TRACKER",
};

// Which top-nav item should highlight as active for a given view.
const NAV_KEY_FOR_VIEW = {
  [VIEW.DASHBOARD]: "DASHBOARD",
  [VIEW.UPLOAD]: "RESUME",
  [VIEW.PROFILE_VIEW]: "RESUME",
  [VIEW.PREFERENCES_WIZARD]: "PROFILE",
  [VIEW.PREFERENCES_SAVED]: "PROFILE",
  [VIEW.DISCOVER_COMPANIES]: "DISCOVER",
  [VIEW.COMPANIES_FOUND]: "DISCOVER",
  [VIEW.DISCOVER_JOBS]: "DISCOVER",
  [VIEW.JOBS_FOUND]: "DISCOVER",
  [VIEW.APPLICATION_APPROVAL]: "APPLICATIONS",
  [VIEW.APPLICATION_PREPARATION]: "APPLICATIONS",
  [VIEW.APPLICATIONS_TRACKER]: "APPLICATIONS",
};

function AppContent() {
  const [view, setView] = useState(VIEW.UPLOAD);
  const [candidate, setCandidate] = useState(null);
  const [preferences, setPreferences] = useState(null);
  const [companyResult, setCompanyResult] = useState(null);
  const [jobResult, setJobResult] = useState(null);
  const [selectedJobs, setSelectedJobs] = useState([]);

  const handleResumeAnalyzed = (result) => {
    setCandidate(result);
    setView(VIEW.PROFILE_VIEW);
  };

  const handleStartOver = () => {
    setCandidate(null);
    setPreferences(null);
    setCompanyResult(null);
    setJobResult(null);
    setSelectedJobs([]);
    setView(VIEW.UPLOAD);
  };

  const handlePreferencesSaved = (result) => {
    setPreferences(result.preferences);
    setView(VIEW.PREFERENCES_SAVED);
  };

  const handleCompaniesDiscovered = (result) => {
    setCompanyResult(result);
    setView(VIEW.COMPANIES_FOUND);
  };

  const handleJobsDiscovered = (result) => {
    setJobResult(result);
    setView(VIEW.JOBS_FOUND);
  };

  const handleSelectionApproved = (jobs) => {
    setSelectedJobs(jobs);
    setView(VIEW.APPLICATION_APPROVAL);
  };

  const handleNavigate = (navKey) => {
    switch (navKey) {
      case "DASHBOARD":
        setView(VIEW.DASHBOARD);
        break;
      case "RESUME":
        setView(candidate ? VIEW.PROFILE_VIEW : VIEW.UPLOAD);
        break;
      case "PROFILE":
        if (!candidate) setView(VIEW.UPLOAD);
        else setView(preferences ? VIEW.PREFERENCES_SAVED : VIEW.PREFERENCES_WIZARD);
        break;
      case "DISCOVER":
        if (!candidate) setView(VIEW.UPLOAD);
        else if (!preferences) setView(VIEW.PREFERENCES_WIZARD);
        else if (jobResult) setView(VIEW.JOBS_FOUND);
        else if (companyResult) setView(VIEW.COMPANIES_FOUND);
        else setView(VIEW.DISCOVER_COMPANIES);
        break;
      case "APPLICATIONS":
        setView(candidate ? VIEW.APPLICATIONS_TRACKER : VIEW.UPLOAD);
        break;
      default:
        break;
    }
  };

  const needsResume = (
    <EmptyState icon="📄" title="Your career search starts with your resume">
      <div className="button-row" style={{ justifyContent: "center" }}>
        <button className="btn btn-primary" onClick={() => setView(VIEW.UPLOAD)}>Upload Resume</button>
      </div>
    </EmptyState>
  );

  return (
    <div className="app-root">
      {view !== VIEW.UPLOAD && (
        <TopNav activePage={NAV_KEY_FOR_VIEW[view] || "DASHBOARD"} onNavigate={handleNavigate} />
      )}

      <main className={`app-main ${view === VIEW.UPLOAD ? "app-main--narrow" : ""}`}>
        {view === VIEW.DASHBOARD && (
          candidate ? (
            <Dashboard
              candidate={candidate}
              preferences={preferences}
              companyResult={companyResult}
              jobResult={jobResult}
              onNavigate={handleNavigate}
            />
          ) : needsResume
        )}

        {view === VIEW.UPLOAD && <ResumeUpload onAnalyzed={handleResumeAnalyzed} />}

        {view === VIEW.PROFILE_VIEW && candidate && (
          <CandidateProfileView
            candidate={candidate}
            onStartOver={handleStartOver}
            onContinue={() => setView(preferences ? VIEW.PREFERENCES_SAVED : VIEW.PREFERENCES_WIZARD)}
          />
        )}

        {view === VIEW.PREFERENCES_WIZARD && (candidate ? (
          <PreferencesForm candidateId={candidate.id} onSaved={handlePreferencesSaved} />
        ) : needsResume)}

        {view === VIEW.PREFERENCES_SAVED && preferences && (
          <PreferencesSummary
            preferences={preferences}
            onEdit={() => setView(VIEW.PREFERENCES_WIZARD)}
            onContinue={() => setView(VIEW.DISCOVER_COMPANIES)}
          />
        )}

        {view === VIEW.DISCOVER_COMPANIES && (candidate ? (
          <CompanyDiscovery candidateId={candidate.id} onDiscovered={handleCompaniesDiscovered} />
        ) : needsResume)}

        {view === VIEW.COMPANIES_FOUND && companyResult && (
          <CompanyResults
            result={companyResult}
            onRediscover={() => setView(VIEW.DISCOVER_COMPANIES)}
            onContinue={() => setView(VIEW.DISCOVER_JOBS)}
          />
        )}

        {view === VIEW.DISCOVER_JOBS && candidate && (
          <JobDiscovery candidateId={candidate.id} onDiscovered={handleJobsDiscovered} />
        )}

        {view === VIEW.JOBS_FOUND && jobResult && candidate && (
          <JobResults
            candidateId={candidate.id}
            result={jobResult}
            companiesDiscoveredCount={companyResult ? companyResult.companies.length : 0}
            onRediscover={() => setView(VIEW.DISCOVER_JOBS)}
            onResultChange={setJobResult}
            onSelectionApproved={handleSelectionApproved}
          />
        )}

        {view === VIEW.APPLICATION_APPROVAL && candidate && (
          <ApplicationApproval
            candidateId={candidate.id}
            selectedJobs={selectedJobs}
            onBack={() => setView(VIEW.JOBS_FOUND)}
            onApproved={() => setView(VIEW.APPLICATION_PREPARATION)}
          />
        )}

        {view === VIEW.APPLICATION_PREPARATION && candidate && (
          <ApplicationPreparation candidateId={candidate.id} selectedJobs={selectedJobs} />
        )}

        {view === VIEW.APPLICATIONS_TRACKER && (candidate ? (
          <ApplicationTracker candidateId={candidate.id} onBack={() => setView(VIEW.DASHBOARD)} />
        ) : needsResume)}
      </main>
    </div>
  );
}

export default function App() {
  return (
    <ToastProvider>
      <AppContent />
    </ToastProvider>
  );
}
