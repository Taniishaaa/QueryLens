import { useEffect, useState } from "react";
import { connectDatabase, getHealth } from "./api";

const sampleQuery = `SELECT
  f.flight_id,
  f.flight_no,
  f.status,
  r.departure_airport,
  r.arrival_airport
FROM bookings.flights AS f
JOIN bookings.routes AS r ON f.route_no = r.route_no
WHERE f.status = 'Scheduled'
ORDER BY f.scheduled_departure
LIMIT 50;`;

const tabs = ["Results", "Query plan", "Features", "Optimized SQL"];

function Icon({ name, size = 18 }) {
  const paths = {
    spark: <path d="m12 2 1.6 6.4L20 10l-6.4 1.6L12 18l-1.6-6.4L4 10l6.4-1.6L12 2Z" />,
    database: <><ellipse cx="12" cy="5" rx="7" ry="3" /><path d="M5 5v7c0 1.66 3.13 3 7 3s7-1.34 7-3V5M5 12v7c0 1.66 3.13 3 7 3s7-1.34 7-3v-7" /></>,
    chevron: <path d="m8 10 4 4 4-4" />,
    search: <><circle cx="11" cy="11" r="6" /><path d="m16 16 4 4" /></>,
    play: <path d="m8 5 11 7-11 7V5Z" />,
    chart: <><path d="M4 19V5M4 19h16" /><path d="m7 15 4-4 3 2 5-6" /></>,
    code: <path d="m8 9-3 3 3 3M16 9l3 3-3 3M14 5l-4 14" />,
    layers: <><path d="m12 3 8 4-8 4-8-4 8-4Z" /><path d="m4 12 8 4 8-4M4 17l8 4 8-4" /></>,
    filter: <path d="M4 5h16l-6 7v5l-4 2v-7L4 5Z" />,
    merge: <><path d="M7 4v4c0 4 3 4 5 4h5" /><path d="m14 8 3 4-3 4" /><path d="M7 20v-4c0-4 3-4 5-4" /></>,
    settings: <><circle cx="12" cy="12" r="3" /><path d="M19.4 15a1.7 1.7 0 0 0 .34 1.88l.06.06-2.68 2.68-.06-.06a1.7 1.7 0 0 0-1.88-.34 1.7 1.7 0 0 0-1.03 1.56V21h-3.8v-.22a1.7 1.7 0 0 0-1.03-1.56 1.7 1.7 0 0 0-1.88.34l-.06.06-2.68-2.68.06-.06A1.7 1.7 0 0 0 5.1 15a1.7 1.7 0 0 0-1.56-1.03H3.3v-3.8h.23A1.7 1.7 0 0 0 5.1 9.14a1.7 1.7 0 0 0-.34-1.88l-.06-.06 2.68-2.68.06.06a1.7 1.7 0 0 0 1.88.34 1.7 1.7 0 0 0 1.03-1.56V3.15h3.8v.22a1.7 1.7 0 0 0 1.03 1.56 1.7 1.7 0 0 0 1.88-.34l.06-.06 2.68 2.68-.06.06a1.7 1.7 0 0 0-.34 1.88 1.7 1.7 0 0 0 1.56 1.03h.22v3.8h-.22A1.7 1.7 0 0 0 19.4 15Z" /></>,
    close: <path d="m6 6 12 12M18 6 6 18" />,
    shield: <><path d="M12 3 5 6v5c0 4.5 3 7.5 7 10 4-2.5 7-5.5 7-10V6l-7-3Z" /><path d="m9 12 2 2 4-4" /></>,
    refresh: <><path d="M20 11a8 8 0 0 0-14.9-3L3 10" /><path d="M3 4v6h6M4 13a8 8 0 0 0 14.9 3L21 14" /><path d="M21 20v-6h-6" /></>,
  };

  return <svg aria-hidden="true" fill="none" height={size} stroke="currentColor" strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.8" viewBox="0 0 24 24" width={size}>{paths[name]}</svg>;
}

function formatCount(value) {
  if (value === null || value === undefined || value < 0) return "—";
  return new Intl.NumberFormat("en", { notation: "compact", maximumFractionDigits: 1 }).format(value);
}

