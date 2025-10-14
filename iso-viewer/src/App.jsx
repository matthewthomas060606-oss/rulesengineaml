// /mnt/data/App.jsx
import React, { useEffect, useMemo, useState } from "react";

const BASE = (typeof import.meta !== "undefined" && import.meta.env && import.meta.env.BASE_URL) ? import.meta.env.BASE_URL : "/";
const FETCH_URLS = { latest: `${BASE}latest.json`, history: `${BASE}history.jsonl`, db: `${BASE}sanctions_index.json` };

const get = (o, p, d) => { try { return p.split(".").reduce((a, k) => (a && k in a ? a[k] : undefined), o) ?? d; } catch { return d; } };
const uniq = (a = []) => Array.from(new Set(a.filter(Boolean)));

function useData() {
  const [latest, setLatest] = useState(null);
  const [history, setHistory] = useState([]);
  const [db, setDb] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const reload = async () => {
    setLoading(true);
    setError(null);
    try {
      const l = await fetch(FETCH_URLS.latest, { cache: "no-store" });
      const latestJson = await l.json();
      const h = await fetch(FETCH_URLS.history, { cache: "no-store" });
      const historyText = await h.text();
      let hx = [];
      try {
        const lines = historyText.replace(/\r/g, "").split("\n");
        hx = lines.map(t => t.trim()).filter(Boolean).map(line => { try { return JSON.parse(line); } catch { return null; } }).filter(Boolean);
        if (hx.length === 0) {
          const maybeArray = JSON.parse(historyText);
          if (Array.isArray(maybeArray)) hx = maybeArray;
        }
      } catch {}
      let dbJson = [];
      try {
        const d = await fetch(FETCH_URLS.db, { cache: "no-store" });
        if (d.ok) dbJson = await d.json();
      } catch {}
      setLatest(latestJson);
      setHistory(hx);
      setDb(Array.isArray(dbJson) ? dbJson : []);
    } catch (e) { setError(String(e.message || e)); }
    finally { setLoading(false); }
  };
  useEffect(() => { reload(); }, []);
  return { latest, history, db, loading, error, reload };
}

