import os
import re
import sqlite3
from datetime import datetime, timezone
import requests
from flask import Flask, request, jsonify, make_response, session, redirect
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "gelo_super_secret_production_key_998811")

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
AUDD_API_KEY = os.getenv("AUDD_API_KEY", "").strip()
DB_FILE = "users.db"

def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            display_name TEXT,
            password_hash TEXT NOT NULL
        )
    """)
    # Ensure display_name column exists for existing databases
    c.execute("PRAGMA table_info(users)")
    cols = [col[1] for col in c.fetchall()]
    if "display_name" not in cols:
        c.execute("ALTER TABLE users ADD COLUMN display_name TEXT")
    conn.commit()
    conn.close()

init_db()

# --- AUTH TEMPLATE ---
AUTH_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0">
  <title>HELLO Gelo - Authentication</title>
  <style>
    :root {
      --bg: #07090e;
      --card-bg: rgba(18, 24, 38, 0.85);
      --card-border: rgba(255, 255, 255, 0.08);
      --accent: #38bdf8;
      --primary: #2563eb;
      --text: #f1f5f9;
      --text-muted: #94a3b8;
    }
    * { box-sizing: border-box; margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; }
    body {
      background-color: var(--bg);
      background-image: 
        radial-gradient(circle at 15% 15%, rgba(56, 189, 248, 0.08) 0%, transparent 40%),
        radial-gradient(circle at 85% 85%, rgba(37, 99, 235, 0.08) 0%, transparent 40%);
      color: var(--text);
      min-height: 100vh;
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      padding: 20px 16px;
    }
    .brand { display: flex; align-items: center; gap: 8px; margin-bottom: 20px; }
    .brand-icon { font-size: 26px; }
    .brand-title {
      font-size: 26px;
      font-weight: 800;
      letter-spacing: -0.5px;
      background: linear-gradient(135deg, #ffffff 30%, #38bdf8 100%);
      -webkit-background-clip: text;
      -webkit-text-fill-color: transparent;
    }
    .auth-card {
      background: var(--card-bg);
      border: 1px solid var(--card-border);
      border-radius: 18px;
      padding: 24px;
      width: 100%;
      max-width: 380px;
      box-shadow: 0 20px 40px rgba(0, 0, 0, 0.4);
    }
    .auth-toggle {
      display: flex;
      background: rgba(15, 23, 42, 0.85);
      border: 1px solid var(--card-border);
      padding: 4px;
      border-radius: 12px;
      margin-bottom: 20px;
    }
    .toggle-btn {
      flex: 1;
      border: none;
      background: transparent;
      color: var(--text-muted);
      padding: 8px;
      border-radius: 9px;
      font-size: 13.5px;
      font-weight: 600;
      cursor: pointer;
    }
    .toggle-btn.active { background: rgba(56, 189, 248, 0.15); color: var(--accent); }
    .form-group { margin-bottom: 14px; }
    .form-group label { display: block; font-size: 12px; font-weight: 600; color: var(--text-muted); margin-bottom: 6px; }
    .form-input {
      width: 100%;
      background: rgba(8, 12, 22, 0.7);
      border: 1px solid rgba(255, 255, 255, 0.12);
      color: var(--text);
      padding: 12px 14px;
      border-radius: 10px;
      font-size: 14px;
      outline: none;
    }
    .form-input:focus { border-color: var(--accent); }
    .auth-submit {
      width: 100%;
      background: linear-gradient(135deg, #2563eb, #1d4ed8);
      border: none;
      color: #fff;
      padding: 12px;
      border-radius: 10px;
      font-size: 14.5px;
      font-weight: 700;
      cursor: pointer;
      margin-top: 6px;
    }
    .error-msg {
      color: #f87171;
      background: rgba(239, 68, 68, 0.1);
      border: 1px solid rgba(239, 68, 68, 0.2);
      padding: 8px 12px;
      border-radius: 8px;
      font-size: 13px;
      margin-bottom: 14px;
      display: none;
    }
  </style>
</head>
<body>
  <div class="brand">
    <span class="brand-icon">⚡</span>
    <span class="brand-title">HELLO Gelo</span>
  </div>

  <div class="auth-card">
    <div class="auth-toggle">
      <button class="toggle-btn active" id="tabLogin" onclick="setMode('login')">Sign In</button>
      <button class="toggle-btn" id="tabRegister" onclick="setMode('register')">Register</button>
    </div>

    <div id="authError" class="error-msg"></div>

    <form onsubmit="handleAuth(event)">
      <div class="form-group" id="displayNameGroup" style="display: none;">
        <label>Display Name (Nickname)</label>
        <input type="text" class="form-input" id="authDisplayName" placeholder="e.g. Mike">
      </div>
      <div class="form-group">
        <label id="userLabel">Username or Email</label>
        <input type="text" class="form-input" id="authUsername" required autocomplete="username">
      </div>
      <div class="form-group">
        <label>Password</label>
        <input type="password" class="form-input" id="authPassword" required autocomplete="current-password">
      </div>
      <button type="submit" class="auth-submit" id="submitBtn">Sign In</button>
    </form>
  </div>

  <script>
    let mode = 'login';
    function setMode(newMode) {
      mode = newMode;
      document.getElementById('tabLogin').classList.toggle('active', mode === 'login');
      document.getElementById('tabRegister').classList.toggle('active', mode === 'register');
      document.getElementById('submitBtn').innerText = mode === 'login' ? 'Sign In' : 'Create Account';
      document.getElementById('displayNameGroup').style.display = mode === 'register' ? 'block' : 'none';
      document.getElementById('authError').style.display = 'none';
    }

    async function handleAuth(e) {
      e.preventDefault();
      const username = document.getElementById('authUsername').value.trim();
      const password = document.getElementById('authPassword').value;
      const displayName = document.getElementById('authDisplayName').value.trim();
      const errBox = document.getElementById('authError');
      errBox.style.display = 'none';

      const endpoint = mode === 'login' ? '/api/login' : '/api/register';
      try {
        const res = await fetch(endpoint, {
          method: 'POST',
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify({ username, password, display_name: displayName })
        });
        const data = await res.json();
        if (res.ok) {
          window.location.href = '/';
        } else {
          errBox.innerText = data.error || 'Authentication failed.';
          errBox.style.display = 'block';
        }
      } catch (err) {
        errBox.innerText = 'Network error: ' + err.message;
        errBox.style.display = 'block';
      }
    }
  </script>
</body>
</html>
"""

