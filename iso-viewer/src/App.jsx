import React, { useEffect, useMemo, useState } from "react";

const BASE = (typeof import.meta !== "undefined" && import.meta.env && import.meta.env.BASE_URL) ? import.meta.env.BASE_URL : "/";
const FETCH_URLS = { latest: `${BASE}latest.json`, history: `${BASE}history.jsonl` };

const get = (o, p, d) => { try { return p.split(".").reduce((a, k) => (a && k in a ? a[k] : undefined), o) ?? d; } catch { return d; } };
const uniq = (a = []) => Array.from(new Set(a.filter(Boolean)));
const prettyRole = (r = '') => {
  const x = String(r).toLowerCase();
  if (x.includes('debt')) return 'Debtor';
  if (x.includes('dbtr')) return 'Debtor';
  if (x.includes('cred')) return 'Creditor';
  if (x.includes('cdtr')) return 'Creditor';
  return r || '—';
};
const extractNamesAndRoles = (obj) => {
  const nsr = get(obj, 'nameScreeningResults', []) || [];
  const flagged = nsr.filter(r => (r?.matches || []).length > 0 || r?.flagged === true);
  let names = uniq([
    ...flagged.map(r => r.inputName),
    ...flagged.flatMap(r => (r.matches || []).map(m => m.displayName))
  ]);
  let roles = uniq(flagged.map(r => prettyRole(r.partyRole)));
  // Fallback to raw engine payload if nameScreeningResults missing
  if (names.length === 0) {
    const hits = get(obj, 'audit.rawEngineResponse.matches', []) || [];
    if (hits.length) {
      names = uniq(hits.map(h => h.name));
      roles = uniq(hits.map(h => prettyRole(h.role)));
    }
  }
  return { names, roles };
};

const buildReason = (obj = {}) => {
  const explanations  = get(obj, "decision.explanations", []) || [];
  const drivers       = get(obj, "riskSummary.drivers", []) || [];
  const reasonCodes   = get(obj, "decision.reasonCodes", []) || [];
  const listNames     = (get(obj, "listsUsed", []) || []).map(l => l?.name).filter(Boolean);
  const matches       = get(obj, "audit.rawEngineResponse.matches", []) || [];
  const flagged       = Boolean(get(obj, "audit.rawEngineResponse.flagged", false));

  const parts = [
    ...explanations,
];
  return parts.filter(Boolean).join(" — ");
};

function useData() {
  const [latest, setLatest] = useState(null);
  const [history, setHistory] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  useEffect(() => {
    let live = true;
    (async () => {
      setLoading(true);
      setError(null);
      try {
        const l = await fetch(FETCH_URLS.latest, { cache: "no-store" });
        if (!l.ok) throw new Error(`latest.json HTTP ${l.status}`);
        const latestJson = await l.json();

        const h = await fetch(FETCH_URLS.history, { cache: "no-store" });
        if (!h.ok) throw new Error(`history.jsonl HTTP ${h.status}`);
        const historyText = await h.text();
        let hx = [];
        try {
          const lines = historyText.replace(/\r/g, '').split('\n');
          hx = lines
            .map(t => t.trim())
            .filter(Boolean)
            .map(line => { try { return JSON.parse(line); } catch { return null; } })
            .filter(Boolean);
          if (hx.length === 0) {
            const maybeArray = JSON.parse(historyText);
            if (Array.isArray(maybeArray)) hx = maybeArray;
          }
        } catch {}

        if (live) { setLatest(latestJson); setHistory(hx); }
      } catch (e) { if (live) setError(String(e.message || e)); }
      finally { if (live) setLoading(false); }
    })();
    return () => { live = false; };
  }, []);
  return { latest, history, loading, error };
}

function Row({ label, value }) {
  return (
    <div style={{ display: "grid", gridTemplateColumns: "220px 1fr", padding: "8px 0", borderTop: "1px dashed #eee", gap: 12 }}>
      <div style={{ color: "#555" }}>{label}</div>
      <div style={{ fontWeight: 600, whiteSpace: 'pre-wrap' }}>{value ?? "—"}</div>
    </div>
  );
}

