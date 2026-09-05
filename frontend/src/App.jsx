import { useState } from "react";

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

const schema = [
  { name: "airports", rows: "104", columns: ["airport_code", "airport_name", "city"] },
  { name: "bookings", rows: "1.1M", columns: ["book_ref", "book_date", "total_amount"] },
  { name: "flights", rows: "214K", columns: ["flight_id", "flight_no", "status", "route_no"] },
  { name: "routes", rows: "787", columns: ["route_no", "departure_airport", "arrival_airport"] },
];

const metrics = [
  ["Tables", "2", "database"],
  ["Joins", "1", "merge"],
  ["Filters", "1", "filter"],
  ["Plan depth", "2", "layers"],
];

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
  };
  return <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">{paths[name]}</svg>;
}

function App() {
  const [query, setQuery] = useState(sampleQuery);
  const [activeTab, setActiveTab] = useState("Results");
  const [expandedTable, setExpandedTable] = useState("flights");

  return <main className="app-shell">
    <header className="topbar">
      <a className="brand" href="#workspace" aria-label="QueryLens workspace"><span className="brand-mark"><Icon name="spark" size={17} /></span><span>Query<span>Lens</span></span></a>
      <div className="workspace-crumb"><span>Workspace</span><i /> <strong>Airlines demo</strong></div>
      <div className="topbar-actions"><span className="connection"><b /> Connected <span>demo</span></span><button className="icon-button" aria-label="Settings"><Icon name="settings" /></button><div className="avatar">RP</div></div>
    </header>

    <section className="workspace" id="workspace">
      <aside className="schema-panel">
        <div className="panel-heading"><div><p className="eyebrow">Database</p><h2><Icon name="database" /> demo</h2></div><button className="more-button" aria-label="Database options">•••</button></div>
        <label className="search"><Icon name="search" size={16} /><input placeholder="Search schema" /></label>
        <div className="schema-label"><Icon name="chevron" size={16} /><span>bookings</span><em>4</em></div>
        <div className="table-list">{schema.map((table) => <div className="schema-table" key={table.name}>
          <button className={`schema-table-button ${expandedTable === table.name ? "selected" : ""}`} onClick={() => setExpandedTable(expandedTable === table.name ? "" : table.name)}><Icon name="chevron" size={15} /><Icon name="database" size={15} /><span>{table.name}</span><em>{table.rows}</em></button>
          {expandedTable === table.name && <ul>{table.columns.map((column, index) => <li key={column}><span className={index === 0 ? "key-dot" : "column-dot"} />{column}</li>)}</ul>}
        </div>)}</div>
        <div className="schema-footer"><span>4 tables</span><span>•</span><span>1.3M rows</span></div>
      </aside>

      <section className="query-panel">
        <div className="query-header"><div><p className="eyebrow">Query editor</p><h1>Flight status overview</h1></div><span className="saved-state">Saved just now</span></div>
        <div className="editor-card"><div className="editor-toolbar"><div className="file-pill"><Icon name="code" size={16} />query.sql</div><span>PostgreSQL</span></div><textarea aria-label="SQL query editor" spellCheck="false" value={query} onChange={(event) => setQuery(event.target.value)} />
          <div className="editor-footer"><span><i className="live-dot" /> Ready to analyze</span><span>{query.split("\n").length} lines</span></div></div>
        <div className="action-row"><button className="button button-run"><Icon name="play" size={16} />Run query</button><button className="button button-estimate"><Icon name="chart" size={17} />Estimate</button><button className="button button-optimize"><Icon name="spark" size={17} />Optimize</button><button className="clear-button" onClick={() => setQuery("")}>Clear</button></div>
        <section className="results-card"><div className="tabs">{["Results", "Query plan", "Features", "Optimized SQL"].map((tab) => <button key={tab} onClick={() => setActiveTab(tab)} className={activeTab === tab ? "active" : ""}>{tab}</button>)}</div>
          {activeTab === "Results" ? <div className="results"><div className="result-meta"><span>50 rows returned</span><span>Execution time <strong>4.28 ms</strong></span></div><table><thead><tr><th>flight_id</th><th>flight_no</th><th>status</th><th>departure_airport</th><th>arrival_airport</th></tr></thead><tbody><tr><td>136029</td><td>PG0400</td><td><span className="status-pill">Scheduled</span></td><td>LED</td><td>SVO</td></tr><tr><td>136047</td><td>PG0402</td><td><span className="status-pill">Scheduled</span></td><td>DME</td><td>LED</td></tr></tbody></table></div> : <div className="tab-placeholder"><Icon name={activeTab === "Query plan" ? "layers" : activeTab === "Features" ? "chart" : "spark"} size={24} /><p>{activeTab} will appear after you analyze the query.</p></div>}</section>
      </section>

      <aside className="insights-panel"><div className="insight-heading"><div><p className="eyebrow">Query insights</p><h2>Estimated profile</h2></div><button className="more-button" aria-label="Insight options">•••</button></div>
        <article className="cost-card"><div className="cost-card-top"><span className="cost-badge">Medium cost</span><span className="trend">↗ 12%</span></div><div className="confidence"><span>Model confidence</span><strong>91%</strong></div><div className="confidence-bar"><i /></div><div className="cost-numbers"><div><strong>245.6<span>ms</span></strong><p>Predicted time</p></div><div><strong>684.2</strong><p>PostgreSQL cost</p></div></div></article>
        <div className="metric-grid">{metrics.map(([label, value, icon]) => <article className="metric" key={label}><span className="metric-icon"><Icon name={icon} size={16} /></span><strong>{value}</strong><p>{label}</p></article>)}</div>
        <article className="plan-card"><div className="plan-title"><span className="metric-icon"><Icon name="layers" size={16} /></span><div><h3>Plan signals</h3><p>PostgreSQL EXPLAIN</p></div></div><div className="signal"><span>Sequential scans</span><b className="warning">1</b></div><div className="signal"><span>Index scans</span><b>1</b></div><div className="signal"><span>Estimated rows</span><b>10,842</b></div></article>
        <article className="tip-card"><span className="tip-icon"><Icon name="spark" size={16} /></span><div><h3>Optimization opportunity</h3><p>An index on <code>flights.status</code> could reduce the sequential scan.</p><button>Explore optimization <span>→</span></button></div></article>
      </aside>
    </section>
  </main>;
}

export default App;