# --- MAIN APP TEMPLATE ---
MAIN_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
  <title>HELLO Gelo</title>
  <style>
    :root {
      --bg: #07090e;
      --card-bg: rgba(18, 24, 38, 0.85);
      --card-border: rgba(255, 255, 255, 0.08);
      --accent: #38bdf8;
      --accent-glow: rgba(56, 189, 248, 0.35);
      --primary: #2563eb;
      --text: #f1f5f9;
      --text-muted: #94a3b8;
    }
    * { box-sizing: border-box; margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; -webkit-tap-highlight-color: transparent; }
    body {
      background-color: var(--bg);
      background-image: 
        radial-gradient(circle at 15% 15%, rgba(56, 189, 248, 0.08) 0%, transparent 40%),
        radial-gradient(circle at 85% 85%, rgba(37, 99, 235, 0.08) 0%, transparent 40%);
      color: var(--text);
      min-height: 100vh;
      display: flex;
      flex-direction: column;
      align-items: center;
      padding: 16px 12px 20px;
    }
    .top-nav {
      width: 100%;
      max-width: 480px;
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 12px;
    }
    .brand { display: flex; align-items: center; gap: 8px; }
    .brand-icon { font-size: 24px; filter: drop-shadow(0 0 12px var(--accent)); }
    .brand-title {
      font-size: 22px;
      font-weight: 800;
      letter-spacing: -0.5px;
      background: linear-gradient(135deg, #ffffff 30%, #38bdf8 100%);
      -webkit-background-clip: text;
      -webkit-text-fill-color: transparent;
    }
    .user-tag {
      font-size: 13px;
      color: var(--text-muted);
      display: flex;
      align-items: center;
      gap: 10px;
    }
    .user-badge {
      background: rgba(56, 189, 248, 0.12);
      border: 1px solid rgba(56, 189, 248, 0.25);
      color: var(--accent);
      padding: 4px 10px;
      border-radius: 8px;
      cursor: pointer;
      font-weight: 600;
      display: flex;
      align-items: center;
      gap: 5px;
    }
    .logout-btn { color: #f87171; text-decoration: underline; cursor: pointer; font-weight: 600; font-size: 12px; }
    .tab-bar {
      display: flex;
      background: rgba(15, 23, 42, 0.85);
      border: 1px solid var(--card-border);
      padding: 4px;
      border-radius: 12px;
      width: 100%;
      max-width: 480px;
      margin-bottom: 12px;
    }
    .tab-btn {
      flex: 1;
      border: none;
      background: transparent;
      color: var(--text-muted);
      padding: 9px 12px;
      border-radius: 9px;
      font-size: 13.5px;
      font-weight: 600;
      cursor: pointer;
      display: flex;
      align-items: center;
      justify-content: center;
      gap: 6px;
      transition: all 0.2s ease;
    }
    .tab-btn.active { background: rgba(56, 189, 248, 0.15); color: var(--accent); }
    .glass-card {
      background: var(--card-bg);
      border: 1px solid var(--card-border);
      border-radius: 18px;
      width: 100%;
      max-width: 480px;
      display: none;
      overflow: hidden;
    }
    #viewBrain { height: 75vh; }
    #viewBrain.active-view { display: flex; flex-direction: column; }
    #viewMusic.active-view { display: block; }
    .chat-header {
      padding: 12px 16px;
      border-bottom: 1px solid var(--card-border);
      display: flex;
      justify-content: space-between;
      align-items: center;
      font-size: 13px;
      font-weight: 700;
      color: var(--text-muted);
    }
    .chat-reset-btn { color: #64748b; font-size: 12px; cursor: pointer; text-decoration: underline; }
    .chat-stream { flex: 1; overflow-y: auto; padding: 14px; display: flex; flex-direction: column; gap: 14px; scroll-behavior: smooth; }
    .msg { max-width: 88%; padding: 10px 14px; border-radius: 14px; font-size: 14px; line-height: 1.55; word-break: break-word; }
    .msg-user { align-self: flex-end; background: linear-gradient(135deg, #2563eb, #1d4ed8); color: #fff; border-bottom-right-radius: 4px; }
    .msg-bot { align-self: flex-start; background: rgba(15, 23, 42, 0.85); border: 1px solid var(--card-border); color: #e2e8f0; border-bottom-left-radius: 4px; width: 100%; max-width: 95%; }
    .msg-bot strong { color: #fff; }
    .msg-bot code { background: rgba(0, 0, 0, 0.5); color: var(--accent); padding: 2px 6px; border-radius: 4px; font-family: monospace; font-size: 13px; }
    .msg-bot pre { background: rgba(0, 0, 0, 0.6); padding: 10px; border-radius: 8px; overflow-x: auto; margin: 8px 0; }
    .msg-bot pre code { background: transparent; padding: 0; }
    .thought-details { margin-bottom: 8px; background: rgba(0, 0, 0, 0.35); border: 1px solid rgba(56, 189, 248, 0.2); border-radius: 8px; overflow: hidden; font-size: 12px; }
    .thought-summary { padding: 6px 10px; cursor: pointer; color: var(--accent); font-weight: 600; user-select: none; }
    .thought-content { padding: 8px 10px; color: #94a3b8; border-top: 1px solid rgba(255, 255, 255, 0.05); white-space: pre-wrap; }
    .chat-input-bar { padding: 10px; border-top: 1px solid var(--card-border); background: rgba(11, 15, 25, 0.95); display: flex; gap: 8px; align-items: center; }
    .chat-input { flex: 1; background: rgba(18, 24, 38, 0.8); border: 1px solid rgba(255, 255, 255, 0.12); color: var(--text); padding: 10px 14px; border-radius: 12px; font-size: 14px; outline: none; }
    .chat-input:focus { border-color: var(--accent); }
    .send-btn { background: #2563eb; border: none; color: #fff; padding: 10px 16px; border-radius: 12px; font-size: 14px; font-weight: 700; cursor: pointer; }
    .send-btn:disabled { opacity: 0.5; }
    
    /* Settings Modal */
    .modal-overlay {
      position: fixed;
      top: 0; left: 0; right: 0; bottom: 0;
      background: rgba(0, 0, 0, 0.7);
      backdrop-filter: blur(8px);
      display: none;
      align-items: center;
      justify-content: center;
      z-index: 100;
      padding: 16px;
    }
    .modal-card {
      background: #111827;
      border: 1px solid var(--card-border);
      border-radius: 18px;
      padding: 20px;
      width: 100%;
      max-width: 360px;
    }
    .modal-title { font-size: 16px; font-weight: 700; margin-bottom: 14px; color: #fff; display: flex; justify-content: space-between; }
    .modal-close { cursor: pointer; color: var(--text-muted); font-size: 18px; }
    .modal-btn {
      width: 100%;
      background: #2563eb;
      color: #fff;
      border: none;
      padding: 10px;
      border-radius: 10px;
      font-weight: 600;
      margin-top: 10px;
      cursor: pointer;
    }
    .modal-input {
      width: 100%;
      background: rgba(0, 0, 0, 0.4);
      border: 1px solid rgba(255, 255, 255, 0.1);
      color: #fff;
      padding: 10px;
      border-radius: 8px;
      margin-bottom: 12px;
      outline: none;
    }

    /* Radar UI */
    .radar-wrapper { display: flex; flex-direction: column; align-items: center; padding: 24px 16px 20px; }
    .pulse-container { position: relative; width: 140px; height: 140px; display: flex; align-items: center; justify-content: center; margin-bottom: 20px; }
    .radar-btn { position: relative; z-index: 2; width: 108px; height: 108px; border-radius: 50%; background: linear-gradient(145deg, #0ea5e9, #2563eb); box-shadow: 0 0 30px var(--accent-glow); display: flex; align-items: center; justify-content: center; cursor: pointer; border: none; color: #fff; font-size: 40px; transition: transform 0.1s ease-out; }
    .pulse-ring { position: absolute; width: 100%; height: 100%; border-radius: 50%; border: 2px solid var(--accent); opacity: 0; pointer-events: none; }
    .is-listening .pulse-ring { animation: ripple 1.6s cubic-bezier(0.2, 0.8, 0.2, 1) infinite; }
    @keyframes ripple { 0% { transform: scale(0.7); opacity: 0.85; } 100% { transform: scale(1.6); opacity: 0; } }
    .radar-status { font-size: 15px; font-weight: 700; color: var(--text-muted); letter-spacing: 0.3px; text-align: center; min-height: 24px; }
    .track-result-card { background: rgba(30, 41, 59, 0.6); border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 16px; padding: 14px; margin-top: 18px; display: flex; flex-direction: column; gap: 12px; width: 100%; }
    .track-main { display: flex; align-items: center; gap: 14px; }
    .track-artwork { width: 62px; height: 62px; border-radius: 10px; object-fit: cover; flex-shrink: 0; background: #1e293b; }
    .track-meta { flex: 1; overflow: hidden; }
    .track-name { font-size: 15px; font-weight: 700; color: #fff; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
    .track-artist { font-size: 13px; color: var(--text-muted); margin-top: 2px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
    .store-badges { display: flex; gap: 8px; margin-top: 8px; }
    .store-badge { font-size: 11px; font-weight: 600; padding: 4px 10px; border-radius: 6px; text-decoration: none; color: #fff; background: #0284c7; }
    .lyrics-drawer { background: rgba(15, 23, 42, 0.6); border: 1px solid rgba(255, 255, 255, 0.06); border-radius: 10px; overflow: hidden; }
    .lyrics-summary { font-size: 12px; font-weight: 700; color: var(--accent); padding: 8px 12px; cursor: pointer; user-select: none; }
    .lyrics-body { font-size: 12.5px; line-height: 1.6; color: #cbd5e1; padding: 10px 12px; max-height: 220px; overflow-y: auto; white-space: pre-wrap; border-top: 1px solid rgba(255, 255, 255, 0.05); }
    .history-section { width: 100%; margin-top: 20px; padding-top: 16px; border-top: 1px solid var(--card-border); }
    .history-header { font-size: 12px; font-weight: 700; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.6px; display: flex; justify-content: space-between; margin-bottom: 8px; }
  </style>
</head>
<body>

  <div class="top-nav">
    <div class="brand">
      <span class="brand-icon">⚡</span>
      <span class="brand-title">HELLO Gelo</span>
    </div>
    <div class="user-tag">
      <div class="user-badge" onclick="openSettings()">👤 {{ display_name }} ⚙️</div>
      <span class="logout-btn" onclick="window.location.href='/logout'">Logout</span>
    </div>
  </div>

  <div class="tab-bar">
    <button class="tab-btn active" id="tabBrain" onclick="switchView('brain')">💬 Ask Gelo</button>
    <button class="tab-btn" id="tabMusic" onclick="switchView('music')">🎵 Music Search</button>
  </div>

  <div class="glass-card active-view" id="viewBrain">
    <div class="chat-header">
      <span>AI Conversation</span>
      <span class="chat-reset-btn" onclick="resetChat()">New Topic</span>
    </div>
    <div class="chat-stream" id="chatStream">
      <div class="msg msg-bot">⚡ Hi {{ display_name }}! What would you like to explore or learn today?</div>
    </div>
    <div class="chat-input-bar">
      <input type="text" class="chat-input" id="chatInput" placeholder="Reply or ask a question..." onkeydown="handleKey(event)">
      <button class="send-btn" id="sendBtn" onclick="sendChat()">Send</button>
    </div>
  </div>

  <div class="glass-card" id="viewMusic">
    <div class="radar-wrapper">
      <div class="pulse-container" id="pulseContainer">
        <div class="pulse-ring"></div>
        <div class="pulse-ring" style="animation-delay: 0.5s;"></div>
        <button class="radar-btn" id="radarBtn" onclick="startShazam()">⚡</button>
      </div>
      <div class="radar-status" id="radarStatus">Tap to Search</div>
      <div id="resultSlot" style="width: 100%;"></div>
      <div class="history-section">
        <div class="history-header">
          <span>Recent Discoveries</span>
          <span style="cursor: pointer; text-decoration: underline;" onclick="clearHistory()">Clear</span>
        </div>
        <div id="historyList"></div>
      </div>
    </div>
  </div>

  <!-- Settings / Profile Modal -->
  <div class="modal-overlay" id="settingsModal">
    <div class="modal-card">
      <div class="modal-title">
        <span>Profile & Settings</span>
        <span class="modal-close" onclick="closeSettings()">&times;</span>
      </div>
      <label style="font-size: 12px; color: var(--text-muted); display: block; margin-bottom: 4px;">Display Name</label>
      <input type="text" class="modal-input" id="newDisplayName" value="{{ display_name }}">
      <button class="modal-btn" onclick="updateDisplayName()">Save Display Name</button>
    </div>
  </div>

  <script>
    let chatHistory = [];
    let audioCtx, analyser, sourceNode, animFrame;

    document.addEventListener("DOMContentLoaded", renderHistory);

    function switchView(tab) {
      document.getElementById('viewBrain').classList.toggle('active-view', tab === 'brain');
      document.getElementById('viewMusic').classList.toggle('active-view', tab === 'music');
      document.getElementById('tabBrain').classList.toggle('active', tab === 'brain');
      document.getElementById('tabMusic').classList.toggle('active', tab === 'music');
    }

    function openSettings() { document.getElementById('settingsModal').style.display = 'flex'; }
    function closeSettings() { document.getElementById('settingsModal').style.display = 'none'; }

    async function updateDisplayName() {
      const name = document.getElementById('newDisplayName').value.trim();
      if (!name) return;
      try {
        const res = await fetch('/api/update-profile', {
          method: 'POST',
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify({ display_name: name })
        });
        if (res.ok) {
          window.location.reload();
        } else {
          alert('Failed to update name.');
        }
      } catch (e) {
        alert(e.message);
      }
    }

    function renderBasicMarkdown(text) {
      let escaped = text.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
      escaped = escaped.replace(/```([\\s\\S]*?)```/g, '<pre><code>$1</code></pre>');
      escaped = escaped.replace(/`([^`]+)`/g, '<code>$1</code>');
      escaped = escaped.replace(/\\*\\*([^\\*]+)\\*\\*/g, '<strong>$1</strong>');
      escaped = escaped.replace(/^### (.*$)/gim, '<h3 style="color:#38bdf8; margin:6px 0;">$1</h3>');
      escaped = escaped.replace(/^## (.*$)/gim, '<h2 style="color:#38bdf8; margin:8px 0;">$1</h2>');
      escaped = escaped.replace(/^# (.*$)/gim, '<h1 style="color:#38bdf8; margin:10px 0;">$1</h1>');
      escaped = escaped.replace(/^\\* (.*$)/gim, '• $1');
      return escaped.replace(/\\n/g, '<br>');
    }

    function handleKey(e) { if (e.key === 'Enter') sendChat(); }

    function resetChat() {
      chatHistory = [];
      document.getElementById('chatStream').innerHTML = '<div class="msg msg-bot">⚡ New topic started. What would you like to explore?</div>';
    }

    async function sendChat() {
      const input = document.getElementById('chatInput');
      const text = input.value.trim();
      const sendBtn = document.getElementById('sendBtn');
      const stream = document.getElementById('chatStream');
      if (!text) return;

      const userBubble = document.createElement('div');
      userBubble.className = 'msg msg-user';
      userBubble.innerText = text;
      stream.appendChild(userBubble);

      chatHistory.push({ role: "user", parts: [{ text: text }] });
      input.value = "";
      sendBtn.disabled = true;

      const botBubble = document.createElement('div');
      botBubble.className = 'msg msg-bot';
      botBubble.innerHTML = "<em>⚡ Deep thinking...</em>";
      stream.appendChild(botBubble);
      stream.scrollTop = stream.scrollHeight;

      try {
        const response = await fetch('/ask', {
          method: 'POST',
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify({ history: chatHistory })
        });
        const data = await response.json();
        if (data.answer) {
          let innerHtml = "";
          if (data.thinking) {
            innerHtml += `
              <details class="thought-details">
                <summary class="thought-summary">🧠 Deep Thought Process</summary>
                <div class="thought-content">${renderBasicMarkdown(data.thinking)}</div>
              </details>
            `;
          }
          innerHtml += renderBasicMarkdown(data.answer);
          botBubble.innerHTML = innerHtml;
          chatHistory.push({ role: "model", parts: [{ text: data.answer }] });
        } else {
          botBubble.innerHTML = `<span style="color:#f87171;">${data.error || "No response."}</span>`;
        }
      } catch (err) {
        botBubble.innerHTML = `<span style="color:#f87171;">Connection error: ${err.message}</span>`;
      } finally {
        sendBtn.disabled = false;
        stream.scrollTop = stream.scrollHeight;
      }
    }

    function getCover(track) {
      if (track.spotify?.album?.images?.[0]) return track.spotify.album.images[0].url;
      if (track.apple_music?.artwork) return track.apple_music.artwork.url.replace('{w}x{h}', '300x300');
      return 'https://via.placeholder.com/150/1e293b/38bdf8?text=Song';
    }

    function renderShazamResult(track) {
      const slot = document.getElementById('resultSlot');
      const coverUrl = getCover(track);
      const spotify = track.spotify?.external_urls?.spotify;
      const apple = track.apple_music?.url;
      const lyrics = track.lyrics?.lyrics;

      slot.innerHTML = `
        <div class="track-result-card">
          <div class="track-main">
            <img class="track-artwork" src="${coverUrl}" alt="Artwork">
            <div class="track-meta">
              <div class="track-name">${track.title}</div>
              <div class="track-artist">${track.artist}</div>
              <div class="store-badges">
                ${spotify ? `<a class="store-badge" href="${spotify}" target="_blank">Spotify</a>` : ''}
                ${apple ? `<a class="store-badge" href="${apple}" target="_blank">Apple Music</a>` : ''}
              </div>
            </div>
          </div>
          ${lyrics ? `
            <details class="lyrics-drawer">
              <summary class="lyrics-summary">📜 Lyrics Preview</summary>
              <div class="lyrics-body">${lyrics}</div>
            </details>
          ` : `
            <details class="lyrics-drawer">
              <summary class="lyrics-summary">📜 Search Lyrics Online</summary>
              <div class="lyrics-body" style="color: #94a3b8; font-style: italic;">
                Lyrics not directly in database. Check Spotify or Apple Music for full licensed text.
              </div>
            </details>
          `}
        </div>
      `;
      saveHistory(track);
    }

    function saveHistory(track) {
      const history = JSON.parse(localStorage.getItem('gelo_history') || '[]');
      const filtered = history.filter(i => i.title !== track.title);
      filtered.unshift({
        title: track.title,
        artist: track.artist,
        cover: getCover(track),
        spotify: track.spotify?.external_urls?.spotify,
        apple: track.apple_music?.url
      });
      localStorage.setItem('gelo_history', JSON.stringify(filtered.slice(0, 5)));
      renderHistory();
    }

    function renderHistory() {
      const list = document.getElementById('historyList');
      const history = JSON.parse(localStorage.getItem('gelo_history') || '[]');
      if (!history.length) {
        list.innerHTML = '<div style="font-size: 12px; color: #475569; padding: 6px 0;">No discoveries yet.</div>';
        return;
      }
      list.innerHTML = history.map(item => `
        <div class="track-result-card" style="margin-top: 8px; padding: 10px;">
          <div class="track-main">
            <img class="track-artwork" style="width: 44px; height: 44px;" src="${item.cover}">
            <div class="track-meta">
              <div class="track-name" style="font-size: 13.5px;">${item.title}</div>
              <div class="track-artist" style="font-size: 12px;">${item.artist}</div>
              <div class="store-badges">
                ${item.spotify ? `<a class="store-badge" style="font-size: 10px; padding: 2px 7px;" href="${item.spotify}" target="_blank">Spotify</a>` : ''}
                ${item.apple ? `<a class="store-badge" style="font-size: 10px; padding: 2px 7px;" href="${item.apple}" target="_blank">Apple</a>` : ''}
              </div>
            </div>
          </div>
        </div>
      `).join('');
    }

    function clearHistory() {
      localStorage.removeItem('gelo_history');
      renderHistory();
    }

    function startVisualizer(stream) {
      audioCtx = new (window.AudioContext || window.webkitAudioContext)();
      analyser = audioCtx.createAnalyser();
      analyser.fftSize = 64;
      sourceNode = audioCtx.createMediaStreamSource(stream);
      sourceNode.connect(analyser);

      const bufferLength = analyser.frequencyBinCount;
      const dataArray = new Uint8Array(bufferLength);
      const btn = document.getElementById('radarBtn');

      function draw() {
        animFrame = requestAnimationFrame(draw);
        analyser.getByteFrequencyData(dataArray);
        let sum = 0;
        for (let i = 0; i < bufferLength; i++) sum += dataArray[i];
        btn.style.transform = `scale(${1 + ((sum / bufferLength) / 255) * 0.22})`;
      }
      draw();
    }

    function stopVisualizer() {
      if (animFrame) cancelAnimationFrame(animFrame);
      if (sourceNode) sourceNode.disconnect();
      if (audioCtx && audioCtx.state !== 'closed') audioCtx.close();
      const btn = document.getElementById('radarBtn');
      if (btn) btn.style.transform = 'scale(1)';
    }

    async function uploadAudio(blob) {
      const status = document.getElementById('radarStatus');
      const container = document.getElementById('pulseContainer');
      status.innerText = "Searching database & lyrics...";
      container.classList.remove('is-listening');
      stopVisualizer();

      const formData = new FormData();
      formData.append('file', blob, 'audio.webm');

      try {
        const res = await fetch('/identify', { method: 'POST', body: formData });
        const data = await res.json();
        if (data.result && data.result.title) {
          status.innerText = "Track Identified!";
          renderShazamResult(data.result);
        } else {
          status.innerText = "No match found. Try again closer.";
        }
      } catch (e) {
        status.innerText = "Identification failed: " + e.message;
      }
    }

    async function startShazam() {
      const status = document.getElementById('radarStatus');
      const container = document.getElementById('pulseContainer');
      document.getElementById('resultSlot').innerHTML = "";

      if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
        status.innerText = "Microphone not supported on this browser.";
        return;
      }

      try {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: { echoCancellation: true, noiseSuppression: true } });
        startVisualizer(stream);

        let mimeType = '';
        if (typeof MediaRecorder !== 'undefined') {
          if (MediaRecorder.isTypeSupported('audio/webm;codecs=opus')) mimeType = 'audio/webm;codecs=opus';
          else if (MediaRecorder.isTypeSupported('audio/webm')) mimeType = 'audio/webm';
          else if (MediaRecorder.isTypeSupported('audio/mp4')) mimeType = 'audio/mp4';
        }

        const options = mimeType ? { mimeType } : {};
        const mediaRecorder = new MediaRecorder(stream, options);
        const audioChunks = [];

        mediaRecorder.ondataavailable = e => { if (e.data && e.data.size > 0) audioChunks.push(e.data); };
        mediaRecorder.onstop = () => {
          const audioBlob = new Blob(audioChunks, { type: mimeType || 'audio/webm' });
          uploadAudio(audioBlob);
        };

        mediaRecorder.start(250);
        container.classList.add('is-listening');

        let secondsLeft = 7;
        status.innerText = `Listening... (${secondsLeft}s)`;
        const timer = setInterval(() => {
          secondsLeft--;
          if (secondsLeft > 0) {
            status.innerText = `Listening... (${secondsLeft}s)`;
          } else {
            clearInterval(timer);
            if (mediaRecorder.state !== 'inactive') mediaRecorder.stop();
            stream.getTracks().forEach(t => t.stop());
          }
        }, 1000);
      } catch (err) {
        container.classList.remove('is-listening');
        stopVisualizer();
        status.innerHTML = `<span style="color:#f87171;">Mic permission denied or unavailable.</span>`;
      }
    }
  </script>
</body>
</html>
"""

def clean_name(raw_val, custom_display=None):
    if custom_display and custom_display.strip():
        return custom_display.strip()
    if "@" in raw_val:
        return raw_val.split("@")[0]
    return raw_val

# --- AUTH ROUTES ---
@app.route("/login")
def login_page():
    if "user" in session:
        return redirect("/")
    resp = make_response(AUTH_TEMPLATE)
    resp.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    return resp

@app.route("/api/register", methods=["POST"])
def register():
    data = request.json or {}
    username = data.get("username", "").strip()
    password = data.get("password", "").strip()
    display_name = data.get("display_name", "").strip()

    if not username or not password:
        return jsonify({"error": "Username/Email and password required."}), 400
    if len(password) < 6:
        return jsonify({"error": "Password must be at least 6 characters."}), 400

    resolved_display = clean_name(username, display_name)

    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    try:
        c.execute("INSERT INTO users (username, display_name, password_hash) VALUES (?, ?, ?)", 
                  (username, resolved_display, generate_password_hash(password)))
        conn.commit()
        session["user"] = username
        session["display_name"] = resolved_display
        return jsonify({"status": "registered"})
    except sqlite3.IntegrityError:
        return jsonify({"error": "Account already exists."}), 409
    finally:
        conn.close()

@app.route("/api/login", methods=["POST"])
def login():
    data = request.json or {}
    username = data.get("username", "").strip()
    password = data.get("password", "").strip()

    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT password_hash, display_name FROM users WHERE username = ?", (username,))
    row = c.fetchone()
    conn.close()

    if row and check_password_hash(row[0], password):
        session["user"] = username
        session["display_name"] = row[1] if row[1] else clean_name(username)
        return jsonify({"status": "logged_in"})
    return jsonify({"error": "Invalid username or password."}), 401

@app.route("/api/update-profile", methods=["POST"])
def update_profile():
    if "user" not in session:
        return jsonify({"error": "Unauthorized"}), 401
    data = request.json or {}
    new_name = data.get("display_name", "").strip()
    if not new_name:
        return jsonify({"error": "Display name cannot be empty"}), 400

    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("UPDATE users SET display_name = ? WHERE username = ?", (new_name, session["user"]))
    conn.commit()
    conn.close()

    session["display_name"] = new_name
    return jsonify({"status": "updated"})

@app.route("/logout")
def logout():
    session.pop("user", None)
    session.pop("display_name", None)
    return redirect("/login")

# --- PROTECTED APP ROUTES ---
@app.route("/")
def index():
    if "user" not in session:
        return redirect("/login")
    display_name = session.get("display_name") or clean_name(session["user"])
    rendered = MAIN_TEMPLATE.replace("{{ display_name }}", display_name)
    resp = make_response(rendered)
    resp.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    return resp

@app.route("/ask", methods=["POST"])
def ask():
    if "user" not in session:
        return jsonify({"error": "Unauthorized"}), 401

    req_data = request.json or {}
    history = req_data.get("history", [])
    if not history:
        return jsonify({"error": "Empty message"}), 400
    if not GEMINI_API_KEY:
        return jsonify({"error": "GEMINI_API_KEY missing."}), 500

    now_utc = datetime.now(timezone.utc).strftime('%A, %B %d, %Y, %H:%M:%S UTC')
    display_name = session.get("display_name") or clean_name(session["user"])

    payload = {
        "system_instruction": {
            "parts": [{
                "text": (
                    f"You are Gelo, an elite conversational AI companion. The user's name is {display_name}. "
                    f"The current reference time is {now_utc}. Engage in natural conversation remembering past context. "
                    "Conduct your step-by-step reasoning process enclosed in <thought>...</thought> tags, "
                    "then deliver your clean final response outside the tags."
                )
            }]
        },
        "contents": history[-8:]
    }

    headers = {"Content-Type": "application/json", "x-goog-api-key": GEMINI_API_KEY}
    for model in ["gemini-3.8-flash", "gemini-3.6-flash"]:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
        try:
            res = requests.post(url, headers=headers, json=payload, timeout=20)
            data = res.json()
            if "candidates" in data and data["candidates"]:
                raw_text = data["candidates"][0]["content"]["parts"][0]["text"]
                thought_match = re.search(r'<thought>(.*?)</thought>', raw_text, re.DOTALL)
                if thought_match:
                    thinking = thought_match.group(1).strip()
                    answer = re.sub(r'<thought>.*?</thought>', '', raw_text, flags=re.DOTALL).strip()
                else:
                    thinking = "Synthesized context and prepared response."
                    answer = raw_text.strip()
                return jsonify({"thinking": thinking, "answer": answer})
        except Exception:
            continue

    return jsonify({"error": "Service busy. Please try again."}), 503

@app.route("/identify", methods=["POST"])
def identify():
    if "user" not in session:
        return jsonify({"error": "Unauthorized"}), 401
    if "file" not in request.files:
        return jsonify({"error": {"error_message": "Missing audio file"}}), 400

    file = request.files["file"]
    data = {"api_token": AUDD_API_KEY, "return": "apple_music,spotify,lyrics"}
    try:
        res = requests.post("https://api.audd.io/", data=data, files={"file": file.read()}, timeout=25)
        return jsonify(res.json())
    except Exception as e:
        return jsonify({"error": {"error_message": str(e)}}), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