function ConnectionModal({ isOpen, isSubmitting, onClose, onConnect, error }) {
  const [connectionString, setConnectionString] = useState("");

  if (!isOpen) return null;

  function submit(event) {
    event.preventDefault();
    onConnect(connectionString);
  }

  return <div className="modal-backdrop" role="presentation">
    <section aria-labelledby="connect-title" aria-modal="true" className="connection-modal" role="dialog">
      <button aria-label="Close connection dialog" className="modal-close" disabled={isSubmitting} onClick={onClose}><Icon name="close" /></button>
      <span className="modal-icon"><Icon name="database" size={22} /></span>
      <p className="eyebrow">PostgreSQL connection</p>
      <h2 id="connect-title">Connect your database</h2>
      <p className="modal-copy">QueryLens reads your schema so you can explore tables, run safe queries, and analyze performance.</p>
      <form onSubmit={submit}>
        <label htmlFor="connection-string">Connection string</label>
        <input autoComplete="off" autoFocus disabled={isSubmitting} id="connection-string" onChange={(event) => setConnectionString(event.target.value)} placeholder="postgresql://user:password@host:5432/database" required type="password" value={connectionString} />
        {error && <p aria-live="polite" className="form-error">{error}</p>}
        <button className="connect-button" disabled={isSubmitting || !connectionString.trim()} type="submit">{isSubmitting ? "Connecting…" : "Connect database"}</button>
      </form>
      <p className="security-note"><Icon name="shield" size={15} /> Your connection string is sent only to the configured QueryLens backend and is not stored by this frontend.</p>
    </section>
  </div>;
}

function SchemaExplorer({ metadata, onConnect }) {
  const [searchTerm, setSearchTerm] = useState("");
  const [expandedTable, setExpandedTable] = useState("");
  const normalizedSearch = searchTerm.trim().toLowerCase();
  const tables = metadata?.tables ?? [];
  const schemas = metadata?.schemas ?? [];
  const matchingTables = tables.filter((table) => {
    const fields = [table.schema, table.table, ...table.columns.map((column) => column.column_name)];
    return fields.some((field) => field.toLowerCase().includes(normalizedSearch));
  });

  return <aside className="schema-panel">
    <div className="panel-heading"><div><p className="eyebrow">Database</p><h2><Icon name="database" /> {metadata?.database_name || "Not connected"}</h2></div><button aria-label="Connect another database" className="more-button" onClick={onConnect}>•••</button></div>
    <label className="search"><Icon name="search" size={16} /><input aria-label="Search database schema" disabled={!metadata} onChange={(event) => setSearchTerm(event.target.value)} placeholder="Search schema" value={searchTerm} /></label>
    {!metadata ? <div className="schema-empty"><Icon name="database" size={25} /><strong>Connect a database</strong><p>Tables and columns will appear here after you connect.</p><button onClick={onConnect}>Connect database</button></div> : <div className="schema-list">
      {schemas.map((schema) => {
        const schemaTables = matchingTables.filter((table) => table.schema === schema);
        if (!schemaTables.length) return null;
        return <section className="schema-group" key={schema}>
          <div className="schema-label"><Icon name="chevron" size={16} /><span>{schema}</span><em>{schemaTables.length}</em></div>
          {schemaTables.map((table) => {
            const tableId = `${table.schema}.${table.table}`;
            const isExpanded = expandedTable === tableId;
            return <div className="schema-table" key={tableId}>
              <button aria-expanded={isExpanded} className={`schema-table-button ${isExpanded ? "selected" : ""}`} onClick={() => setExpandedTable(isExpanded ? "" : tableId)}><Icon name="chevron" size={15} /><Icon name="database" size={15} /><span>{table.table}</span><em>{formatCount(table.estimated_row_count)}</em></button>
              {isExpanded && <ul>{table.columns.map((column) => <li key={column.column_name}><span className={column.is_nullable === "NO" ? "key-dot" : "column-dot"} /><span>{column.column_name}</span><small>{column.data_type}</small></li>)}</ul>}
            </div>;
          })}
        </section>;
      })}
      {!matchingTables.length && <p className="no-match">No tables or columns match “{searchTerm}”.</p>}
    </div>}
    {metadata && <div className="schema-footer"><span>{metadata.table_count} tables</span><span>•</span><span>{schemas.length} schemas</span></div>}
  </aside>;
}

