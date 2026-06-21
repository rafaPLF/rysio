from __future__ import annotations


def render_logs_viewer_page(api_base_url: str = "") -> str:
    api_base_url = api_base_url.replace("&", "&amp;").replace('"', "&quot;")
    api_base_url_js = api_base_url.replace("\\", "\\\\").replace("`", "\\`")
    return f"""<!DOCTYPE html>
<html lang="de">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Rysio Control Panel</title>
  <style>
    :root {{
      color-scheme: dark;
      --bg: #091018;
      --panel: rgba(16, 24, 36, 0.9);
      --panel-strong: rgba(23, 35, 51, 0.96);
      --panel-soft: rgba(21, 30, 44, 0.82);
      --text: #eef4fb;
      --muted: #94a6b8;
      --accent: #63e0ff;
      --accent-soft: rgba(99, 224, 255, 0.14);
      --green: #7bf0c3;
      --yellow: #ffd779;
      --danger: #ff8585;
      --border: rgba(255, 255, 255, 0.12);
      --shadow: 0 24px 80px rgba(0, 0, 0, 0.42);
      --radius: 22px;
    }}

    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      min-height: 100vh;
      font-family: Consolas, "Courier New", monospace;
      color: var(--text);
      background:
        radial-gradient(circle at top left, rgba(99, 224, 255, 0.16), transparent 26%),
        radial-gradient(circle at top right, rgba(123, 240, 195, 0.14), transparent 22%),
        linear-gradient(180deg, #081018 0%, #0d1520 100%);
    }}

    .page {{ width: min(1280px, calc(100% - 28px)); margin: 18px auto 42px; }}
    .topbar {{
      display: flex; justify-content: space-between; align-items: center; gap: 16px;
      padding: 14px 18px; margin-bottom: 18px; border-radius: 20px; border: 1px solid var(--border);
      background: rgba(14, 22, 33, 0.82); box-shadow: var(--shadow); backdrop-filter: blur(14px); flex-wrap: wrap;
    }}
    .brand {{ display: flex; flex-direction: column; gap: 4px; }}
    .brand-mark {{ display: inline-flex; align-items: center; gap: 10px; font-size: 30px; font-weight: 700; letter-spacing: 0.04em; }}
    .brand-sub {{ color: var(--muted); font-size: 13px; }}
    .top-actions {{ display: flex; gap: 12px; align-items: center; flex-wrap: wrap; }}
    .pill {{
      display: inline-flex; align-items: center; gap: 8px; padding: 10px 14px; border-radius: 999px;
      border: 1px solid var(--border); background: rgba(9, 14, 20, 0.92); color: var(--muted); font-size: 13px;
    }}
    .layout {{ display: grid; grid-template-columns: 310px minmax(0, 1fr); gap: 18px; }}
    .sidebar, .content-shell {{
      border: 1px solid var(--border); border-radius: 24px; background: rgba(16, 24, 36, 0.9);
      box-shadow: var(--shadow); backdrop-filter: blur(14px);
    }}
    .sidebar {{ padding: 18px; display: grid; gap: 16px; align-content: start; }}
    .content-shell {{ padding: 18px; display: grid; gap: 18px; }}
    .block, .hero, .metric, .card, .feature-card, .entry {{
      border: 1px solid var(--border); border-radius: var(--radius);
      background: linear-gradient(180deg, var(--panel-strong), var(--panel-soft)); padding: 16px;
    }}
    .hero {{
      padding: 20px;
      background: linear-gradient(135deg, rgba(99, 224, 255, 0.12), rgba(123, 240, 195, 0.08)), linear-gradient(180deg, var(--panel-strong), var(--panel-soft));
    }}
    h1, h2, h3, p {{ margin: 0; }}
    h1 {{ font-size: clamp(30px, 4vw, 44px); line-height: 0.98; margin-bottom: 10px; }}
    h2 {{ font-size: 18px; margin-bottom: 12px; }}
    h3 {{ font-size: 15px; margin-bottom: 10px; }}
    .muted, .hint, .meta, .empty, .error {{ color: var(--muted); }}
    .metrics, .feature-grid, .control-grid {{ display: grid; gap: 14px; }}
    .metrics {{ grid-template-columns: repeat(auto-fit, minmax(170px, 1fr)); }}
    .feature-grid {{ grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); }}
    .control-grid {{ grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); }}
    .metric-value {{ font-size: 30px; color: var(--accent); margin-top: 8px; }}
    .status-row {{ display: flex; gap: 10px; flex-wrap: wrap; margin-top: 16px; }}
    .status-chip {{
      display: inline-flex; align-items: center; gap: 8px; padding: 9px 12px; border-radius: 999px;
      font-size: 12px; border: 1px solid var(--border); background: rgba(9, 14, 20, 0.85);
    }}
    .good {{ color: var(--green); border-color: rgba(123, 240, 195, 0.35); background: rgba(123, 240, 195, 0.08); }}
    .warn {{ color: var(--yellow); border-color: rgba(255, 215, 121, 0.35); background: rgba(255, 215, 121, 0.08); }}
    label {{ display: block; margin-bottom: 8px; font-size: 12px; text-transform: uppercase; letter-spacing: 0.08em; color: var(--muted); }}
    input, select, button {{
      width: 100%; padding: 12px 14px; border-radius: 14px; border: 1px solid var(--border);
      background: rgba(8, 12, 18, 0.94); color: var(--text); font: inherit;
    }}
    button {{
      cursor: pointer; background: linear-gradient(135deg, rgba(99, 224, 255, 0.18), rgba(123, 240, 195, 0.18));
      transition: transform 0.15s ease, border-color 0.15s ease, filter 0.15s ease;
    }}
    button:hover {{ transform: translateY(-1px); border-color: rgba(99, 224, 255, 0.55); filter: brightness(1.05); }}
    .ghost {{ background: rgba(8, 12, 18, 0.94); }}
    .button-row {{ display: flex; gap: 12px; flex-wrap: wrap; }}
    .button-row button {{ width: auto; min-width: 180px; }}
    .stack {{ display: grid; gap: 14px; }}
    .feature-top {{ display: flex; justify-content: space-between; gap: 12px; align-items: flex-start; margin-bottom: 10px; }}
    .feature-badge {{
      padding: 6px 10px; border-radius: 999px; font-size: 11px; border: 1px solid var(--border);
      background: var(--accent-soft); color: var(--accent);
    }}
    .feature-actions {{ margin-top: 14px; display: flex; gap: 10px; flex-wrap: wrap; }}
    .feature-actions button {{ width: auto; min-width: 130px; }}
    .list {{ display: grid; gap: 10px; padding: 0; margin: 0; list-style: none; }}
    .list li {{ padding: 12px; border-radius: 14px; border: 1px solid var(--border); background: rgba(8, 12, 18, 0.7); }}
    .entry-list {{ display: grid; gap: 14px; }}
    .entry-head {{ display: flex; justify-content: space-between; gap: 12px; align-items: center; flex-wrap: wrap; margin-bottom: 12px; }}
    .entry-type {{
      display: inline-flex; align-items: center; padding: 6px 10px; border-radius: 999px;
      background: rgba(99, 224, 255, 0.12); border: 1px solid rgba(99, 224, 255, 0.34); color: var(--accent); font-size: 12px;
    }}
    .summary {{ font-size: 16px; margin-bottom: 12px; }}
    pre {{
      margin: 0; padding: 12px; border-radius: 14px; background: rgba(5, 9, 14, 0.9);
      border: 1px solid var(--border); color: #dbe8f5; white-space: pre-wrap; word-break: break-word; overflow-x: auto;
    }}
    .login-box {{ background: linear-gradient(135deg, rgba(88, 101, 242, 0.18), rgba(99, 224, 255, 0.06)), linear-gradient(180deg, var(--panel-strong), var(--panel-soft)); }}
    .discord-button {{ background: linear-gradient(135deg, rgba(88, 101, 242, 0.32), rgba(88, 101, 242, 0.18)); border-color: rgba(88, 101, 242, 0.45); }}
    .small {{ font-size: 12px; }}
    @media (max-width: 980px) {{ .layout {{ grid-template-columns: 1fr; }} }}
    @media (max-width: 720px) {{
      .page {{ width: calc(100% - 18px); margin: 10px auto 24px; }}
      .topbar, .sidebar, .content-shell {{ padding: 14px; }}
    }}
  </style>
</head>
<body>
  <main class="page">
    <header class="topbar">
      <div class="brand">
        <div class="brand-mark">RYSIO PANEL</div>
        <div class="brand-sub">Discord Bot Control Panel vorbereiten: ohne eigene Accounts, spaeter mit Discord OAuth Login.</div>
      </div>
      <div class="top-actions">
        <div class="pill">Build: Pre-Alpha Panel</div>
        <div class="pill">Mode: Testserver</div>
      </div>
    </header>
    <div class="layout">
      <aside class="sidebar">
        <section class="block login-box">
          <h2>Discord Login</h2>
          <p class="muted">Genau so werden wir es spaeter machen: Login mit Discord statt eigene Accounts in deiner Datenbank.</p>
          <div class="button-row" style="margin-top:14px;">
            <button class="discord-button" type="button" id="discordLoginButton">Mit Discord anmelden</button>
          </div>
          <p class="hint small" style="margin-top:12px;">Aktuell ist das nur vorbereitet. Der echte OAuth-Flow kommt im naechsten Backend-Schritt.</p>
        </section>
        <section class="block">
          <h2>Server Auswahl</h2>
          <label for="guildId">Guild ID</label>
          <input id="guildId" placeholder="123456789012345678">
          <p class="hint small" style="margin-top:10px;">Spaeter wird diese Liste automatisch aus deinen Discord-Servern geladen.</p>
        </section>
        <section class="block">
          <h2>API Verbindung</h2>
          <div class="stack">
            <div>
              <label for="apiBaseUrl">API Base URL</label>
              <input id="apiBaseUrl" placeholder="https://api.deinedomain.de" value="{api_base_url}">
            </div>
            <div>
              <label for="apiToken">API Token</label>
              <input id="apiToken" type="password" placeholder="WEB_API_TOKEN vom Bot-Server">
            </div>
            <div>
              <label for="limit">Log Limit</label>
              <input id="limit" type="number" min="1" max="200" value="25">
            </div>
            <div>
              <label for="eventType">Event Filter</label>
              <select id="eventType">
                <option value="">Alle</option>
                <option value="member.join">member.join</option>
                <option value="member.leave">member.leave</option>
                <option value="message.delete">message.delete</option>
                <option value="message.edit">message.edit</option>
                <option value="voice.join">voice.join</option>
                <option value="voice.leave">voice.leave</option>
                <option value="voice.move">voice.move</option>
              </select>
            </div>
          </div>
          <div class="button-row" style="margin-top:14px;">
            <button id="loadButton" type="button">Logs laden</button>
            <button id="saveButton" type="button" class="ghost">Panel Daten speichern</button>
          </div>
        </section>
        <section class="block">
          <h2>Naechste Backend Schritte</h2>
          <ul class="list">
            <li>Discord OAuth Login mit Guild-Auswahl</li>
            <li>Rollen- und Rechtepruefung ueber Discord</li>
            <li>Feature-Settings per API speichern</li>
            <li>Live-Logs und Moderations-Aktionen</li>
          </ul>
        </section>
      </aside>
      <section class="content-shell">
        <section class="hero">
          <h1>Ein Control Panel statt nur ein Log Viewer</h1>
          <p class="muted">Die Seite ist jetzt schon so aufgebaut, wie wir das echte Rysio Panel spaeter brauchen: Login, Server-Kontext, Feature-Karten, Moderation und Live-Logbereich. Die einzelnen Buttons sind bewusst vorbereitet, damit wir jetzt Schritt fuer Schritt das Backend dahinter setzen koennen.</p>
          <div class="status-row">
            <span class="status-chip good">Discord OAuth geplant</span>
            <span class="status-chip warn">Feature-Speicherung folgt</span>
            <span class="status-chip good">Audit-Logs schon angebunden</span>
            <span class="status-chip warn">Moderation API als naechstes</span>
          </div>
        </section>
        <section class="metrics">
          <article class="metric"><h3>Aktive Server</h3><div class="metric-value">1</div><p class="muted">Teststand fuer deinen aktuellen Panel-Aufbau.</p></article>
          <article class="metric"><h3>Features geplant</h3><div class="metric-value">8+</div><p class="muted">Autoroles, Tickets, Verification, Logs, JTC, Reaction Roles und mehr.</p></article>
          <article class="metric"><h3>Geladene Logs</h3><div class="metric-value" id="loadedStat">0</div><p class="muted">Kommt direkt aus deiner Audit-Log API.</p></article>
          <article class="metric"><h3>Gesamteintraege</h3><div class="metric-value" id="totalStat">0</div><p class="muted">Hilft spaeter fuer Suche, Pagination und Export.</p></article>
        </section>
        <section class="feature-grid">
          <article class="feature-card"><div class="feature-top"><div><h2>Setup & Branding</h2><p class="muted">Info-Channel, Sprache, Begruessung, Patch Notes.</p></div><span class="feature-badge">bereit</span></div><div class="feature-actions"><button type="button" class="ghost">Spaeter oeffnen</button></div></article>
          <article class="feature-card"><div class="feature-top"><div><h2>Moderation</h2><p class="muted">Warns, Mutes, Kicks, Bans, Case-Historie und Staff-Aktionen.</p></div><span class="feature-badge">naechstes modul</span></div><div class="feature-actions"><button type="button">Moderation vorbereiten</button></div></article>
          <article class="feature-card"><div class="feature-top"><div><h2>Verification</h2><p class="muted">Panel, Rolle, Captcha-Flow und spaeter Web-Kontrolle.</p></div><span class="feature-badge">backend da</span></div><div class="feature-actions"><button type="button" class="ghost">Status anzeigen</button></div></article>
          <article class="feature-card"><div class="feature-top"><div><h2>Tickets</h2><p class="muted">Panel, Limits, Support-Kontext und spaeter Ticket-Uebersicht im Web.</p></div><span class="feature-badge">backend da</span></div><div class="feature-actions"><button type="button" class="ghost">Spaeter anbinden</button></div></article>
          <article class="feature-card"><div class="feature-top"><div><h2>Reaction Roles</h2><p class="muted">Panel-Management ohne Command-Spam und spaeter per Panel editierbar.</p></div><span class="feature-badge">lokal aktiv</span></div><div class="feature-actions"><button type="button" class="ghost">UI vorbereiten</button></div></article>
          <article class="feature-card"><div class="feature-top"><div><h2>Join to Create</h2><p class="muted">Voice-Lobby, Temp-Channels und spaeter Nutzerrechte per Webpanel.</p></div><span class="feature-badge">backend da</span></div><div class="feature-actions"><button type="button" class="ghost">Details spaeter</button></div></article>
        </section>
        <section class="control-grid">
          <article class="card"><h2>Discord OAuth Plan</h2><ul class="list"><li>Login Button leitet zu Discord weiter</li><li>Discord gibt User-ID, Name und Guilds zurueck</li><li>Rysio prueft, welche Server du verwalten darfst</li><li>Keine eigenen Benutzerkonten noetig</li></ul></article>
          <article class="card"><h2>Panel Navigation Plan</h2><ul class="list"><li>Dashboard</li><li>Server Settings</li><li>Moderation</li><li>Logs</li><li>Tickets</li><li>Verification</li></ul></article>
        </section>
        <section class="card">
          <h2>Audit Logs</h2>
          <p class="muted">Das hier bleibt schon live nutzbar. Alles andere drumherum ist die Vorbereitung fuer das spaetere echte Control Panel.</p>
          <p id="statusText" class="meta" style="margin-top:12px;">Bereit.</p>
          <p id="errorText" class="error" hidden style="margin-top:8px;"></p>
          <section id="entries" class="entry-list" style="margin-top:16px;"><div class="empty">Noch keine Daten geladen.</div></section>
        </section>
      </section>
    </div>
  </main>
  <script>
    const DEFAULT_API_BASE_URL = `{api_base_url_js}`;
    const apiBaseUrlInput = document.getElementById("apiBaseUrl");
    const guildIdInput = document.getElementById("guildId");
    const apiTokenInput = document.getElementById("apiToken");
    const limitInput = document.getElementById("limit");
    const eventTypeInput = document.getElementById("eventType");
    const statusText = document.getElementById("statusText");
    const errorText = document.getElementById("errorText");
    const totalStat = document.getElementById("totalStat");
    const loadedStat = document.getElementById("loadedStat");
    const entries = document.getElementById("entries");
    const STORAGE_KEY = "rysio-control-panel";

    function escapeHtml(value) {{
      return String(value).replaceAll("&", "&amp;").replaceAll("<", "&lt;").replaceAll(">", "&gt;").replaceAll('"', "&quot;").replaceAll("'", "&#39;");
    }}
    function loadSavedState() {{
      try {{
        const raw = localStorage.getItem(STORAGE_KEY);
        if (!raw) return;
        const saved = JSON.parse(raw);
        apiBaseUrlInput.value = saved.apiBaseUrl || DEFAULT_API_BASE_URL;
        guildIdInput.value = saved.guildId || "";
        apiTokenInput.value = saved.apiToken || "";
        limitInput.value = saved.limit || "25";
        eventTypeInput.value = saved.eventType || "";
      }} catch {{}}
    }}
    function saveState() {{
      const payload = {{
        apiBaseUrl: apiBaseUrlInput.value.trim(),
        guildId: guildIdInput.value.trim(),
        apiToken: apiTokenInput.value.trim(),
        limit: limitInput.value.trim(),
        eventType: eventTypeInput.value,
      }};
      localStorage.setItem(STORAGE_KEY, JSON.stringify(payload));
      statusText.textContent = "Panel-Daten lokal gespeichert.";
    }}
    function setError(message) {{
      if (!message) {{
        errorText.hidden = true;
        errorText.textContent = "";
        return;
      }}
      errorText.hidden = false;
      errorText.textContent = message;
    }}
    function renderEntries(items) {{
      if (!items.length) {{
        entries.innerHTML = '<div class="empty">Keine Log-Eintraege fuer diese Auswahl gefunden.</div>';
        return;
      }}
      entries.innerHTML = items.map((item) => {{
        const details = item.details ? JSON.stringify(item.details, null, 2) : "{{}}";
        return `<article class="entry"><div class="entry-head"><span class="entry-type">${{escapeHtml(item.event_type)}}</span><span class="meta">${{escapeHtml(item.created_at || "unbekannt")}}</span></div><p class="summary">${{escapeHtml(item.summary)}}</p><p class="meta">ID: ${{escapeHtml(item.id)}} | User: ${{escapeHtml(item.user_id ?? "-")}} | Channel: ${{escapeHtml(item.channel_id ?? "-")}}</p><pre>${{escapeHtml(details)}}</pre></article>`;
      }}).join("");
    }}
    async function loadLogs() {{
      const apiBaseUrl = apiBaseUrlInput.value.trim().replace(/\\/$/, "");
      const guildId = guildIdInput.value.trim();
      const apiToken = apiTokenInput.value.trim();
      const limit = limitInput.value.trim() || "25";
      const eventType = eventTypeInput.value;
      if (!apiBaseUrl) {{ setError("Bitte zuerst die API Base URL eintragen."); return; }}
      if (!guildId) {{ setError("Bitte zuerst eine Guild ID eintragen."); return; }}
      if (!apiToken) {{ setError("Bitte zuerst den WEB_API_TOKEN eintragen."); return; }}
      saveState();
      setError("");
      statusText.textContent = "Logs werden geladen...";
      const params = new URLSearchParams({{ limit }});
      if (eventType) params.set("event_type", eventType);
      try {{
        const response = await fetch(`${{apiBaseUrl}}/api/guilds/${{guildId}}/logs?${{params.toString()}}`, {{ headers: {{ Authorization: `Bearer ${{apiToken}}` }} }});
        const payload = await response.json();
        if (!response.ok) throw new Error(payload.error || `HTTP ${{response.status}}`);
        totalStat.textContent = String(payload.total ?? 0);
        loadedStat.textContent = String(payload.items?.length ?? 0);
        renderEntries(payload.items || []);
        statusText.textContent = `Erfolgreich geladen: ${{payload.items?.length ?? 0}} Log-Eintraege.`;
      }} catch (error) {{
        totalStat.textContent = "0";
        loadedStat.textContent = "0";
        entries.innerHTML = '<div class="empty">Keine Daten dargestellt.</div>';
        setError(`Abruf fehlgeschlagen: ${{error.message}}`);
        statusText.textContent = "Fehler beim Laden.";
      }}
    }}
    document.getElementById("loadButton").addEventListener("click", loadLogs);
    document.getElementById("saveButton").addEventListener("click", saveState);
    document.getElementById("discordLoginButton").addEventListener("click", () => {{
      statusText.textContent = "Discord OAuth ist vorbereitet, aber noch nicht ans Backend angebunden.";
      setError("");
    }});
    loadSavedState();
  </script>
</body>
</html>
"""