export default function App() {
  const { latest, history, loading, error } = useData();
  const [selectedIndex, setSelectedIndex] = useState(null);
  const item = useMemo(() => (selectedIndex == null ? latest : history?.[selectedIndex] ?? latest), [selectedIndex, history, latest]);

  const when = get(item, "audit.screeningRunAt") || get(item, "timeflagged");
  const whenNice = when ? new Date(when).toLocaleString() : "—";

  // From nameScreeningResults pull flagged names + roles
  const { names: namesArr, roles: rolesArr } = extractNamesAndRoles(item || {});
  const namesFlagged = namesArr.join(', ');
  const rolesFlagged = rolesArr.join(', ');
  const nsr = get(item, "nameScreeningResults", []) || [];
  const flagged = nsr.filter(r => (r?.matches || []).length > 0 || r?.flagged === true);

  // Build reason for the current item
  const reason = buildReason(item || {});

  return (
    <div style={s.page}>
      <div style={{ ...s.container, ...s.header }}>
        <div style={{ fontWeight: 800 }}>ISO Screening Viewer</div>
        <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
          {loading && <span style={{ color: "#666", fontSize: 12 }}>Loading…</span>}
          {error && <span style={{ color: "#b00", fontSize: 12 }}>Error: {error}</span>}
          <button onClick={() => window.location.reload()} style={s.btn}>Refresh</button>
        </div>
      </div>

      <div style={s.container}>
        <section style={s.section}>
          <div style={s.sectionTitle}>Summary</div>
          {!item && <div style={{ color: "#666", fontSize: 14 }}>No data.</div>}
          {item && (
            <div>
              <Row label="Name(s)" value={namesFlagged || "—"} />
              <Row label="Fields Flagged" value={rolesFlagged || "—"} />
              <Row label="Reason" value={reason || "—"} />
              <Row label="Time" value={whenNice} />
            </div>
          )}
        </section>

        <section style={s.section}>
          <div style={s.sectionTitle}>Raw JSON</div>
          <pre style={s.pre}>{item ? JSON.stringify(item, null, 2) : ""}</pre>
        </section>

        <section style={s.section}>
          <div style={s.sectionTitle}>History</div>
          {history.length === 0 && <div style={{ color: "#666", fontSize: 14 }}>No history found.</div>}
          {history.length > 0 && (
            <div style={{ overflow: "auto", border: "1px solid #eee", borderRadius: 8 }}>
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
                    const w = get(h, "audit.screeningRunAt") || get(h, "timeflagged");
                    const wNice = w ? new Date(w).toLocaleString() : "—";
                    const { names: _n, roles: _r } = extractNamesAndRoles(h || {});
                    const _names = _n.join(', ');
                    const _roles = _r.join(', ');
                    return (
                      <tr key={i} onClick={() => setSelectedIndex(i)} style={{ cursor: "pointer", background: selectedIndex === i ? "#f5f9ff" : "#fff" }}>
                        <td style={s.td}>{wNice}</td>
                        <td style={s.td}>{_names || '—'}</td>
                        <td style={s.td}>{_roles || '—'}</td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </section>
      </div>
    </div>
  );
}

const s = {
  page: { fontFamily: "system-ui,-apple-system,Segoe UI,Roboto,Arial,sans-serif", background: "#f7f7f8", color: "#111", minHeight: "100vh", width: "100vw", overflowX: "hidden" },
  container: { width: "100%", maxWidth: "none", margin: 0, padding: "0 12px" },
  header: { display: "flex", justifyContent: "space-between", alignItems: "center", padding: "12px 0", borderBottom: "1px solid #e6e6e9", background: "#fff", position: "sticky", top: 0, zIndex: 1 },
  section: { background: "#fff", border: "1px solid #e6e6e9", borderRadius: 10, padding: 16, marginTop: 12 },
  sectionTitle: { fontWeight: 800, marginBottom: 8 },
  pre: { padding: 12, background: "#0b1020", color: "#d6e2ff", borderRadius: 8, overflow: "auto", fontSize: 12, lineHeight: 1.45, maxHeight: 420 },
  btn: { background: "#111", color: "#fff", border: "none", borderRadius: 6, padding: "6px 10px", cursor: "pointer", fontSize: 12 },
  table: { width: "100%", borderCollapse: "separate", borderSpacing: 0 },
  th: { textAlign: "left", fontWeight: 700, fontSize: 12, padding: 10, borderBottom: "1px solid #eee", background: "#fafafa", position: "sticky", top: 0 },
  td: { fontSize: 13, padding: 10, borderBottom: "1px solid #f0f0f0" },
};