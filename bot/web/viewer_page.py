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
      --brand: #738bff;
      --brand-soft: rgba(115, 139, 255, 0.16);
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
        radial-gradient(circle at top right, rgba(115, 139, 255, 0.14), transparent 24%),
        linear-gradient(180deg, #081018 0%, #0d1520 100%);
    }}

    .page {{ width: min(1380px, calc(100% - 28px)); margin: 18px auto 42px; }}
    .topbar {{
      display: flex; justify-content: space-between; align-items: center; gap: 16px;
      padding: 14px 18px; margin-bottom: 18px; border-radius: 20px; border: 1px solid var(--border);
      background: rgba(14, 22, 33, 0.82); box-shadow: var(--shadow); backdrop-filter: blur(14px); flex-wrap: wrap;
    }}
    .brand {{ display: flex; flex-direction: column; gap: 4px; }}
    .brand-mark {{ display: inline-flex; align-items: center; gap: 10px; font-size: 30px; font-weight: 700; letter-spacing: 0.04em; }}
    .brand-sub {{ color: var(--muted); font-size: 13px; max-width: 780px; }}
    .top-actions {{ display: flex; gap: 12px; align-items: center; flex-wrap: wrap; }}
    .pill {{
      display: inline-flex; align-items: center; gap: 8px; padding: 10px 14px; border-radius: 999px;
      border: 1px solid var(--border); background: rgba(9, 14, 20, 0.92); color: var(--muted); font-size: 13px;
    }}
    .layout {{ display: grid; grid-template-columns: 320px minmax(0, 1fr); gap: 18px; }}
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
      background: linear-gradient(135deg, rgba(99, 224, 255, 0.12), rgba(115, 139, 255, 0.1)), linear-gradient(180deg, var(--panel-strong), var(--panel-soft));
    }}
    h1, h2, h3, p {{ margin: 0; }}
    h1 {{ font-size: clamp(30px, 4vw, 44px); line-height: 0.98; margin-bottom: 10px; }}
    h2 {{ font-size: 18px; margin-bottom: 12px; }}
    h3 {{ font-size: 15px; margin-bottom: 10px; }}
    .muted, .hint, .meta, .empty, .error {{ color: var(--muted); }}
    .empty {{ padding: 12px; border-radius: 14px; border: 1px dashed var(--border); background: rgba(8, 12, 18, 0.52); }}
    .metrics, .feature-grid, .control-grid, .ticket-grid {{ display: grid; gap: 14px; }}
    .metrics {{ grid-template-columns: repeat(auto-fit, minmax(170px, 1fr)); }}
    .feature-grid {{ grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); }}
    .control-grid {{ grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); }}
    .ticket-grid {{ grid-template-columns: minmax(0, 1.2fr) minmax(0, 1fr); }}
    .metric-value {{ font-size: 30px; color: var(--accent); margin-top: 8px; }}
    .status-row {{ display: flex; gap: 10px; flex-wrap: wrap; margin-top: 16px; }}
    .status-chip {{
      display: inline-flex; align-items: center; gap: 8px; padding: 9px 12px; border-radius: 999px;
      font-size: 12px; border: 1px solid var(--border); background: rgba(9, 14, 20, 0.85);
    }}
    .good {{ color: var(--green); border-color: rgba(123, 240, 195, 0.35); background: rgba(123, 240, 195, 0.08); }}
    .warn {{ color: var(--yellow); border-color: rgba(255, 215, 121, 0.35); background: rgba(255, 215, 121, 0.08); }}
    label {{ display: block; margin-bottom: 8px; font-size: 12px; text-transform: uppercase; letter-spacing: 0.08em; color: var(--muted); }}
    input, select, textarea, button {{
      width: 100%; padding: 12px 14px; border-radius: 14px; border: 1px solid var(--border);
      background: rgba(8, 12, 18, 0.94); color: var(--text); font: inherit;
    }}
    textarea {{ min-height: 120px; resize: vertical; }}
    button {{
      cursor: pointer; background: linear-gradient(135deg, rgba(99, 224, 255, 0.18), rgba(115, 139, 255, 0.18));
      transition: transform 0.15s ease, border-color 0.15s ease, filter 0.15s ease;
    }}
    button:hover {{ transform: translateY(-1px); border-color: rgba(99, 224, 255, 0.55); filter: brightness(1.05); }}
    button:disabled {{ opacity: 0.55; cursor: not-allowed; transform: none; filter: none; }}
    .ghost {{ background: rgba(8, 12, 18, 0.94); }}
    .danger-button {{ background: linear-gradient(135deg, rgba(255, 133, 133, 0.18), rgba(255, 80, 80, 0.16)); }}
    .button-row {{ display: flex; gap: 12px; flex-wrap: wrap; }}
    .button-row button {{ width: auto; min-width: 160px; }}
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
    .entry-list, .panel-list {{ display: grid; gap: 14px; }}
    .entry-head, .panel-head {{ display: flex; justify-content: space-between; gap: 12px; align-items: center; flex-wrap: wrap; margin-bottom: 12px; }}
    .entry-type, .panel-tag {{
      display: inline-flex; align-items: center; padding: 6px 10px; border-radius: 999px;
      background: rgba(99, 224, 255, 0.12); border: 1px solid rgba(99, 224, 255, 0.34); color: var(--accent); font-size: 12px;
    }}
    .summary {{ font-size: 16px; margin-bottom: 12px; }}
    .panel-card {{
      border: 1px solid var(--border); border-radius: 18px; padding: 14px;
      background: linear-gradient(180deg, rgba(17, 25, 37, 0.92), rgba(13, 20, 31, 0.82));
    }}
    .panel-meta {{ display: grid; gap: 8px; color: var(--muted); font-size: 13px; margin-top: 12px; }}
    .login-box {{ background: linear-gradient(135deg, rgba(88, 101, 242, 0.18), rgba(99, 224, 255, 0.06)), linear-gradient(180deg, var(--panel-strong), var(--panel-soft)); }}
    .discord-button {{ background: linear-gradient(135deg, rgba(88, 101, 242, 0.32), rgba(88, 101, 242, 0.18)); border-color: rgba(88, 101, 242, 0.45); }}
    .session-box {{ margin-top: 14px; padding: 12px; border-radius: 14px; border: 1px solid var(--border); background: rgba(8, 12, 18, 0.7); }}
    .session-name {{ color: var(--text); margin-bottom: 8px; }}
    .small {{ font-size: 12px; }}
    pre {{
      margin: 0; padding: 12px; border-radius: 14px; background: rgba(5, 9, 14, 0.9);
      border: 1px solid var(--border); color: #dbe8f5; white-space: pre-wrap; word-break: break-word; overflow-x: auto;
    }}
    @media (max-width: 1080px) {{ .layout, .ticket-grid {{ grid-template-columns: 1fr; }} }}
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
        <div class="brand-sub">Jetzt mit echtem Discord-Login, Server-Auswahl und dem ersten echten Modul: Ticket-Panels direkt aus dem Web erstellen und verwalten.</div>
      </div>
      <div class="top-actions">
        <div class="pill">Build: Panel Alpha</div>
        <div class="pill">Mode: Tickets zuerst</div>
      </div>
    </header>
    <div class="layout">
      <aside class="sidebar">
        <section class="block login-box">
          <h2>Discord Login</h2>
          <p class="muted">Login mit Discord statt eigene Accounts in deiner Datenbank. Der Secret-Teil bleibt nur auf deinem Bot-Server.</p>
          <div class="button-row" style="margin-top:14px;">
            <button class="discord-button" type="button" id="discordLoginButton">Mit Discord anmelden</button>
            <button class="ghost" type="button" id="discordLogoutButton">Discord Logout</button>
          </div>
          <div class="session-box">
            <p class="session-name" id="sessionUserText">Noch nicht eingeloggt.</p>
            <p class="hint small" id="sessionGuildCountText">0 verwaltbare Server von Discord geladen.</p>
            <p class="hint small" id="oauthErrorText" hidden></p>
          </div>
        </section>
        <section class="block">
          <h2>Server Auswahl</h2>
          <label for="guildSelect">Discord Server</label>
          <select id="guildSelect">
            <option value="">Server auswaehlen</option>
          </select>
          <p class="hint small" style="margin-top:10px;">Es werden nur Server angezeigt, die du in Discord verwalten darfst.</p>
          <div class="session-box" style="margin-top:12px;">
            <p class="small">Guild ID</p>
            <p id="selectedGuildIdText" class="session-name">-</p>
            <p id="selectedGuildNameText" class="hint small">Noch kein Server ausgewaehlt.</p>
          </div>
        </section>
        <section class="block">
          <h2>API Verbindung</h2>
          <div class="stack">
            <div>
              <label for="apiBaseUrl">API Base URL</label>
              <input id="apiBaseUrl" placeholder="https://api.deinedomain.de" value="{api_base_url}">
            </div>
            <div>
              <label for="apiToken">Fallback API Token</label>
              <input id="apiToken" type="password" placeholder="Nur noetig ohne Discord-Session">
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
          <h2>Naechste echte Module</h2>
          <ul class="list">
            <li>Moderation Cases im Web</li>
            <li>Verification Settings im Panel</li>
            <li>Reaction Roles verwalten</li>
            <li>Join to Create bearbeiten</li>
          </ul>
        </section>
      </aside>
      <section class="content-shell">
        <section class="hero">
          <h1>Der erste echte Panel-Bereich ist da</h1>
          <p class="muted">Das Panel liest jetzt deine Discord-Session, zeigt dir verwaltbare Server, laedt Channels und Rollen und erstellt Ticket-Panels direkt ueber die Weboberflaeche. So bauen wir Rysio Schritt fuer Schritt in Richtung echtes Kunden-Panel auf.</p>
          <div class="status-row">
            <span class="status-chip good">Discord OAuth live</span>
            <span class="status-chip good">Server-Auswahl live</span>
            <span class="status-chip good">Ticket-Panels per Web</span>
            <span class="status-chip warn">Moderation kommt als naechstes</span>
          </div>
        </section>
        <section class="metrics">
          <article class="metric"><h3>Verwaltbare Server</h3><div class="metric-value" id="guildCountStat">0</div><p class="muted">Kommt direkt aus deinem Discord Login.</p></article>
          <article class="metric"><h3>Ticket-Panels</h3><div class="metric-value" id="ticketPanelCountStat">0</div><p class="muted">Panels fuer den aktuell ausgewaehlten Server.</p></article>
          <article class="metric"><h3>Geladene Logs</h3><div class="metric-value" id="loadedStat">0</div><p class="muted">Kommt direkt aus deiner Audit-Log API.</p></article>
          <article class="metric"><h3>Gesamteintraege</h3><div class="metric-value" id="totalStat">0</div><p class="muted">Hilft spaeter fuer Suche, Pagination und Export.</p></article>
        </section>
        <section class="feature-grid">
          <article class="feature-card"><div class="feature-top"><div><h2>Setup & Branding</h2><p class="muted">Info-Channel, Sprache, Begruessung und Patch Notes folgen als eigener Bereich.</p></div><span class="feature-badge">als naechstes</span></div></article>
          <article class="feature-card"><div class="feature-top"><div><h2>Tickets</h2><p class="muted">Das erste Modul mit echter Web-Funktion: Panels erstellen und vorhandene Panels sehen.</p></div><span class="feature-badge">live</span></div></article>
          <article class="feature-card"><div class="feature-top"><div><h2>Moderation</h2><p class="muted">Warns, Timeouts, Kicks, Bans und Fallhistorie werden direkt danach ins Panel gezogen.</p></div><span class="feature-badge">vorbereitet</span></div></article>
        </section>
        <section class="card">
          <div class="panel-head">
            <div>
              <h2>Ticket Panel Manager</h2>
              <p class="muted">Erstelle Ticket-Panels fuer den ausgewaehlten Server direkt im Browser. Das ist bewusst panel-faehig aufgebaut, damit wir spaeter Bearbeiten, Limits und Premium leichter nachziehen koennen.</p>
            </div>
            <span class="panel-tag">Web -> Discord</span>
          </div>
          <div class="ticket-grid">
            <section class="card">
              <h3>Neues Ticket-Panel erstellen</h3>
              <div class="stack">
                <div>
                  <label for="ticketChannelSelect">Panel Channel</label>
                  <select id="ticketChannelSelect">
                    <option value="">Channel auswaehlen</option>
                  </select>
                </div>
                <div>
                  <label for="ticketCategorySelect">Ticket Kategorie</label>
                  <select id="ticketCategorySelect">
                    <option value="">Keine Kategorie</option>
                  </select>
                </div>
                <div>
                  <label for="ticketSupportRoleSelect">Support Rolle</label>
                  <select id="ticketSupportRoleSelect">
                    <option value="">Keine Support Rolle</option>
                  </select>
                </div>
                <div>
                  <label for="ticketTitleInput">Panel Titel</label>
                  <input id="ticketTitleInput" value="Support Ticket">
                </div>
                <div>
                  <label for="ticketDescriptionInput">Panel Beschreibung</label>
                  <textarea id="ticketDescriptionInput">Klicke unten auf den Button, um ein Ticket zu erstellen.</textarea>
                </div>
                <div>
                  <label for="ticketWelcomeInput">Erste Auto-Nachricht im Ticket</label>
                  <textarea id="ticketWelcomeInput" placeholder="Optional: z. B. Hallo {{user}}, beschreibe bitte dein Anliegen."></textarea>
                </div>
              </div>
              <div class="button-row" style="margin-top:14px;">
                <button id="createTicketPanelButton" type="button">Ticket-Panel erstellen</button>
                <button id="reloadOverviewButton" type="button" class="ghost">Serverdaten neu laden</button>
              </div>
            </section>
            <section class="card">
              <h3>Bestehende Ticket-Panels</h3>
              <div id="ticketPanelsList" class="panel-list">
                <div class="empty">Noch kein Server geladen.</div>
              </div>
            </section>
          </div>
        </section>
        <section class="card">
          <h2>Audit Logs</h2>
          <p class="muted">Die Logs bleiben live nutzbar. Damit hast du jetzt im gleichen Panel sowohl Server-Funktionen als auch den Log-Bereich an einem Ort.</p>
          <p id="statusText" class="meta" style="margin-top:12px;">Bereit.</p>
          <p id="errorText" class="error" hidden style="margin-top:8px;"></p>
          <section id="entries" class="entry-list" style="margin-top:16px;"><div class="empty">Noch keine Daten geladen.</div></section>
        </section>
      </section>
    </div>
  </main>
  <script>
    const DEFAULT_API_BASE_URL = `{api_base_url_js}`;
    const STORAGE_KEY = "rysio-control-panel";

    const apiBaseUrlInput = document.getElementById("apiBaseUrl");
    const guildSelect = document.getElementById("guildSelect");
    const apiTokenInput = document.getElementById("apiToken");
    const limitInput = document.getElementById("limit");
    const eventTypeInput = document.getElementById("eventType");
    const statusText = document.getElementById("statusText");
    const errorText = document.getElementById("errorText");
    const oauthErrorText = document.getElementById("oauthErrorText");
    const totalStat = document.getElementById("totalStat");
    const loadedStat = document.getElementById("loadedStat");
    const guildCountStat = document.getElementById("guildCountStat");
    const ticketPanelCountStat = document.getElementById("ticketPanelCountStat");
    const entries = document.getElementById("entries");
    const sessionUserText = document.getElementById("sessionUserText");
    const sessionGuildCountText = document.getElementById("sessionGuildCountText");
    const selectedGuildIdText = document.getElementById("selectedGuildIdText");
    const selectedGuildNameText = document.getElementById("selectedGuildNameText");
    const ticketChannelSelect = document.getElementById("ticketChannelSelect");
    const ticketCategorySelect = document.getElementById("ticketCategorySelect");
    const ticketSupportRoleSelect = document.getElementById("ticketSupportRoleSelect");
    const ticketTitleInput = document.getElementById("ticketTitleInput");
    const ticketDescriptionInput = document.getElementById("ticketDescriptionInput");
    const ticketWelcomeInput = document.getElementById("ticketWelcomeInput");
    const ticketPanelsList = document.getElementById("ticketPanelsList");

    let sessionToken = "";
    let currentSession = null;
    let currentOverview = null;

    function escapeHtml(value) {{
      return String(value).replaceAll("&", "&amp;").replaceAll("<", "&lt;").replaceAll(">", "&gt;").replaceAll('"', "&quot;").replaceAll("'", "&#39;");
    }}

    function normalizeBaseUrl(value) {{
      return value.trim().replace(/\\/$/, "");
    }}

    function getAuthHeaders() {{
      const headers = {{}};
      if (sessionToken) {{
        headers["X-Rysio-Panel-Token"] = sessionToken;
      }} else {{
        const apiToken = apiTokenInput.value.trim();
        if (apiToken) {{
          headers["Authorization"] = `Bearer ${{apiToken}}`;
        }}
      }}
      return headers;
    }}

    function loadSavedState() {{
      try {{
        const raw = localStorage.getItem(STORAGE_KEY);
        if (!raw) return;
        const saved = JSON.parse(raw);
        apiBaseUrlInput.value = saved.apiBaseUrl || DEFAULT_API_BASE_URL;
        apiTokenInput.value = saved.apiToken || "";
        limitInput.value = saved.limit || "25";
        eventTypeInput.value = saved.eventType || "";
        ticketTitleInput.value = saved.ticketTitle || "Support Ticket";
        ticketDescriptionInput.value = saved.ticketDescription || "Klicke unten auf den Button, um ein Ticket zu erstellen.";
        ticketWelcomeInput.value = saved.ticketWelcome || "";
      }} catch {{}}
    }}

    function saveState() {{
      const payload = {{
        apiBaseUrl: apiBaseUrlInput.value.trim(),
        apiToken: apiTokenInput.value.trim(),
        limit: limitInput.value.trim(),
        eventType: eventTypeInput.value,
        ticketTitle: ticketTitleInput.value,
        ticketDescription: ticketDescriptionInput.value,
        ticketWelcome: ticketWelcomeInput.value,
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

    function setOauthError(message) {{
      if (!message) {{
        oauthErrorText.hidden = true;
        oauthErrorText.textContent = "";
        return;
      }}
      oauthErrorText.hidden = false;
      oauthErrorText.textContent = message;
    }}

    function populateGuildSelect(guilds) {{
      const currentValue = guildSelect.value;
      guildSelect.innerHTML = '<option value="">Server auswaehlen</option>';
      for (const guild of guilds) {{
        const option = document.createElement("option");
        option.value = guild.id;
        option.textContent = guild.bot_in_guild ? `${{guild.name}}` : `${{guild.name}} (Bot fehlt)`;
        option.disabled = !guild.bot_in_guild;
        guildSelect.appendChild(option);
      }}
      if (currentValue && [...guildSelect.options].some((option) => option.value === currentValue && !option.disabled)) {{
        guildSelect.value = currentValue;
      }}
      guildCountStat.textContent = String(guilds.length);
    }}

    function renderSession(session) {{
      currentSession = session;
      if (!session) {{
        sessionUserText.textContent = "Noch nicht eingeloggt.";
        sessionGuildCountText.textContent = "0 verwaltbare Server von Discord geladen.";
        populateGuildSelect([]);
        return;
      }}
      const username = session.user?.global_name || session.user?.username || "Discord User";
      sessionUserText.textContent = `Eingeloggt als ${{username}}.`;
      sessionGuildCountText.textContent = `${{session.guilds.length}} verwaltbare Server von Discord geladen.`;
      populateGuildSelect(session.guilds);
    }}

    function renderOverview(overview) {{
      currentOverview = overview;
      selectedGuildIdText.textContent = overview.guild.id;
      selectedGuildNameText.textContent = overview.guild.name;
      ticketPanelCountStat.textContent = String((overview.ticket_panels || []).length);

      ticketChannelSelect.innerHTML = '<option value="">Channel auswaehlen</option>';
      for (const channel of overview.channels || []) {{
        const option = document.createElement("option");
        option.value = channel.id;
        option.textContent = `#${{channel.name}}`;
        ticketChannelSelect.appendChild(option);
      }}

      ticketCategorySelect.innerHTML = '<option value="">Keine Kategorie</option>';
      for (const category of overview.categories || []) {{
        const option = document.createElement("option");
        option.value = category.id;
        option.textContent = category.name;
        ticketCategorySelect.appendChild(option);
      }}

      ticketSupportRoleSelect.innerHTML = '<option value="">Keine Support Rolle</option>';
      for (const role of overview.roles || []) {{
        const option = document.createElement("option");
        option.value = role.id;
        option.textContent = role.name;
        ticketSupportRoleSelect.appendChild(option);
      }}

      renderTicketPanels(overview.ticket_panels || []);
    }}

    function renderTicketPanels(panels) {{
      if (!panels.length) {{
        ticketPanelsList.innerHTML = '<div class="empty">Noch keine Ticket-Panels fuer diesen Server gefunden.</div>';
        return;
      }}
      ticketPanelsList.innerHTML = panels.map((panel) => `
        <article class="panel-card">
          <div class="panel-head">
            <strong>#${{escapeHtml(panel.channel_name)}}</strong>
            <span class="panel-tag">Panel-ID ${{escapeHtml(panel.id)}}</span>
          </div>
          <div class="panel-meta">
            <div>Message ID: <code>${{escapeHtml(panel.message_id)}}</code></div>
            <div>Kategorie: ${{escapeHtml(panel.category_name || "Keine")}}</div>
            <div>Support Rolle: ${{escapeHtml(panel.support_role_name || "Keine")}}</div>
            <div>Welcome: ${{escapeHtml(panel.welcome_message || "Keine Auto-Nachricht gesetzt.")}}</div>
          </div>
          <div class="button-row" style="margin-top:14px;">
            <button type="button" class="danger-button" data-delete-panel-id="${{escapeHtml(panel.id)}}">Panel loeschen</button>
          </div>
        </article>
      `).join("");

      for (const button of ticketPanelsList.querySelectorAll("[data-delete-panel-id]")) {{
        button.addEventListener("click", async () => {{
          await deleteTicketPanel(button.getAttribute("data-delete-panel-id"));
        }});
      }}
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

    function readHashState() {{
      const fragment = window.location.hash.startsWith("#") ? window.location.hash.slice(1) : "";
      const params = new URLSearchParams(fragment);
      const token = params.get("rysio_panel_token") || "";
      const oauthError = params.get("rysio_oauth_error") || "";
      if (token) {{
        sessionToken = token;
      }}
      if (oauthError) {{
        setOauthError(`Discord Login Fehler: ${{oauthError}}`);
      }}
      if (fragment) {{
        history.replaceState(null, "", window.location.pathname + window.location.search);
      }}
    }}

    async function fetchPanelSession() {{
      if (!sessionToken) {{
        renderSession(null);
        return;
      }}
      try {{
        const response = await fetch(`${{normalizeBaseUrl(apiBaseUrlInput.value || DEFAULT_API_BASE_URL)}}/api/panel/session`, {{
          headers: {{ "X-Rysio-Panel-Token": sessionToken }},
        }});
        const payload = await response.json();
        if (!response.ok) throw new Error(payload.error || "session_failed");
        renderSession(payload);
        setOauthError("");
      }} catch (error) {{
        renderSession(null);
        sessionToken = "";
        setOauthError("Discord-Session ist ungueltig oder abgelaufen.");
        statusText.textContent = error.message || "Session konnte nicht geladen werden.";
      }}
    }}

    async function loadOverview() {{
      const guildId = guildSelect.value;
      const apiBaseUrl = normalizeBaseUrl(apiBaseUrlInput.value || DEFAULT_API_BASE_URL);
      if (!guildId) {{
        currentOverview = null;
        ticketPanelsList.innerHTML = '<div class="empty">Waehle zuerst einen Server aus.</div>';
        selectedGuildIdText.textContent = "-";
        selectedGuildNameText.textContent = "Noch kein Server ausgewaehlt.";
        ticketPanelCountStat.textContent = "0";
        return;
      }}

      saveState();
      setError("");
      statusText.textContent = "Serverdaten werden geladen...";
      try {{
        const response = await fetch(`${{apiBaseUrl}}/api/guilds/${{guildId}}/overview`, {{
          headers: getAuthHeaders(),
        }});
        const payload = await response.json();
        if (!response.ok) throw new Error(payload.error || `HTTP ${{response.status}}`);
        renderOverview(payload);
        statusText.textContent = `Serverdaten fuer ${{payload.guild.name}} geladen.`;
      }} catch (error) {{
        currentOverview = null;
        ticketPanelsList.innerHTML = '<div class="empty">Serverdaten konnten nicht geladen werden.</div>';
        ticketPanelCountStat.textContent = "0";
        setError(`Serverdaten fehlgeschlagen: ${{error.message}}`);
        statusText.textContent = "Fehler beim Laden der Serverdaten.";
      }}
    }}

    async function loadLogs() {{
      const apiBaseUrl = normalizeBaseUrl(apiBaseUrlInput.value || DEFAULT_API_BASE_URL);
      const guildId = guildSelect.value;
      const limit = limitInput.value.trim() || "25";
      const eventType = eventTypeInput.value;
      if (!apiBaseUrl) {{ setError("Bitte zuerst die API Base URL eintragen."); return; }}
      if (!guildId) {{ setError("Bitte zuerst einen Discord Server auswaehlen."); return; }}
      if (!sessionToken && !apiTokenInput.value.trim()) {{
        setError("Bitte per Discord einloggen oder den Fallback API Token eintragen.");
        return;
      }}
      saveState();
      setError("");
      statusText.textContent = "Logs werden geladen...";
      const params = new URLSearchParams({{ limit }});
      if (eventType) params.set("event_type", eventType);
      try {{
        const response = await fetch(`${{apiBaseUrl}}/api/guilds/${{guildId}}/logs?${{params.toString()}}`, {{
          headers: getAuthHeaders(),
        }});
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

    async function createTicketPanel() {{
      const guildId = guildSelect.value;
      const apiBaseUrl = normalizeBaseUrl(apiBaseUrlInput.value || DEFAULT_API_BASE_URL);
      const payload = {{
        channel_id: ticketChannelSelect.value,
        category_id: ticketCategorySelect.value,
        support_role_id: ticketSupportRoleSelect.value,
        title: ticketTitleInput.value.trim(),
        description_text: ticketDescriptionInput.value.trim(),
        welcome_message: ticketWelcomeInput.value.trim(),
      }};
      if (!guildId) {{
        setError("Bitte zuerst einen Discord Server auswaehlen.");
        return;
      }}
      if (!payload.channel_id || !payload.title || !payload.description_text) {{
        setError("Bitte Channel, Titel und Beschreibung fuellen.");
        return;
      }}

      saveState();
      setError("");
      statusText.textContent = "Ticket-Panel wird erstellt...";
      try {{
        const response = await fetch(`${{apiBaseUrl}}/api/guilds/${{guildId}}/tickets/panels`, {{
          method: "POST",
          headers: {{
            ...getAuthHeaders(),
            "Content-Type": "application/json",
          }},
          body: JSON.stringify(payload),
        }});
        const body = await response.json();
        if (!response.ok) throw new Error(body.error || `HTTP ${{response.status}}`);
        statusText.textContent = "Ticket-Panel erfolgreich erstellt.";
        await loadOverview();
      }} catch (error) {{
        setError(`Ticket-Panel fehlgeschlagen: ${{error.message}}`);
        statusText.textContent = "Ticket-Panel konnte nicht erstellt werden.";
      }}
    }}

    async function deleteTicketPanel(panelId) {{
      const guildId = guildSelect.value;
      const apiBaseUrl = normalizeBaseUrl(apiBaseUrlInput.value || DEFAULT_API_BASE_URL);
      if (!guildId || !panelId) return;
      setError("");
      statusText.textContent = "Ticket-Panel wird geloescht...";
      try {{
        const response = await fetch(`${{apiBaseUrl}}/api/guilds/${{guildId}}/tickets/panels/${{panelId}}`, {{
          method: "DELETE",
          headers: getAuthHeaders(),
        }});
        const body = await response.json();
        if (!response.ok) throw new Error(body.error || `HTTP ${{response.status}}`);
        statusText.textContent = "Ticket-Panel geloescht.";
        await loadOverview();
      }} catch (error) {{
        setError(`Loeschen fehlgeschlagen: ${{error.message}}`);
        statusText.textContent = "Ticket-Panel konnte nicht geloescht werden.";
      }}
    }}

    document.getElementById("loadButton").addEventListener("click", loadLogs);
    document.getElementById("saveButton").addEventListener("click", saveState);
    document.getElementById("createTicketPanelButton").addEventListener("click", createTicketPanel);
    document.getElementById("reloadOverviewButton").addEventListener("click", loadOverview);
    document.getElementById("discordLoginButton").addEventListener("click", () => {{
      const apiBaseUrl = normalizeBaseUrl(apiBaseUrlInput.value || DEFAULT_API_BASE_URL);
      window.location.href = `${{apiBaseUrl}}/api/oauth/discord/login`;
    }});
    document.getElementById("discordLogoutButton").addEventListener("click", () => {{
      sessionToken = "";
      currentSession = null;
      currentOverview = null;
      renderSession(null);
      guildSelect.value = "";
      ticketPanelsList.innerHTML = '<div class="empty">Discord-Session getrennt.</div>';
      selectedGuildIdText.textContent = "-";
      selectedGuildNameText.textContent = "Noch kein Server ausgewaehlt.";
      ticketPanelCountStat.textContent = "0";
      setOauthError("");
      statusText.textContent = "Discord-Session lokal entfernt.";
    }});
    guildSelect.addEventListener("change", loadOverview);

    loadSavedState();
    readHashState();
    fetchPanelSession().then(() => {{
      if (guildSelect.value) {{
        loadOverview();
      }}
    }});
  </script>
</body>
</html>
"""
