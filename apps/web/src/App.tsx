import { useEffect, useRef, useState } from "react";
import { filterRoutes, normalizeRoute, routes, type RoutePath } from "./navigation";

import Dashboard from "./Dashboard";
import SettingsScreens from "./SettingsScreens";
import { createApiWorkspace } from "./api-workspace";

const icons: Record<RoutePath, string> = {
  "/overview": "M3 3h7v7H3z M14 3h7v7h-7z M3 14h7v7H3z M14 14h7v7h-7z",
  "/payables": "M6 3h12v18H6z M9 8h6 M9 12h6 M9 16h4",
  "/mandate": "M12 3l8 3v6c0 4-4 7-8 9-4-2-8-5-8-9V6z M8 12l3 3 5-5",
  "/setup": "M3 7h18v13H3z M3 7l14-4v4 M15 11h6v5h-6z",
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
  const [apiWorkspace] = useState(() => {
    const endpoint = import.meta.env.VITE_SPA_API_URL?.trim();
    return endpoint ? createApiWorkspace(endpoint) : null;
  });
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
          <svg className="nav-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><path d={icons[item.path]} /></svg>
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
        <strong>{apiWorkspace ? 'Connected API' : 'Demo data is simulated'}</strong>{apiWorkspace ? ' · payment status is shown from the backend' : ' — no real funds are moved'}
      </div>
      <div className="app-layout">
        {menuOpen && <button className="mobile-scrim" aria-label="Close navigation" onClick={() => setMenuOpen(false)} />}
        <aside id="workspace-sidebar" className={`sidebar ${menuOpen ? "sidebar-open" : ""}`} aria-label="Workspace sidebar">
          <a className="brand" href="#/overview" onClick={() => setMenuOpen(false)}>
            <img className="brand-mark" src={`${import.meta.env.BASE_URL}spa-mark.svg`} alt="" width="44" height="44" />
            <span><strong>SPA</strong><small>Agentic finance</small></span>
          </a>
          <label className="workspace-label" htmlFor="workspace">WORKSPACE</label>
          <select id="workspace" className="workspace-select" defaultValue="Demo workspace">
            <option>Demo workspace</option>
            <option disabled>Sandbox workspace (unavailable)</option>
          </select>

          {navigation}
          <div className="sidebar-foot">
            <span className="environment-tag">● {apiWorkspace ? 'API connected' : 'Simulated · Testnet'}</span>
          </div>
        </aside>
        <div className="content-shell">
          <header className="topbar">
            <button ref={menuButton} className="icon-button mobile-menu"
              aria-label={menuOpen ? "Close menu" : "Open menu"}
              aria-expanded={menuOpen} aria-controls="workspace-sidebar"
              onClick={() => setMenuOpen((value) => !value)}>
              <svg className="ui-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" aria-hidden="true">
                <path d={menuOpen ? "m6 6 12 12M18 6 6 18" : "M4 6h16M4 12h16M4 18h16"} />
              </svg>
            </button>

            <div className="top-actions">
              <button ref={searchButton} className="search-trigger" onClick={() => setSearchOpen(true)}
                aria-label="Search workspace pages">
                <svg className="ui-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" aria-hidden="true"><circle cx="10.5" cy="10.5" r="5.5" /><path d="m15 15 5 5" /></svg> <span className="search-label">Search pages</span>
                <kbd>⌘ K</kbd>
              </button>
              <div className="avatar" aria-label="Operator account">OP</div>
            </div>
          </header>
          <main id="main-content" className="main-content">
            <div className="page-heading">
              <h1>{current.heading}</h1>
            </div>
            {route === "/mandate" || route === "/setup" ? <SettingsScreens key={route} screen={route === "/mandate" ? "mandate" : "setup"} adapter={apiWorkspace?.settings} /> : <Dashboard screen={route === "/overview" ? "overview" : "payables"} load={apiWorkspace?.loadDashboard} paymentAdapter={apiWorkspace?.payments} source={apiWorkspace ? 'api' : 'fixture'} />}
          </main>
        </div>
      </div>
      {searchOpen && <div className="dialog-backdrop" onMouseDown={(event) => {
        if (event.target === event.currentTarget) setSearchOpen(false);
      }}>
        <section ref={searchDialog} className="search-dialog" role="dialog" aria-modal="true" aria-label="Search pages">
          <div className="dialog-search"><svg className="ui-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" aria-hidden="true"><circle cx="10.5" cy="10.5" r="5.5" /><path d="m15 15 5 5" /></svg>
            <input ref={searchInput} aria-label="Search pages" placeholder="Find a page…"
              value={query} onChange={(event) => setQuery(event.target.value)}
              onKeyDown={(event) => {
                if (event.key !== "Enter" || event.nativeEvent.isComposing || matches.length !== 1) return;
                event.preventDefault();
                window.location.hash = matches[0].path;
                setSearchOpen(false);
                setQuery("");
              }} />
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