function App() {
  const [query, setQuery] = useState(sampleQuery);
  const [activeTab, setActiveTab] = useState("Results");
  const [metadata, setMetadata] = useState(null);
  const [connectionStatus, setConnectionStatus] = useState("checking");
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [connectionError, setConnectionError] = useState("");

  useEffect(() => {
    let isCurrent = true;
    getHealth()
      .then(({ connected }) => {
        if (!isCurrent) return;
        setConnectionStatus(connected ? "connected" : "disconnected");
        setIsModalOpen(!connected);
      })
      .catch(() => {
        if (!isCurrent) return;
        setConnectionStatus("offline");
        setIsModalOpen(true);
        setConnectionError("QueryLens could not reach the backend. Start the API server and try again.");
      });
    return () => { isCurrent = false; };
  }, []);

  async function handleConnect(connectionString) {
    setIsSubmitting(true);
    setConnectionError("");
    try {
      const result = await connectDatabase(connectionString.trim());
      setMetadata(result.metadata);
      setConnectionStatus("connected");
      setIsModalOpen(false);
    } catch (error) {
      setConnectionStatus("disconnected");
      setConnectionError(error.message);
    } finally {
      setIsSubmitting(false);
    }
  }

  const isConnected = connectionStatus === "connected";
  const databaseName = metadata?.database_name || (isConnected ? "Active session" : "Not connected");

  return <main className="app-shell">
    <header className="topbar">
      <a className="brand" href="#workspace"><span className="brand-mark"><Icon name="spark" size={17} /></span><span>Query<span>Lens</span></span></a>
      <div className="workspace-crumb"><span>Workspace</span><i /> <strong>{databaseName}</strong></div>
      <div className="topbar-actions"><button className={`connection ${connectionStatus}`} onClick={() => setIsModalOpen(true)}><b /> {connectionStatus === "checking" ? "Checking connection" : isConnected ? "Connected" : "Connect database"}<span>{metadata?.database_name || "PostgreSQL"}</span></button><button aria-label="Refresh connection status" className="icon-button" onClick={() => window.location.reload()}><Icon name="refresh" /></button><button aria-label="Settings" className="icon-button"><Icon name="settings" /></button><div aria-label="Current user" className="avatar">QL</div></div>
    </header>

    <section className="workspace" id="workspace">
      <SchemaExplorer metadata={metadata} onConnect={() => { setConnectionError(""); setIsModalOpen(true); }} />
      <section className="query-panel">
        <div className="query-header"><div><p className="eyebrow">Query editor</p><h1>Flight status overview</h1></div><span className="saved-state">Saved locally</span></div>
        {!isConnected && <div className="connection-banner"><Icon name="database" size={17} /><span>Connect a database before running or analyzing this query.</span><button onClick={() => setIsModalOpen(true)}>Connect now</button></div>}
        <div className="editor-card"><div className="editor-toolbar"><div className="file-pill"><Icon name="code" size={16} />query.sql</div><span>PostgreSQL</span></div><textarea aria-label="SQL query editor" spellCheck="false" value={query} onChange={(event) => setQuery(event.target.value)} /><div className="editor-footer"><span><i className="live-dot" /> {isConnected ? "Ready to analyze" : "Waiting for database"}</span><span>{query.split("\n").length} lines</span></div></div>
        <div className="action-row"><button className="button button-run" disabled={!isConnected}><Icon name="play" size={16} />Run query</button><button className="button button-estimate" disabled={!isConnected}><Icon name="chart" size={17} />Estimate</button><button className="button button-optimize" disabled={!isConnected}><Icon name="spark" size={17} />Optimize</button><button className="clear-button" onClick={() => setQuery("")}>Clear</button></div>
        <section className="results-card"><div className="tabs">{tabs.map((tab) => <button className={activeTab === tab ? "active" : ""} key={tab} onClick={() => setActiveTab(tab)}>{tab}</button>)}</div><div className="tab-placeholder"><Icon name={activeTab === "Query plan" ? "layers" : activeTab === "Features" ? "chart" : activeTab === "Optimized SQL" ? "spark" : "database"} size={24} /><p>{isConnected ? `${activeTab} will appear after you analyze the query.` : "Connect a database to start exploring query results."}</p></div></section>
      </section>

      <aside className="insights-panel"><div className="insight-heading"><div><p className="eyebrow">Connection status</p><h2>{isConnected ? "Database ready" : "Awaiting connection"}</h2></div><span className={`state-dot ${connectionStatus}`} /></div><article className="connection-card"><span className="metric-icon"><Icon name="database" size={17} /></span><h3>{databaseName}</h3><p>{isConnected ? metadata ? `${metadata.table_count} tables discovered across ${metadata.schemas.length} schemas.` : "A backend session is connected. Reconnect to load schema metadata in this browser." : connectionStatus === "offline" ? "The backend is unavailable." : "Connect PostgreSQL to unlock query analysis."}</p><button onClick={() => setIsModalOpen(true)}>{isConnected ? "Switch database" : "Connect database"} <span>→</span></button></article><div className="phase-note"><span>Phase 2 complete</span><p>Connection state and schema discovery are live. Query execution and analysis arrive next.</p></div></aside>
    </section>
    <ConnectionModal error={connectionError} isOpen={isModalOpen} isSubmitting={isSubmitting} onClose={() => { if (!isSubmitting) setIsModalOpen(false); }} onConnect={handleConnect} />
  </main>;
}

export default App;
