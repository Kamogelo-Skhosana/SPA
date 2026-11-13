import { useEffect, useRef, useState } from "react";
import { filterRoutes, normalizeRoute, routes, type RoutePath } from "./navigation";

import RunFlow from "./RunFlow";
import SettingsScreens from "./SettingsScreens";

const symbols: Record<RoutePath, string> = {
  "/overview": "◫",
  "/payables": "▤",
  "/mandate": "◇",
  "/setup": "⚙",
};

function useRoute() {
  const [route, setRoute] = useState<RoutePath>(() => normalizeRoute(window.location.hash));
  useEffect(() => {
    const onHash = () => setRoute(normalizeRoute(window.location.hash));
    window.addEventListener("hashchange", onHash);
    return () => window.removeEventListener("hashchange", onHash);
  }, []);
  return route;
}

export default function App() {
  const route = useRoute();
  const [menuOpen, setMenuOpen] = useState(false);
  const [searchOpen, setSearchOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [workspace, setWorkspace] = useState("Demo workspace");
  const menuButton = useRef<HTMLButtonElement>(null);
  const searchInput = useRef<HTMLInputElement>(null);
  const searchButton = useRef<HTMLButtonElement>(null);
  const searchDialog = useRef<HTMLElement>(null);
  const current = routes.find((item) => item.path === route)!;
  const matches = filterRoutes(query);

  useEffect(() => {
    setMenuOpen(false);
    setSearchOpen(false);
    setQuery("");
  }, [route]);

  useEffect(() => {
    if (!searchOpen) return;
    const previous = document.activeElement as HTMLElement | null;
    searchInput.current?.focus();
    return () => previous?.focus();
  }, [searchOpen]);

  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "k") {
        event.preventDefault();
        setSearchOpen(true);
      }
      if (searchOpen && event.key === "Tab") {
        const controls = searchDialog.current?.querySelectorAll<HTMLElement>("input, button, a[href]");
        if (controls?.length) {
          const first = controls[0];
          const last = controls[controls.length - 1];
          if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last.focus(); }
          else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first.focus(); }
        }
      }
      if (event.key === "Escape") {
        if (menuOpen) {
          setMenuOpen(false);
          menuButton.current?.focus();
        }
        setSearchOpen(false);
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [menuOpen, searchOpen]);

  const navigation = (
    <nav aria-label="Primary navigation" className="navigation">
      {routes.map((item) => (
        <a key={item.path} href={`#${item.path}`}
          aria-current={item.path === route ? "page" : undefined}
          className={item.path === route ? "nav-link active" : "nav-link"}
          onClick={() => setMenuOpen(false)}>
          <span className="nav-icon" aria-hidden="true">{symbols[item.path]}</span>
          <span>{item.label}</span>
        </a>
      ))}
    </nav>
  );

  return (
    <div className="app-shell">
      <div className="testnet-banner" role="status">
        <span className="banner-dot" aria-hidden="true" />
        XRPL Testnet environment <span className="banner-divider" aria-hidden="true">·</span>
        <strong>Demo data is simulated</strong> — no real funds are moved
      </div>
      <div className="app-layout">
        {menuOpen && <button className="mobile-scrim" aria-label="Close navigation" onClick={() => setMenuOpen(false)} />}
        <aside id="workspace-sidebar" className={`sidebar ${menuOpen ? "sidebar-open" : ""}`} aria-label="Workspace sidebar">
          <a className="brand" href="#/overview" onClick={() => setMenuOpen(false)}>
            <span className="brand-mark" aria-hidden="true">S</span>
            <span><strong>SPA</strong><small>Agentic finance</small></span>
          </a>
          <label className="workspace-label" htmlFor="workspace">WORKSPACE</label>
          <select id="workspace" className="workspace-select" value={workspace}
            onChange={(event) => setWorkspace(event.target.value)}>
            <option>Demo workspace</option>
            <option>Sandbox workspace</option>
          </select>
          <div className="nav-heading">YOUR WORKSPACE</div>
          {navigation}
          <div className="sidebar-foot">
            <span className="environment-tag">● Simulated · Testnet</span>
            <span className="sidebar-note">Operator dashboard MVP</span>
          </div>
        </aside>
        <div className="content-shell">
          <header className="topbar">
            <button ref={menuButton} className="icon-button mobile-menu"
              aria-label={menuOpen ? "Close menu" : "Open menu"}
              aria-expanded={menuOpen} aria-controls="workspace-sidebar"
              onClick={() => setMenuOpen((value) => !value)}>☰</button>
            <div className="breadcrumb">Workspace <span aria-hidden="true">/</span> <strong>{current.label}</strong></div>
            <div className="top-actions">
              <button ref={searchButton} className="search-trigger" onClick={() => setSearchOpen(true)}
                aria-label="Search workspace pages">
                <span aria-hidden="true">⌕</span> <span className="search-label">Search pages</span>
                <kbd>⌘ K</kbd>
              </button>
              <div className="avatar" aria-label="Operator account">OP</div>
            </div>
          </header>
          <main id="main-content" className="main-content">
            <div className="page-heading">
              <div><p className="eyebrow">SPA / OPERATOR WORKSPACE</p><h1>{current.label}</h1>
                <p className="page-description">{current.description}</p></div>
              <span className="mode-pill">Simulated preview</span>
            </div>
            {route === "/mandate" || route === "/setup" ? <SettingsScreens screen={route === "/mandate" ? "mandate" : "setup"} /> : <><section className="placeholder-panel" aria-labelledby="screen-title">
              <span className="placeholder-symbol" aria-hidden="true">{symbols[route]}</span>
              <h2 id="screen-title">{current.label} screen</h2>
              <p>This section is a fixture-backed placeholder. Its interactive functionality will be delivered in the corresponding frontend ticket.</p>
              <span className="placeholder-status">Not connected to live services</span>
            </section><RunFlow /></>}
          </main>
        </div>
      </div>
      {searchOpen && <div className="dialog-backdrop" onMouseDown={(event) => {
        if (event.target === event.currentTarget) setSearchOpen(false);
      }}>
        <section ref={searchDialog} className="search-dialog" role="dialog" aria-modal="true" aria-label="Search pages">
          <div className="dialog-search"><span aria-hidden="true">⌕</span>
            <input ref={searchInput} aria-label="Search pages" placeholder="Find a page…"
              value={query} onChange={(event) => setQuery(event.target.value)} />
            <button onClick={() => setSearchOpen(false)} aria-label="Close search">Esc</button>
          </div>
          <div className="search-results">
            {matches.length ? matches.map((item) => (
              <a href={`#${item.path}`} key={item.path} onClick={() => setSearchOpen(false)}>
                <strong>{item.label}</strong><span>{item.description}</span>
              </a>
            )) : <p className="no-results">No matching pages</p>}
          </div>
        </section>
      </div>}
    </div>
  );
}
