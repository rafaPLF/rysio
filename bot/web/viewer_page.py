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

    .page {{ width: min(1460px, calc(100% - 28px)); margin: 18px auto 42px; }}
    .topbar {{
      display: flex; justify-content: space-between; align-items: center; gap: 16px;
      padding: 14px 18px; margin-bottom: 18px; border-radius: 20px; border: 1px solid var(--border);
      background: rgba(14, 22, 33, 0.82); box-shadow: var(--shadow); backdrop-filter: blur(14px); flex-wrap: wrap;
    }}
    .brand {{ display: flex; flex-direction: column; gap: 4px; }}
    .brand-mark {{ display: inline-flex; align-items: center; gap: 10px; font-size: 30px; font-weight: 700; letter-spacing: 0.04em; }}
    .brand-sub {{ color: var(--muted); font-size: 13px; max-width: 840px; }}
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
    .block, .hero, .metric, .card, .entry {{
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
    .metrics, .ticket-grid, .log-grid {{ display: grid; gap: 14px; }}
    .metrics {{ grid-template-columns: repeat(auto-fit, minmax(170px, 1fr)); }}
    .ticket-grid {{ grid-template-columns: minmax(0, 1fr) minmax(0, 1fr); }}
    .log-grid {{ grid-template-columns: minmax(0, 1fr); }}
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
    textarea {{ min-height: 110px; resize: vertical; }}
    button {{
      cursor: pointer; background: linear-gradient(135deg, rgba(99, 224, 255, 0.18), rgba(115, 139, 255, 0.18));
      transition: transform 0.15s ease, border-color 0.15s ease, filter 0.15s ease;
    }}
    button:hover {{ transform: translateY(-1px); border-color: rgba(99, 224, 255, 0.55); filter: brightness(1.05); }}
    button:disabled {{ opacity: 0.55; cursor: not-allowed; transform: none; filter: none; }}
    .ghost {{ background: rgba(8, 12, 18, 0.94); }}
    .danger-button {{ background: linear-gradient(135deg, rgba(255, 133, 133, 0.18), rgba(255, 80, 80, 0.16)); }}
    .button-row {{ display: flex; gap: 12px; flex-wrap: wrap; }}
    .button-row button {{ width: auto; min-width: 150px; }}
    .stack {{ display: grid; gap: 14px; }}
    .login-box {{ background: linear-gradient(135deg, rgba(88, 101, 242, 0.18), rgba(99, 224, 255, 0.06)), linear-gradient(180deg, var(--panel-strong), var(--panel-soft)); }}
    .discord-button {{ background: linear-gradient(135deg, rgba(88, 101, 242, 0.32), rgba(88, 101, 242, 0.18)); border-color: rgba(88, 101, 242, 0.45); }}
    .session-box {{ margin-top: 14px; padding: 12px; border-radius: 14px; border: 1px solid var(--border); background: rgba(8, 12, 18, 0.7); }}
    .session-name {{ color: var(--text); margin-bottom: 8px; }}
    .small {{ font-size: 12px; }}
    .panel-list, .ticket-list, .entry-list {{ display: grid; gap: 14px; }}
    .panel-card, .ticket-card {{
      border: 1px solid var(--border); border-radius: 18px; padding: 14px;
      background: linear-gradient(180deg, rgba(17, 25, 37, 0.92), rgba(13, 20, 31, 0.82));
    }}
    .panel-head, .ticket-head, .entry-head {{
      display: flex; justify-content: space-between; gap: 12px; align-items: center; flex-wrap: wrap; margin-bottom: 12px;
    }}
    .panel-tag, .ticket-tag, .entry-type {{
      display: inline-flex; align-items: center; padding: 6px 10px; border-radius: 999px;
      background: rgba(99, 224, 255, 0.12); border: 1px solid rgba(99, 224, 255, 0.34); color: var(--accent); font-size: 12px;
    }}
    .ticket-tag.warn-tag {{
      background: rgba(255, 215, 121, 0.12);
      border-color: rgba(255, 215, 121, 0.3);
      color: var(--yellow);
    }}
    .panel-meta, .ticket-meta {{ display: grid; gap: 8px; color: var(--muted); font-size: 13px; margin-top: 10px; }}
    .ticket-note-list {{ display: grid; gap: 8px; margin-top: 12px; }}
    .ticket-note {{
      padding: 10px; border-radius: 12px; border: 1px solid var(--border); background: rgba(8, 12, 18, 0.66);
    }}
    pre {{
      margin: 0; padding: 12px; border-radius: 14px; background: rgba(5, 9, 14, 0.9);
      border: 1px solid var(--border); color: #dbe8f5; white-space: pre-wrap; word-break: break-word; overflow-x: auto;
    }}
    @media (max-width: 1100px) {{ .layout, .ticket-grid {{ grid-template-columns: 1fr; }} }}
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
        <div class="brand-sub">Ticket-Panels lassen sich jetzt nicht nur erstellen, sondern auch bearbeiten. Dazu kommt eine Web-Uebersicht fuer offene Tickets mit Claim, Status, Team-Notizen und Close direkt aus dem Panel.</div>
      </div>
      <div class="top-actions">
        <div class="pill">Build: Ticket Panel Beta</div>
        <div class="pill">Focus: Support Teams</div>
      </div>
    </header>
    <div class="layout">
      <aside class="sidebar">
        <section class="block login-box">
          <h2>Discord Login</h2>
          <p class="muted">Login mit Discord statt eigene Accounts in deiner Datenbank. Die Rechte werden spaeter pro Team noch feiner getrennt.</p>
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
      </aside>
      <section class="content-shell">
        <section class="hero">
          <h1>Tickets werden jetzt wirklich web-faehig</h1>
          <p class="muted">Das ist der Schritt vom reinen Tech-Demo-Panel zum ersten echten Support-Panel. Panels koennen bearbeitet werden und offene Tickets werden im Browser sichtbar und bedienbar.</p>
          <div class="status-row">
            <span class="status-chip good">Panel Edit live</span>
            <span class="status-chip good">Open Ticket Übersicht</span>
            <span class="status-chip good">Claim / Waiting / Close</span>
            <span class="status-chip warn">Moderation danach</span>
          </div>
        </section>
        <section class="metrics">
          <article class="metric"><h3>Verwaltbare Server</h3><div class="metric-value" id="guildCountStat">0</div><p class="muted">Kommt direkt aus deinem Discord Login.</p></article>
          <article class="metric"><h3>Notifications</h3><div class="metric-value" id="notificationCountStat">0</div><p class="muted">Twitch, Kick und YouTube pro Server.</p></article>
          <article class="metric"><h3>Ticket-Panels</h3><div class="metric-value" id="ticketPanelCountStat">0</div><p class="muted">Panels fuer den aktuell ausgewaehlten Server.</p></article>
          <article class="metric"><h3>Offene Tickets</h3><div class="metric-value" id="activeTicketCountStat">0</div><p class="muted">Open, claimed und waiting_user im Web.</p></article>
          <article class="metric"><h3>Geladene Logs</h3><div class="metric-value" id="loadedStat">0</div><p class="muted">Audit-Logs bleiben parallel nutzbar.</p></article>
        </section>
        <section class="card">
          <div class="panel-head">
            <div>
              <h2>Notification Manager</h2>
              <p class="muted">Benachrichtigungen fuer Twitch, Kick und YouTube direkt im Panel verwalten und manuell pruefen.</p>
            </div>
            <span class="panel-tag">Live Alerts</span>
          </div>
          <div class="ticket-grid">
            <section class="card">
              <h3 id="notificationFormHeading">Neue Notification erstellen</h3>
              <div class="stack">
                <div>
                  <label for="notificationPlatformSelect">Plattform</label>
                  <select id="notificationPlatformSelect">
                    <option value="twitch">Twitch</option>
                    <option value="kick">Kick</option>
                    <option value="youtube">YouTube</option>
                  </select>
                </div>
                <div>
                  <label for="notificationTargetInput">Target</label>
                  <input id="notificationTargetInput" placeholder="Twitch/Kick Username oder YouTube Channel-ID">
                </div>
                <div>
                  <label for="notificationChannelSelect">Discord Channel</label>
                  <select id="notificationChannelSelect">
                    <option value="">Channel auswaehlen</option>
                  </select>
                </div>
                <div>
                  <label for="notificationMentionRoleSelect">Mention Rolle</label>
                  <select id="notificationMentionRoleSelect">
                    <option value="">Keine Mention Rolle</option>
                  </select>
                </div>
              </div>
              <div class="button-row" style="margin-top:14px;">
                <button id="saveNotificationButton" type="button">Notification speichern</button>
                <button id="cancelNotificationEditButton" type="button" class="ghost">Bearbeiten abbrechen</button>
                <button id="checkNotificationsButton" type="button" class="ghost">Jetzt pruefen</button>
              </div>
            </section>
            <section class="card">
              <h3>Bestehende Notifications</h3>
              <div id="notificationList" class="panel-list">
                <div class="empty">Noch kein Server geladen.</div>
              </div>
            </section>
          </div>
        </section>
        <section class="card">
          <div class="panel-head">
            <div>
              <h2>Ticket Panel Manager</h2>
              <p class="muted">Neue Panels erstellen oder bestehende Panels im gleichen Formular bearbeiten.</p>
            </div>
            <span class="panel-tag">Create + Edit</span>
          </div>
          <div class="ticket-grid">
            <section class="card">
              <h3 id="ticketFormHeading">Neues Ticket-Panel erstellen</h3>
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
                  <textarea id="ticketWelcomeInput" placeholder="Optional: z. B. Hallo User, beschreibe bitte dein Anliegen."></textarea>
                </div>
              </div>
              <div class="button-row" style="margin-top:14px;">
                <button id="saveTicketPanelButton" type="button">Ticket-Panel erstellen</button>
                <button id="cancelTicketEditButton" type="button" class="ghost">Bearbeiten abbrechen</button>
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
          <div class="ticket-head">
            <div>
              <h2>Offene Tickets im Web</h2>
              <p class="muted">Hier sehen Supporter direkt offene Tickets, Claims und interne Notizen, ohne alles in Discord suchen zu muessen.</p>
            </div>
            <span class="ticket-tag">Staff View</span>
          </div>
          <div id="activeTicketsList" class="ticket-list">
            <div class="empty">Noch kein Server geladen.</div>
          </div>
        </section>
        <section class="card">
          <h2>Audit Logs</h2>
          <p class="muted">Die Logs bleiben live nutzbar und helfen spaeter fuer Moderation, Tickets und Support-Kontext.</p>
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
    const loadedStat = document.getElementById("loadedStat");
    const guildCountStat = document.getElementById("guildCountStat");
    const notificationCountStat = document.getElementById("notificationCountStat");
    const ticketPanelCountStat = document.getElementById("ticketPanelCountStat");
    const activeTicketCountStat = document.getElementById("activeTicketCountStat");
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
    const activeTicketsList = document.getElementById("activeTicketsList");
    const ticketFormHeading = document.getElementById("ticketFormHeading");
    const saveTicketPanelButton = document.getElementById("saveTicketPanelButton");
    const cancelTicketEditButton = document.getElementById("cancelTicketEditButton");
    const notificationPlatformSelect = document.getElementById("notificationPlatformSelect");
    const notificationTargetInput = document.getElementById("notificationTargetInput");
    const notificationChannelSelect = document.getElementById("notificationChannelSelect");
    const notificationMentionRoleSelect = document.getElementById("notificationMentionRoleSelect");
    const notificationList = document.getElementById("notificationList");
    const notificationFormHeading = document.getElementById("notificationFormHeading");
    const saveNotificationButton = document.getElementById("saveNotificationButton");
    const cancelNotificationEditButton = document.getElementById("cancelNotificationEditButton");

    let sessionToken = "";
    let currentOverview = null;
    let editingPanelId = null;
    let editingNotificationId = null;

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
        if (apiToken) headers["Authorization"] = `Bearer ${{apiToken}}`;
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
      localStorage.setItem(STORAGE_KEY, JSON.stringify({{
        apiBaseUrl: apiBaseUrlInput.value.trim(),
        apiToken: apiTokenInput.value.trim(),
        limit: limitInput.value.trim(),
        eventType: eventTypeInput.value,
        ticketTitle: ticketTitleInput.value,
        ticketDescription: ticketDescriptionInput.value,
        ticketWelcome: ticketWelcomeInput.value,
      }}));
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

    function resetTicketForm() {{
      editingPanelId = null;
      ticketFormHeading.textContent = "Neues Ticket-Panel erstellen";
      saveTicketPanelButton.textContent = "Ticket-Panel erstellen";
      ticketChannelSelect.value = "";
      ticketCategorySelect.value = "";
      ticketSupportRoleSelect.value = "";
      ticketTitleInput.value = "Support Ticket";
      ticketDescriptionInput.value = "Klicke unten auf den Button, um ein Ticket zu erstellen.";
      ticketWelcomeInput.value = "";
    }}

    function resetNotificationForm() {{
      editingNotificationId = null;
      notificationFormHeading.textContent = "Neue Notification erstellen";
      saveNotificationButton.textContent = "Notification speichern";
      notificationPlatformSelect.value = "twitch";
      notificationTargetInput.value = "";
      notificationChannelSelect.value = "";
      notificationMentionRoleSelect.value = "";
    }}

    function fillTicketForm(panel) {{
      editingPanelId = panel.id;
      ticketFormHeading.textContent = `Ticket-Panel bearbeiten (#${{panel.channel_name}})`;
      saveTicketPanelButton.textContent = "Ticket-Panel speichern";
      ticketChannelSelect.value = panel.channel_id || "";
      ticketCategorySelect.value = panel.category_id || "";
      ticketSupportRoleSelect.value = panel.support_role_id || "";
      ticketTitleInput.value = panel.title || "Support Ticket";
      ticketDescriptionInput.value = panel.description_text || "";
      ticketWelcomeInput.value = panel.welcome_message || "";
      statusText.textContent = `Bearbeitungsmodus fuer Panel #${{panel.id}} aktiviert.`;
      window.scrollTo({{ top: 0, behavior: "smooth" }});
    }}

    function fillNotificationForm(subscription) {{
      editingNotificationId = subscription.id;
      notificationFormHeading.textContent = `Notification bearbeiten (${{subscription.platform}})`;
      saveNotificationButton.textContent = "Notification aktualisieren";
      notificationPlatformSelect.value = subscription.platform || "twitch";
      notificationTargetInput.value = subscription.target || "";
      notificationChannelSelect.value = subscription.announce_channel_id || "";
      notificationMentionRoleSelect.value = subscription.mention_role_id || "";
      statusText.textContent = `Bearbeitungsmodus fuer Notification #${{subscription.id}} aktiviert.`;
      window.scrollTo({{ top: 0, behavior: "smooth" }});
    }}

    function populateGuildSelect(guilds) {{
      const currentValue = guildSelect.value;
      guildSelect.innerHTML = '<option value="">Server auswaehlen</option>';
      for (const guild of guilds) {{
        const option = document.createElement("option");
        option.value = guild.id;
        option.textContent = guild.bot_in_guild ? guild.name : `${{guild.name}} (Bot fehlt)`;
        option.disabled = !guild.bot_in_guild;
        guildSelect.appendChild(option);
      }}
      if (currentValue && [...guildSelect.options].some((option) => option.value === currentValue && !option.disabled)) {{
        guildSelect.value = currentValue;
      }}
      guildCountStat.textContent = String(guilds.length);
    }}

    function renderSession(session) {{
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

    function renderNotifications(subscriptions) {{
      notificationCountStat.textContent = String(subscriptions.length);
      if (!subscriptions.length) {{
        notificationList.innerHTML = '<div class="empty">Noch keine Notifications fuer diesen Server gefunden.</div>';
        return;
      }}
      notificationList.innerHTML = subscriptions.map((subscription) => `
        <article class="panel-card">
          <div class="panel-head">
            <strong>${{escapeHtml(subscription.platform)}} | ${{escapeHtml(subscription.target)}}</strong>
            <span class="panel-tag">Notification-ID ${{escapeHtml(subscription.id)}}</span>
          </div>
          <div class="panel-meta">
            <div>Channel: <strong>#${{escapeHtml(subscription.announce_channel_name)}}</strong></div>
            <div>Mention Rolle: ${{escapeHtml(subscription.mention_role_name || "Keine")}}</div>
            <div>Letzter Inhalt: <code>${{escapeHtml(subscription.last_seen_content_id || "-")}}</code></div>
            <div>Status: ${{subscription.enabled ? "aktiv" : "deaktiviert"}}</div>
          </div>
          <div class="button-row" style="margin-top:14px;">
            <button type="button" data-edit-notification-id="${{escapeHtml(subscription.id)}}">Bearbeiten</button>
            <button type="button" class="danger-button" data-delete-notification-id="${{escapeHtml(subscription.id)}}">Loeschen</button>
          </div>
        </article>
      `).join("");

      for (const button of notificationList.querySelectorAll("[data-edit-notification-id]")) {{
        button.addEventListener("click", () => {{
          const subscription = subscriptions.find((entry) => String(entry.id) === String(button.getAttribute("data-edit-notification-id")));
          if (subscription) fillNotificationForm(subscription);
        }});
      }}
      for (const button of notificationList.querySelectorAll("[data-delete-notification-id]")) {{
        button.addEventListener("click", async () => {{
          await deleteNotification(button.getAttribute("data-delete-notification-id"));
        }});
      }}
    }}

    function renderTicketPanels(panels) {{
      ticketPanelCountStat.textContent = String(panels.length);
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
            <div>Titel: <strong>${{escapeHtml(panel.title || "Support Ticket")}}</strong></div>
            <div>Beschreibung: ${{escapeHtml(panel.description_text || "-")}}</div>
            <div>Kategorie: ${{escapeHtml(panel.category_name || "Keine")}}</div>
            <div>Support Rolle: ${{escapeHtml(panel.support_role_name || "Keine")}}</div>
            <div>Welcome: ${{escapeHtml(panel.welcome_message || "Keine Auto-Nachricht gesetzt.")}}</div>
            <div>Message ID: <code>${{escapeHtml(panel.message_id)}}</code></div>
          </div>
          <div class="button-row" style="margin-top:14px;">
            <button type="button" data-edit-panel-id="${{escapeHtml(panel.id)}}">Panel bearbeiten</button>
            <button type="button" class="danger-button" data-delete-panel-id="${{escapeHtml(panel.id)}}">Panel loeschen</button>
          </div>
        </article>
      `).join("");

      for (const button of ticketPanelsList.querySelectorAll("[data-edit-panel-id]")) {{
        button.addEventListener("click", () => {{
          const panel = panels.find((entry) => String(entry.id) === String(button.getAttribute("data-edit-panel-id")));
          if (panel) fillTicketForm(panel);
        }});
      }}
      for (const button of ticketPanelsList.querySelectorAll("[data-delete-panel-id]")) {{
        button.addEventListener("click", async () => {{
          await deleteTicketPanel(button.getAttribute("data-delete-panel-id"));
        }});
      }}
    }}

    function renderActiveTickets(tickets) {{
      activeTicketCountStat.textContent = String(tickets.length);
      if (!tickets.length) {{
        activeTicketsList.innerHTML = '<div class="empty">Keine offenen Tickets fuer diesen Server gefunden.</div>';
        return;
      }}
      activeTicketsList.innerHTML = tickets.map((ticket) => `
        <article class="ticket-card">
          <div class="ticket-head">
            <div>
              <strong>#${{escapeHtml(ticket.channel_name)}}</strong>
              <p class="muted small">Ticket-ID ${{escapeHtml(ticket.id)}} | Ersteller: ${{escapeHtml(ticket.opener_name)}}</p>
            </div>
            <span class="ticket-tag ${{ticket.status === "waiting_user" ? "warn-tag" : ""}}">${{escapeHtml(ticket.status)}}</span>
          </div>
          <div class="ticket-meta">
            <div>Claimed By: ${{escapeHtml(ticket.claimed_by_name || "-")}}</div>
            <div>Erstellt: ${{escapeHtml(ticket.created_at || "-")}}</div>
            <div>Transcript: ${{escapeHtml(ticket.transcript_path || "-")}}</div>
          </div>
          <div class="button-row" style="margin-top:14px;">
            <button type="button" data-claim-ticket-id="${{escapeHtml(ticket.id)}}">Claim</button>
            <button type="button" class="ghost" data-waiting-ticket-id="${{escapeHtml(ticket.id)}}">Wartet auf User</button>
            <button type="button" class="danger-button" data-close-ticket-id="${{escapeHtml(ticket.id)}}">Close</button>
          </div>
          <div class="stack" style="margin-top:14px;">
            <div>
              <label for="ticket-note-${{escapeHtml(ticket.id)}}">Team-Notiz</label>
              <textarea id="ticket-note-${{escapeHtml(ticket.id)}}" placeholder="Interne Notiz fuer das Team..."></textarea>
            </div>
            <div class="button-row">
              <button type="button" data-note-ticket-id="${{escapeHtml(ticket.id)}}">Notiz speichern</button>
            </div>
          </div>
          <div class="ticket-note-list">
            ${{ticket.notes && ticket.notes.length ? ticket.notes.map((note) => `
              <div class="ticket-note">
                <strong>${{escapeHtml(note.author_username)}}</strong>
                <div class="muted small">${{escapeHtml(note.created_at || "-")}}</div>
                <div>${{escapeHtml(note.note_text)}}</div>
              </div>
            `).join("") : '<div class="empty">Noch keine Team-Notizen.</div>'}}
          </div>
        </article>
      `).join("");

      for (const button of activeTicketsList.querySelectorAll("[data-claim-ticket-id]")) {{
        button.addEventListener("click", async () => runTicketAction(button.getAttribute("data-claim-ticket-id"), "claim"));
      }}
      for (const button of activeTicketsList.querySelectorAll("[data-waiting-ticket-id]")) {{
        button.addEventListener("click", async () => runTicketAction(button.getAttribute("data-waiting-ticket-id"), "waiting-user"));
      }}
      for (const button of activeTicketsList.querySelectorAll("[data-close-ticket-id]")) {{
        button.addEventListener("click", async () => runTicketAction(button.getAttribute("data-close-ticket-id"), "close"));
      }}
      for (const button of activeTicketsList.querySelectorAll("[data-note-ticket-id]")) {{
        button.addEventListener("click", async () => {{
          const ticketId = button.getAttribute("data-note-ticket-id");
          const textarea = document.getElementById(`ticket-note-${{ticketId}}`);
          await saveTicketNote(ticketId, textarea.value);
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
        return `<article class="entry"><div class="entry-head"><span class="entry-type">${{escapeHtml(item.event_type)}}</span><span class="meta">${{escapeHtml(item.created_at || "unbekannt")}}</span></div><p class="meta">${{escapeHtml(item.summary)}}</p><pre>${{escapeHtml(details)}}</pre></article>`;
      }}).join("");
    }}

    function renderOverview(overview) {{
      currentOverview = overview;
      selectedGuildIdText.textContent = overview.guild.id;
      selectedGuildNameText.textContent = overview.guild.name;

      ticketChannelSelect.innerHTML = '<option value="">Channel auswaehlen</option>';
      notificationChannelSelect.innerHTML = '<option value="">Channel auswaehlen</option>';
      for (const channel of overview.channels || []) {{
        const option = document.createElement("option");
        option.value = channel.id;
        option.textContent = `#${{channel.name}}`;
        ticketChannelSelect.appendChild(option);

        const notificationOption = document.createElement("option");
        notificationOption.value = channel.id;
        notificationOption.textContent = `#${{channel.name}}`;
        notificationChannelSelect.appendChild(notificationOption);
      }}

      ticketCategorySelect.innerHTML = '<option value="">Keine Kategorie</option>';
      for (const category of overview.categories || []) {{
        const option = document.createElement("option");
        option.value = category.id;
        option.textContent = category.name;
        ticketCategorySelect.appendChild(option);
      }}

      ticketSupportRoleSelect.innerHTML = '<option value="">Keine Support Rolle</option>';
      notificationMentionRoleSelect.innerHTML = '<option value="">Keine Mention Rolle</option>';
      for (const role of overview.roles || []) {{
        const option = document.createElement("option");
        option.value = role.id;
        option.textContent = role.name;
        ticketSupportRoleSelect.appendChild(option);

        const notificationRoleOption = document.createElement("option");
        notificationRoleOption.value = role.id;
        notificationRoleOption.textContent = role.name;
        notificationMentionRoleSelect.appendChild(notificationRoleOption);
      }}

      renderNotifications(overview.notifications || []);
      renderTicketPanels(overview.ticket_panels || []);
      renderActiveTickets(overview.active_tickets || []);
    }}

    function readHashState() {{
      const fragment = window.location.hash.startsWith("#") ? window.location.hash.slice(1) : "";
      const params = new URLSearchParams(fragment);
      const token = params.get("rysio_panel_token") || "";
      const oauthError = params.get("rysio_oauth_error") || "";
      if (token) sessionToken = token;
      if (oauthError) setOauthError(`Discord Login Fehler: ${{oauthError}}`);
      if (fragment) history.replaceState(null, "", window.location.pathname + window.location.search);
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
        sessionToken = "";
        renderSession(null);
        setOauthError("Discord-Session ist ungueltig oder abgelaufen.");
        statusText.textContent = error.message || "Session konnte nicht geladen werden.";
      }}
    }}

    async function loadOverview() {{
      const guildId = guildSelect.value;
      const apiBaseUrl = normalizeBaseUrl(apiBaseUrlInput.value || DEFAULT_API_BASE_URL);
      if (!guildId) {{
        currentOverview = null;
        selectedGuildIdText.textContent = "-";
        selectedGuildNameText.textContent = "Noch kein Server ausgewaehlt.";
        notificationList.innerHTML = '<div class="empty">Waehle zuerst einen Server aus.</div>';
        ticketPanelsList.innerHTML = '<div class="empty">Waehle zuerst einen Server aus.</div>';
        activeTicketsList.innerHTML = '<div class="empty">Waehle zuerst einen Server aus.</div>';
        notificationCountStat.textContent = "0";
        ticketPanelCountStat.textContent = "0";
        activeTicketCountStat.textContent = "0";
        resetTicketForm();
        resetNotificationForm();
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
        resetTicketForm();
        resetNotificationForm();
        statusText.textContent = `Serverdaten fuer ${{payload.guild.name}} geladen.`;
      }} catch (error) {{
        currentOverview = null;
        notificationList.innerHTML = '<div class="empty">Notifications konnten nicht geladen werden.</div>';
        ticketPanelsList.innerHTML = '<div class="empty">Serverdaten konnten nicht geladen werden.</div>';
        activeTicketsList.innerHTML = '<div class="empty">Tickets konnten nicht geladen werden.</div>';
        notificationCountStat.textContent = "0";
        ticketPanelCountStat.textContent = "0";
        activeTicketCountStat.textContent = "0";
        setError(`Serverdaten fehlgeschlagen: ${{error.message}}`);
        statusText.textContent = "Fehler beim Laden der Serverdaten.";
      }}
    }}

    async function saveNotification() {{
      const guildId = guildSelect.value;
      const apiBaseUrl = normalizeBaseUrl(apiBaseUrlInput.value || DEFAULT_API_BASE_URL);
      const wasEditing = Boolean(editingNotificationId);
      const payload = {{
        platform: notificationPlatformSelect.value,
        target: notificationTargetInput.value.trim(),
        announce_channel_id: notificationChannelSelect.value,
        mention_role_id: notificationMentionRoleSelect.value,
      }};

      if (!guildId) {{ setError("Bitte zuerst einen Discord Server auswaehlen."); return; }}
      if (!payload.platform || !payload.target || !payload.announce_channel_id) {{
        setError("Bitte Plattform, Target und Channel fuellen.");
        return;
      }}

      setError("");
      statusText.textContent = wasEditing ? "Notification wird aktualisiert..." : "Notification wird erstellt...";
      try {{
        const endpoint = wasEditing
          ? `${{apiBaseUrl}}/api/guilds/${{guildId}}/notifications/${{editingNotificationId}}`
          : `${{apiBaseUrl}}/api/guilds/${{guildId}}/notifications`;
        const method = wasEditing ? "PATCH" : "POST";
        const response = await fetch(endpoint, {{
          method,
          headers: {{
            ...getAuthHeaders(),
            "Content-Type": "application/json",
          }},
          body: JSON.stringify(payload),
        }});
        const body = await response.json();
        if (!response.ok) throw new Error(body.error || `HTTP ${{response.status}}`);
        resetNotificationForm();
        await loadOverview();
        statusText.textContent = wasEditing ? "Notification gespeichert." : "Notification erstellt.";
      }} catch (error) {{
        setError(`Notification fehlgeschlagen: ${{error.message}}`);
        statusText.textContent = "Notification konnte nicht gespeichert werden.";
      }}
    }}

    async function deleteNotification(subscriptionId) {{
      const guildId = guildSelect.value;
      const apiBaseUrl = normalizeBaseUrl(apiBaseUrlInput.value || DEFAULT_API_BASE_URL);
      if (!guildId || !subscriptionId) return;
      setError("");
      statusText.textContent = "Notification wird geloescht...";
      try {{
        const response = await fetch(`${{apiBaseUrl}}/api/guilds/${{guildId}}/notifications/${{subscriptionId}}`, {{
          method: "DELETE",
          headers: getAuthHeaders(),
        }});
        const body = await response.json();
        if (!response.ok) throw new Error(body.error || `HTTP ${{response.status}}`);
        if (String(editingNotificationId) === String(subscriptionId)) resetNotificationForm();
        await loadOverview();
        statusText.textContent = "Notification geloescht.";
      }} catch (error) {{
        setError(`Notification-Loeschen fehlgeschlagen: ${{error.message}}`);
        statusText.textContent = "Notification konnte nicht geloescht werden.";
      }}
    }}

    async function checkNotificationsNow() {{
      const guildId = guildSelect.value;
      const apiBaseUrl = normalizeBaseUrl(apiBaseUrlInput.value || DEFAULT_API_BASE_URL);
      if (!guildId) {{ setError("Bitte zuerst einen Discord Server auswaehlen."); return; }}
      setError("");
      statusText.textContent = "Notifications werden jetzt manuell geprueft...";
      try {{
        const response = await fetch(`${{apiBaseUrl}}/api/guilds/${{guildId}}/notifications/check`, {{
          method: "POST",
          headers: getAuthHeaders(),
        }});
        const body = await response.json();
        if (!response.ok) throw new Error(body.error || `HTTP ${{response.status}}`);
        statusText.textContent = `Notification-Check abgeschlossen. Geprueft: ${{body.processed ?? 0}}.`;
      }} catch (error) {{
        setError(`Notification-Check fehlgeschlagen: ${{error.message}}`);
        statusText.textContent = "Notification-Check fehlgeschlagen.";
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
        loadedStat.textContent = String(payload.items?.length ?? 0);
        renderEntries(payload.items || []);
        statusText.textContent = `Erfolgreich geladen: ${{payload.items?.length ?? 0}} Log-Eintraege.`;
      }} catch (error) {{
        loadedStat.textContent = "0";
        entries.innerHTML = '<div class="empty">Keine Daten dargestellt.</div>';
        setError(`Abruf fehlgeschlagen: ${{error.message}}`);
        statusText.textContent = "Fehler beim Laden.";
      }}
    }}

    async function saveTicketPanel() {{
      const guildId = guildSelect.value;
      const apiBaseUrl = normalizeBaseUrl(apiBaseUrlInput.value || DEFAULT_API_BASE_URL);
      const wasEditing = Boolean(editingPanelId);
      const payload = {{
        channel_id: ticketChannelSelect.value,
        category_id: ticketCategorySelect.value,
        support_role_id: ticketSupportRoleSelect.value,
        title: ticketTitleInput.value.trim(),
        description_text: ticketDescriptionInput.value.trim(),
        welcome_message: ticketWelcomeInput.value.trim(),
      }};

      if (!guildId) {{ setError("Bitte zuerst einen Discord Server auswaehlen."); return; }}
      if (!payload.channel_id || !payload.title || !payload.description_text) {{
        setError("Bitte Channel, Titel und Beschreibung fuellen.");
        return;
      }}

      setError("");
      saveState();
      statusText.textContent = editingPanelId ? "Ticket-Panel wird gespeichert..." : "Ticket-Panel wird erstellt...";
      try {{
        const endpoint = editingPanelId
          ? `${{apiBaseUrl}}/api/guilds/${{guildId}}/tickets/panels/${{editingPanelId}}`
          : `${{apiBaseUrl}}/api/guilds/${{guildId}}/tickets/panels`;
        const method = editingPanelId ? "PATCH" : "POST";
        const response = await fetch(endpoint, {{
          method,
          headers: {{
            ...getAuthHeaders(),
            "Content-Type": "application/json",
          }},
          body: JSON.stringify(payload),
        }});
        const body = await response.json();
        if (!response.ok) throw new Error(body.error || `HTTP ${{response.status}}`);
        resetTicketForm();
        await loadOverview();
        statusText.textContent = wasEditing ? "Ticket-Panel gespeichert." : "Ticket-Panel erstellt.";
      }} catch (error) {{
        setError(`Ticket-Panel fehlgeschlagen: ${{error.message}}`);
        statusText.textContent = "Ticket-Panel konnte nicht gespeichert werden.";
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
        if (String(editingPanelId) === String(panelId)) resetTicketForm();
        await loadOverview();
        statusText.textContent = "Ticket-Panel geloescht.";
      }} catch (error) {{
        setError(`Loeschen fehlgeschlagen: ${{error.message}}`);
        statusText.textContent = "Ticket-Panel konnte nicht geloescht werden.";
      }}
    }}

    async function runTicketAction(ticketId, action) {{
      const guildId = guildSelect.value;
      const apiBaseUrl = normalizeBaseUrl(apiBaseUrlInput.value || DEFAULT_API_BASE_URL);
      if (!guildId || !ticketId) return;
      setError("");
      statusText.textContent = `Ticket-Aktion '${{action}}' wird ausgefuehrt...`;
      try {{
        const response = await fetch(`${{apiBaseUrl}}/api/guilds/${{guildId}}/tickets/${{ticketId}}/${{action}}`, {{
          method: "POST",
          headers: getAuthHeaders(),
        }});
        const body = await response.json();
        if (!response.ok) throw new Error(body.error || `HTTP ${{response.status}}`);
        await loadOverview();
        statusText.textContent = `Ticket-Aktion '${{action}}' erfolgreich.`;
      }} catch (error) {{
        setError(`Ticket-Aktion fehlgeschlagen: ${{error.message}}`);
        statusText.textContent = "Ticket-Aktion fehlgeschlagen.";
      }}
    }}

    async function saveTicketNote(ticketId, noteText) {{
      const guildId = guildSelect.value;
      const apiBaseUrl = normalizeBaseUrl(apiBaseUrlInput.value || DEFAULT_API_BASE_URL);
      if (!guildId || !ticketId) return;
      if (!noteText.trim()) {{
        setError("Bitte zuerst einen Notiz-Text eintragen.");
        return;
      }}
      setError("");
      statusText.textContent = "Team-Notiz wird gespeichert...";
      try {{
        const response = await fetch(`${{apiBaseUrl}}/api/guilds/${{guildId}}/tickets/${{ticketId}}/note`, {{
          method: "POST",
          headers: {{
            ...getAuthHeaders(),
            "Content-Type": "application/json",
          }},
          body: JSON.stringify({{ note_text: noteText.trim() }}),
        }});
        const body = await response.json();
        if (!response.ok) throw new Error(body.error || `HTTP ${{response.status}}`);
        await loadOverview();
        statusText.textContent = "Team-Notiz gespeichert.";
      }} catch (error) {{
        setError(`Notiz fehlgeschlagen: ${{error.message}}`);
        statusText.textContent = "Notiz konnte nicht gespeichert werden.";
      }}
    }}

    document.getElementById("loadButton").addEventListener("click", loadLogs);
    document.getElementById("saveButton").addEventListener("click", saveState);
    document.getElementById("reloadOverviewButton").addEventListener("click", loadOverview);
    document.getElementById("saveTicketPanelButton").addEventListener("click", saveTicketPanel);
    cancelTicketEditButton.addEventListener("click", resetTicketForm);
    saveNotificationButton.addEventListener("click", saveNotification);
    cancelNotificationEditButton.addEventListener("click", resetNotificationForm);
    document.getElementById("checkNotificationsButton").addEventListener("click", checkNotificationsNow);
    document.getElementById("discordLoginButton").addEventListener("click", () => {{
      const apiBaseUrl = normalizeBaseUrl(apiBaseUrlInput.value || DEFAULT_API_BASE_URL);
      window.location.href = `${{apiBaseUrl}}/api/oauth/discord/login`;
    }});
    document.getElementById("discordLogoutButton").addEventListener("click", () => {{
      sessionToken = "";
      currentOverview = null;
      renderSession(null);
      guildSelect.value = "";
      selectedGuildIdText.textContent = "-";
      selectedGuildNameText.textContent = "Noch kein Server ausgewaehlt.";
      notificationList.innerHTML = '<div class="empty">Discord-Session getrennt.</div>';
      ticketPanelsList.innerHTML = '<div class="empty">Discord-Session getrennt.</div>';
      activeTicketsList.innerHTML = '<div class="empty">Discord-Session getrennt.</div>';
      notificationCountStat.textContent = "0";
      ticketPanelCountStat.textContent = "0";
      activeTicketCountStat.textContent = "0";
      resetTicketForm();
      resetNotificationForm();
      setOauthError("");
      statusText.textContent = "Discord-Session lokal entfernt.";
    }});
    guildSelect.addEventListener("change", loadOverview);

    loadSavedState();
    readHashState();
    fetchPanelSession().then(() => {{
      if (guildSelect.value) loadOverview();
    }});
  </script>
</body>
</html>
"""