const s = {
  page: { fontFamily: "system-ui,-apple-system,Segoe UI,Roboto,Arial,sans-serif", background: "#0b0f17", color: "#e5e7eb", minHeight: "100vh", width: "100vw", overflowX: "hidden" },
  container: { width: "100%", maxWidth: "none", margin: 0, padding: "0 12px" },
  header: { display: "flex", justifyContent: "space-between", alignItems: "center", padding: "12px 0", borderBottom: "1px solid #1f2937", background: "#111827", position: "sticky", top: 0, zIndex: 1 },
  tabs: { display: "flex", gap: 8 },
  tab: (active) => ({ padding: "6px 12px", borderRadius: 8, border: "1px solid #334155", background: active ? "#2563eb" : "#111827", color: active ? "#fff" : "#e5e7eb", cursor: "pointer", fontSize: 13, fontWeight: 700 }),
  section: { background: "#0f172a", border: "1px solid #1f2937", borderRadius: 10, padding: 16, marginTop: 12 },
  sectionTitle: { fontWeight: 800, marginBottom: 8, color: "#f3f4f6" },
  rowWrap: { display: "grid", gridTemplateColumns: "220px 1fr", padding: "8px 0", borderTop: "1px dashed #1f2937", gap: 12 },
  pre: { padding: 12, background: "#0a0f1a", color: "#cbd5e1", borderRadius: 8, overflow: "auto", fontSize: 12, lineHeight: 1.45, maxHeight: 420, border: "1px solid #1f2937" },
  btn: { background: "#2563eb", color: "#fff", border: "1px solid #1e40af", borderRadius: 6, padding: "6px 10px", cursor: "pointer", fontSize: 12 },
  tableScroll: { overflow: "auto", border: "1px solid #1f2937", borderRadius: 8, maxWidth: "100%" },
  table: { width: "100%", borderCollapse: "separate", borderSpacing: 0, tableLayout: "fixed" },
  th: { textAlign: "left", fontWeight: 700, fontSize: 12, padding: 10, borderBottom: "1px solid #1f2937", background: "#111827", color: "#e5e7eb", position: "sticky", top: 0, whiteSpace: "nowrap" },
  thWrap: { display: "flex", alignItems: "center", gap: 6, minWidth: 0 },
  td: { fontSize: 13, padding: 10, borderBottom: "1px solid #1f2937", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap", color: "#e5e7eb" },
  input: { padding: "8px 10px", borderRadius: 8, border: "1px solid #334155", width: "100%", maxWidth: 480, background: "#0b1220", color: "#e5e7eb" },
  chip: { display: "inline-block", padding: "2px 8px", borderRadius: 999, background: "#1f2937", color: "#93c5fd", fontSize: 12, marginRight: 6, border: "1px solid #334155" },
  colBtn: { border: "1px solid #334155", background: "#0b1220", color: "#e5e7eb", borderRadius: 6, padding: "0 6px", fontSize: 11, cursor: "pointer" },
  controls: { display: "flex", gap: 8, alignItems: "center", marginTop: 8, flexWrap: "wrap" }
};

function Row({ label, value }) {
  return (
    <div style={s.rowWrap}>
      <div style={{ color: "#cbd5e1" }}>{label}</div>
      <div style={{ fontWeight: 600, whiteSpace: "pre-wrap" }}>{value ?? "—"}</div>
    </div>
  );
}

function SummaryView({ item, loading, error, onRefresh }) {
  const when =
    get(item, "screening.engine.timeflagged") ||
    get(item, "riskSummary.time") ||
    get(item, "timeflagged") ||
    get(item, "engine.timeflagged");
  const whenNice = when ? new Date(when).toLocaleString() : "—";
  const matches = get(item, "screening.sanctionsScreening.matches", []) || [];
  const names = uniq(matches.map(m => m.subject_name));
  const roles = uniq(matches.map(m => m.role));
  const reasons = uniq([...(get(item, "decision.explanations", []) || []), ...matches.flatMap(m => m.reasons || [])]);
  const topRisk = get(item, "riskSummary.riskLevel") || "—";
  const riskScore = get(item, "riskSummary.riskScore");
  const action = get(item, "decision.recommendedAction") || "—";
  const listsTriggered = uniq(matches.map(m => m.sanctions_list)).join(", ");
  const idsByList = (() => {
    const m = new Map();
    for (const r of matches) {
      const list = r.sanctions_list || "—";
      const id = r.sanctions_id || "—";
      if (!m.has(list)) m.set(list, new Set());
      m.get(list).add(id);
    }
    return Array.from(m.entries()).map(([list, ids]) => `${list}: ${Array.from(ids).join(", ")}`).join("; ");
  })();
  const top3 = matches
    .slice(0, 3)
    .map(m => `${m.subject_name || "—"} → ${m.record_name || "—"} (${Math.round((m.certainty || 0) * 100)}%) [${m.sanctions_list || "—"}]`)
    .join("\n");
  return (
    <div>
      <section style={s.section}>
        <div style={s.sectionTitle}>Summary</div>
        {!item && <div style={{ color: "#94a3b8", fontSize: 14 }}>No data.</div>}
        {item && (
          <div>
            <Row label="Risk Level" value={`${topRisk}${riskScore != null ? ` (${riskScore})` : ""}`} />
            <Row label="Recommended Action" value={action} />
            <Row label="Name(s)" value={names.join(", ") || "—"} />
            <Row label="Role(s)" value={roles.join(", ") || "—"} />
            <Row label="Reason" value={reasons.join(" — ") || "—"} />
            <Row label="Top Matches" value={top3 || "—"} />
            <Row label="Triggered Lists" value={listsTriggered || "—"} />
            <Row label="Triggered IDs" value={idsByList || "—"} />
            <Row label="Time" value={whenNice} />
          </div>
        )}
      </section>
      <section style={s.section}>
        <div style={s.sectionTitle}>Raw JSON</div>
        <pre style={s.pre}>{item ? JSON.stringify(item, null, 2) : ""}</pre>
      </section>
      <div style={{ display: "flex", gap: 8, alignItems: "center", marginTop: 12 }}>
        {loading && <span style={{ color: "#94a3b8", fontSize: 12 }}>Loading…</span>}
        {error && <span style={{ color: "#f87171", fontSize: 12 }}>Error: {error}</span>}
        <button onClick={onRefresh} style={s.btn}>Refresh</button>
      </div>
    </div>
  );
}

function History({ history, onSelect, selectedIndex }) {
  return (
    <section style={s.section}>
      <div style={s.sectionTitle}>History</div>
      {history.length === 0 && <div style={{ color: "#94a3b8", fontSize: 14 }}>No history found.</div>}
      {history.length > 0 && (
        <div style={s.tableScroll}>
          <table style={s.table}>
            <thead>
              <tr>
                <th style={s.th}>When</th>
                <th style={s.th}>Names flagged</th>
                <th style={s.th}>Role(s)</th>
              </tr>
            </thead>
            <tbody>
              {history.map((h, i) => {
                const w =
                  get(h, "screening.engine.timeflagged") ||
                  get(h, "riskSummary.time") ||
                  get(h, "timeflagged") ||
                  get(h, "engine.timeflagged");
                const wNice = w ? new Date(w).toLocaleString() : "—";
                const matches = get(h, "screening.sanctionsScreening.matches", []) || [];
                const _names = Array.from(new Set(matches.map(m => m.subject_name).filter(Boolean))).join(", ");
                const _roles = Array.from(new Set(matches.map(m => m.role).filter(Boolean))).join(", ");
                return (
                  <tr key={i} onClick={() => onSelect(i)} style={{ cursor: "pointer", background: selectedIndex === i ? "#172554" : "transparent" }}>
                    <td style={s.td}>{wNice}</td>
                    <td style={s.td}>{_names || "—"}</td>
                    <td style={s.td}>{_roles || "—"}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}

const sName = (k) => {
  const map = {
    list_name: "List",
    list_id: "ID",
    primary_name: "Name",
    full_name: "Full Name",
    first_name: "First Name",
    middle_name: "Middle Name",
    last_name: "Last Name",
    aliases: "Aliases",
    target_type: "Target Type",
    sanctions_program_name: "Program",
    country: "Country",
    country_iso: "Country ISO",
    citizenship_country: "Citizenship Country",
    citizenship_country_iso: "Citizenship ISO",
    nationality: "Nationality",
    area: "Region/Area",
    location: "Town/Location",
    address_details: "Address",
    postal_code: "Postal Code",
    email_address: "Email",
    swift_bic: "SWIFT/BIC",
    iban: "IBAN",
    date_of_birth: "Date of Birth",
    dob: "Date of Birth",
    place_of_birth: "Place of Birth",
    gender: "Gender",
    identification_number: "ID Number",
    passport_number: "Passport Number",
    drivers_license_number: "Driver’s License",
    vehicle_registration: "Vehicle Registration",
    vessel_name: "Vessel Name",
    vessel_type: "Vessel Type",
    imo_number: "IMO Number",
    mmsi: "MMSI",
    call_sign: "Call Sign",
    flag: "Flag",
    tonnage: "Tonnage",
    gross_registered_tonnage: "Gross Tonnage",
    aircraft_model: "Aircraft Model",
    aircraft_manufacturer: "Aircraft Manufacturer",
    aircraft_registration: "Tail/Registration",
    aircraft_icao: "Aircraft ICAO"
  };
  if (map[k]) return map[k];
  const t = k.replace(/[_]+/g, " ").trim();
  return t.slice(0, 1).toUpperCase() + t.slice(1);
};

const keyLike = (k, needles) => needles.some(n => k.toLowerCase().includes(n));

function DbTab({ db }) {
  const [filters, setFilters] = useState([{ field: "", op: "contains", value: "" }]);
  const [page, setPage] = useState(1);
  const [colWidth, setColWidth] = useState(180);
  const [expandedCols, setExpandedCols] = useState({});
  const pageSize = 200;

  const allColumns = useMemo(() => {
    const keys = new Set();
    for (const r of db) Object.keys(r || {}).forEach(k => keys.add(k));
    return Array.from(keys).sort((a, b) => a.localeCompare(b));
  }, [db]);

  useEffect(() => {
    setFilters(f => f.map(row => row.field ? row : { ...row, field: allColumns[0] || "" }));
  }, [allColumns.length]);

  const setFilter = (i, patch) => { setFilters(f => f.map((row, idx) => (idx === i ? { ...row, ...patch } : row))); };
  const addFilter = () => setFilters(f => [...f, { field: allColumns[0] || "", op: "contains", value: "" }]);
  const removeFilter = (i) => setFilters(f => f.filter((_, idx) => idx !== i));

  const filtered = useMemo(() => {
    const acts = filters.filter(f => f.field && String(f.value || "").trim() !== "");
    if (acts.length === 0) return db;
    return db.filter(row => acts.every(f => {
      const hay = String(row[f.field] ?? "");
      const needle = String(f.value ?? "");
      if (f.op === "equals") return hay.toLowerCase() === needle.toLowerCase();
      return hay.toLowerCase().includes(needle.toLowerCase());
    }));
  }, [db, filters]);

  const anyVessel = useMemo(() => {
    const keys = new Set(allColumns);
    const hint = [...keys].some(k => keyLike(k, ["vessel", "imo", "mmsi", "call_sign"]));
    if (hint) return true;
    return filtered.some(r => String(r.target_type || "").toLowerCase().includes("vessel") || String(r.vessel_name || r.imo_number || r.mmsi || r.call_sign || "").trim());
  }, [allColumns, filtered]);

  const anyAircraft = useMemo(() => {
    const keys = new Set(allColumns);
    const hint = [...keys].some(k => keyLike(k, ["aircraft", "icao", "tail", "registration"]));
    if (hint) return true;
    return filtered.some(r => String(r.target_type || "").toLowerCase().includes("aircraft") || String(r.aircraft_model || r.aircraft_registration || r.aircraft_icao || "").trim());
  }, [allColumns, filtered]);

  const colsBase = [
    "list_name","list_id","primary_name","full_name","first_name","middle_name","last_name","aliases","target_type","sanctions_program_name","country","country_iso","citizenship_country","citizenship_country_iso","nationality","area","location","address_details","postal_code","email_address","swift_bic","iban","date_of_birth","dob","place_of_birth","gender","identification_number","passport_number","drivers_license_number","vehicle_registration"
  ].filter(k => allColumns.includes(k));

  const colsVessel = [
    "vessel_name","vessel_type","imo_number","mmsi","call_sign","flag","tonnage","gross_registered_tonnage"
  ].filter(k => allColumns.includes(k));

  const colsAircraft = [
    "aircraft_model","aircraft_manufacturer","aircraft_registration","aircraft_icao"
  ].filter(k => allColumns.includes(k));

  const displayColumns = useMemo(() => {
    const present = (k) => filtered.some(r => r[k] !== null && r[k] !== undefined && String(r[k]).trim() !== "");
    const keep = colsBase.filter(present);
    if (anyVessel) keep.push(...colsVessel.filter(present));
    if (anyAircraft) keep.push(...colsAircraft.filter(present));
    const extras = allColumns
      .filter(k => !keep.includes(k) && !keyLike(k, ["vessel","ship","imo","mmsi","call_sign","aircraft","icao","tail","registration"]))
      .filter(present);
    return [...keep, ...extras].slice(0, 80);
  }, [filtered, colsBase, colsVessel, colsAircraft, anyVessel, anyAircraft, allColumns]);

  const total = filtered.length;
  const start = (page - 1) * pageSize;
  const rows = filtered.slice(start, start + pageSize);

  useEffect(() => { setPage(1); }, [JSON.stringify(filters)]);

  const toggleExpand = (col) => setExpandedCols(m => ({ ...m, [col]: m[col] ? undefined : 420 }));
  const resetWidths = () => setExpandedCols({});

  return (
    <div>
      <section style={s.section}>
        <div style={s.sectionTitle}>Sanctions Database (Table 2)</div>

        <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
          {filters.map((f, i) => (
            <div key={i} style={{ display: "flex", gap: 8, alignItems: "center" }}>
              <select value={f.field} onChange={e => setFilter(i, { field: e.target.value })} style={{ padding: 8, background: "#0b1220", color: "#e5e7eb", border: "1px solid #334155", borderRadius: 8 }}>
                {allColumns.map(col => <option key={col} value={col}>{sName(col)}</option>)}
              </select>
              <select value={f.op} onChange={e => setFilter(i, { op: e.target.value })} style={{ padding: 8, background: "#0b1220", color: "#e5e7eb", border: "1px solid #334155", borderRadius: 8 }}>
                <option value="contains">contains</option>
                <option value="equals">equals</option>
              </select>
              <input value={f.value} onChange={e => setFilter(i, { value: e.target.value })} placeholder="value" style={s.input} />
              <button onClick={() => removeFilter(i)} style={s.btn}>Remove</button>
            </div>
          ))}
          <div style={s.controls}>
            <button onClick={addFilter} style={s.btn}>Add Filter</button>
            <label style={{ fontSize: 12, color: "#cbd5e1" }}>Column width
              <input type="range" min="120" max="260" value={colWidth} onChange={e => setColWidth(parseInt(e.target.value || 180, 10))} style={{ marginLeft: 8 }} />
            </label>
            <button onClick={resetWidths} style={s.btn}>Reset widths</button>
            <span style={{ fontSize: 12, color: "#cbd5e1" }}>{total.toLocaleString()} result(s)</span>
          </div>
        </div>

        <div style={{ ...s.tableScroll, marginTop: 12 }}>
          <table style={s.table}>
            <colgroup>
              {displayColumns.map(col => (
                <col key={col} style={{ width: (expandedCols[col] || colWidth) + "px" }} />
              ))}
            </colgroup>
            <thead>
              <tr>
                {displayColumns.map(col => (
                  <th key={col} style={s.th} onDoubleClick={() => toggleExpand(col)} title="Double-click to expand/shrink">
                    <div style={s.thWrap}>
                      <span>{sName(col)}</span>
                      <button style={s.colBtn} onClick={(e) => { e.stopPropagation(); toggleExpand(col); }} aria-label="Expand column">⤢</button>
                    </div>
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {rows.map((r, i) => (
                <tr key={i}>
                  {displayColumns.map(col => (
                    <td key={col} style={s.td} title={r[col] ? String(r[col]) : ""}>
                      {(r[col] === null || r[col] === undefined || r[col] === "") ? "—" : String(r[col])}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {total > pageSize && (
          <div style={{ display: "flex", gap: 8, alignItems: "center", marginTop: 10 }}>
            <span style={s.chip}>Page {page} / {Math.ceil(total / pageSize)}</span>
            <button style={s.btn} onClick={() => setPage(p => Math.max(1, p - 1))}>Prev</button>
            <button style={s.btn} onClick={() => setPage(p => Math.min(Math.ceil(total / pageSize), p + 1))}>Next</button>
          </div>
        )}
      </section>
    </div>
  );
}

export default function App() {
  const { latest, history, db, loading, error, reload } = useData();
  const [selectedIndex, setSelectedIndex] = useState(null);
  const [tab, setTab] = useState("screening");
  const item = useMemo(() => (selectedIndex == null ? latest : history?.[selectedIndex] ?? latest), [selectedIndex, history, latest]);
  return (
    <div style={s.page}>
      <div style={{ ...s.container, ...s.header }}>
        <div style={{ fontWeight: 800, color: "#f3f4f6" }}>ISO Screening Viewer</div>
        <div style={s.tabs}>
          <button style={s.tab(tab === "screening")} onClick={() => setTab("screening")}>Screening</button>
          <button style={s.tab(tab === "database")} onClick={() => setTab("database")}>Sanctions DB</button>
        </div>
        <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
          {loading && <span style={{ color: "#94a3b8", fontSize: 12 }}>Loading…</span>}
          {error && <span style={{ color: "#f87171", fontSize: 12 }}>Error: {error}</span>}
          <button onClick={reload} style={s.btn}>Refresh</button>
        </div>
      </div>
      <div style={s.container}>
        {tab === "screening" && (
          <>
            <SummaryView item={item} loading={loading} error={error} onRefresh={reload} />
            <History history={history} onSelect={setSelectedIndex} selectedIndex={selectedIndex} />
          </>
        )}
        {tab === "database" && <DbTab db={db} />}
      </div>
    </div>
  );
}
