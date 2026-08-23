import { useState } from "react";

const NAV_ITEMS = [
  { key: "DASHBOARD", label: "Dashboard" },
  { key: "DISCOVER", label: "Discover Jobs" },
  { key: "APPLICATIONS", label: "Applications" },
  { key: "RESUME", label: "Resume" },
  { key: "PROFILE", label: "Profile" },
];

export default function TopNav({ activePage, onNavigate }) {
  const [open, setOpen] = useState(false);

  const go = (key) => {
    onNavigate(key);
    setOpen(false);
  };

  return (
    <nav className="top-navbar" aria-label="Main navigation">
      <div className="top-navbar-inner">
        <div className="brand">
          <span className="brand-mark" aria-hidden="true">AI</span>
          Career Assistant
        </div>
        <div className={`nav-links ${open ? "open" : ""}`}>
          {NAV_ITEMS.map((item) => (
            <button
              key={item.key}
              className={`nav-link ${activePage === item.key ? "active" : ""}`}
              onClick={() => go(item.key)}
              aria-current={activePage === item.key ? "page" : undefined}
            >
              {item.label}
            </button>
          ))}
        </div>
        <button
          className="nav-mobile-toggle"
          onClick={() => setOpen(!open)}
          aria-expanded={open}
          aria-label="Toggle navigation menu"
        >
          {open ? "Close" : "Menu"}
        </button>
      </div>
    </nav>
  );
}
