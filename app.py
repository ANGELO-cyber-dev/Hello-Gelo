import os
import re
import json
import base64
import sqlite3
from datetime import datetime, timezone
import requests
from flask import Flask, request, jsonify, make_response, session, redirect, Response, stream_with_context, render_template_string
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
    c.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            role TEXT NOT NULL,
            text TEXT NOT NULL,
            thinking TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    c.execute("PRAGMA table_info(users)")
    cols = [col[1] for col in c.fetchall()]
    if "display_name" not in cols:
        c.execute("ALTER TABLE users ADD COLUMN display_name TEXT")
    conn.commit()
    conn.close()

init_db()

AUTH_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0">
  <title>Gelo — Portal</title>
  <style>
    :root {
      --bg: #090a0f;
      --surface: #11131a;
      --surface-border: rgba(255, 255, 255, 0.08);
      --accent: #38bdf8;
      --accent-muted: rgba(56, 189, 248, 0.15);
      --text: #f8fafc;
      --text-muted: #8492a6;
    }
    * { box-sizing: border-box; margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, "SF Pro Display", "Segoe UI", Roboto, sans-serif; -webkit-tap-highlight-color: transparent; }
    body {
      background-color: var(--bg);
      color: var(--text);
      min-height: 100vh;
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      padding: 24px 16px;
    }
    .brand {
      display: flex;
      align-items: center;
      gap: 10px;
      margin-bottom: 28px;
    }
    .brand-mark {
      width: 28px;
      height: 28px;
      border-radius: 6px;
      background: #1c2230;
      border: 1px solid rgba(56, 189, 248, 0.4);
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 15px;
      color: var(--accent);
    }
    .brand-title {
      font-size: 20px;
      font-weight: 700;
      letter-spacing: 1.5px;
      text-transform: uppercase;
      color: #fff;
    }
    .auth-card {
      background: var(--surface);
      border: 1px solid var(--surface-border);
      border-radius: 12px;
      padding: 28px 24px;
      width: 100%;
      max-width: 360px;
      box-shadow: 0 24px 48px rgba(0, 0, 0, 0.5);
    }
    .auth-nav {
      display: grid;
      grid-template-columns: 1fr 1fr;
      border-bottom: 1px solid var(--surface-border);
      margin-bottom: 22px;
    }
    .auth-tab {
      padding: 10px 0;
      text-align: center;
      font-size: 13px;
      font-weight: 600;
      color: var(--text-muted);
      cursor: pointer;
      border-bottom: 2px solid transparent;
      background: none;
      border-top: none; border-left: none; border-right: none;
    }
    .auth-tab.active {
      color: #fff;
      border-bottom-color: var(--accent);
    }
    .form-group { margin-bottom: 16px; }
    .form-label {
      display: block;
      font-size: 11px;
      font-weight: 600;
      text-transform: uppercase;
      letter-spacing: 0.8px;
      color: var(--text-muted);
      margin-bottom: 6px;
    }
    .form-input {
      width: 100%;
      background: #0b0d13;
      border: 1px solid var(--surface-border);
      color: #fff;
      padding: 11px 13px;
      border-radius: 8px;
      font-size: 13.5px;
      outline: none;
      transition: border-color 0.15s ease;
    }
    .form-input:focus { border-color: var(--accent); }
    .auth-btn {
      width: 100%;
      background: #fff;
      color: #090a0f;
      border: none;
      padding: 12px;
      border-radius: 8px;
      font-size: 13.5px;
      font-weight: 700;
      letter-spacing: 0.3px;
      cursor: pointer;
      margin-top: 6px;
    }
    .auth-btn:hover { background: #e2e8f0; }
    .error-box {
      font-size: 12.5px;
      color: #f87171;
      background: rgba(248, 113, 113, 0.08);
      border: 1px solid rgba(248, 113, 113, 0.2);
      padding: 8px 12px;
      border-radius: 6px;
      margin-bottom: 14px;
      display: none;
    }
  </style>
</head>
<body>
  <div class="brand">
    <div class="brand-mark">⚡</div>
    <div class="brand-title">HELLO Gelo</div>
  </div>

  <div class="auth-card">
    <div class="auth-nav">
      <button class="auth-tab active" id="tabLogin" onclick="setMode('login')">Sign In</button>
      <button class="auth-tab" id="tabRegister" onclick="setMode('register')">Register</button>
    </div>

    <div id="authError" class="error-box"></div>

    <form onsubmit="handleAuth(event)">
      <div class="form-group" id="displayNameGroup" style="display: none;">
        <label class="form-label">Display Name</label>
        <input type="text" class="form-input" id="authDisplayName" placeholder="Preferred Name">
      </div>
      <div class="form-group">
        <label class="form-label">Username / Account</label>
        <input type="text" class="form-input" id="authUsername" required autocomplete="username">
      </div>
      <div class="form-group">
        <label class="form-label">Password</label>
        <input type="password" class="form-input" id="authPassword" required autocomplete="current-password">
      </div>
      <button type="submit" class="auth-btn" id="submitBtn">Sign In</button>
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

MAIN_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
  <title>HELLO Gelo</title>
  <style>
    :root {
      --bg: #090a0f;
      --surface: #101319;
      --surface-elevated: #161a22;
      --surface-border: rgba(255, 255, 255, 0.08);
      --accent: #38bdf8;
      --text: #f8fafc;
      --text-muted: #818cf8;
      --text-dim: #738096;
    }
    * { box-sizing: border-box; margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, "SF Pro Text", "Segoe UI", Roboto, sans-serif; -webkit-tap-highlight-color: transparent; }
    body {
      background-color: var(--bg);
      color: var(--text);
      min-height: 100vh;
      display: flex;
      flex-direction: column;
      align-items: center;
      padding: 10px 8px 12px;
    }

    .app-header {
      width: 100%;
      max-width: 480px;
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 6px 4px 10px;
      border-bottom: 1px solid var(--surface-border);
      margin-bottom: 10px;
    }
    .brand-section {
      display: flex;
      align-items: center;
      gap: 8px;
    }
    .brand-badge {
      width: 24px;
      height: 24px;
      background: #171d29;
      border: 1px solid rgba(56, 189, 248, 0.35);
      border-radius: 5px;
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 13px;
      color: var(--accent);
    }
    .brand-title {
      font-size: 14.5px;
      font-weight: 700;
      letter-spacing: 1px;
      text-transform: uppercase;
      color: #fff;
    }
    .account-meta {
      display: flex;
      align-items: center;
      gap: 10px;
    }
    .user-pill {
      background: #151a24;
      border: 1px solid var(--surface-border);
      color: #cbd5e1;
      font-size: 12px;
      font-weight: 600;
      padding: 4px 10px;
      border-radius: 6px;
      cursor: pointer;
    }
    .logout-btn {
      color: #ef4444;
      font-size: 12px;
      text-decoration: none;
      cursor: pointer;
    }

    .tab-segment {
      width: 100%;
      max-width: 480px;
      background: #0f1218;
      border: 1px solid var(--surface-border);
      border-radius: 8px;
      padding: 3px;
      display: flex;
      gap: 4px;
      margin-bottom: 10px;
    }
    .tab-btn {
      flex: 1;
      border: none;
      background: transparent;
      color: var(--text-dim);
      padding: 8px 12px;
      font-size: 12.5px;
      font-weight: 600;
      border-radius: 6px;
      cursor: pointer;
      letter-spacing: 0.3px;
      transition: all 0.15s ease;
    }
    .tab-btn.active {
      background: #1a202c;
      color: #fff;
      box-shadow: 0 2px 6px rgba(0,0,0,0.4);
    }

    .main-workspace {
      width: 100%;
      max-width: 480px;
      background: var(--surface);
      border: 1px solid var(--surface-border);
      border-radius: 12px;
      overflow: hidden;
      display: none;
    }
    #viewBrain.active-view {
      display: flex;
      flex-direction: column;
      height: calc(100vh - 128px);
    }
    #viewMusic.active-view {
      display: block;
    }

    .workspace-subbar {
      padding: 8px 12px;
      border-bottom: 1px solid var(--surface-border);
      display: flex;
      justify-content: space-between;
      align-items: center;
      background: #0d0f14;
    }
    .status-indicator {
      font-size: 11px;
      font-weight: 600;
      text-transform: uppercase;
      letter-spacing: 0.8px;
      color: #10b981;
      display: flex;
      align-items: center;
      gap: 5px;
    }
    .status-dot {
      width: 6px;
      height: 6px;
      border-radius: 50%;
      background: #10b981;
    }
    .action-link {
      font-size: 11.5px;
      color: var(--text-dim);
      cursor: pointer;
      text-decoration: underline;
    }

    .action-chips-container {
      display: flex;
      gap: 6px;
      padding: 8px 12px;
      background: #0c0e13;
      border-bottom: 1px solid var(--surface-border);
      overflow-x: auto;
      scrollbar-width: none;
    }
    .action-chips-container::-webkit-scrollbar { display: none; }
    .action-chip {
      background: #141822;
      border: 1px solid rgba(255, 255, 255, 0.06);
      color: #cbd5e1;
      padding: 4px 10px;
      border-radius: 6px;
      font-size: 11.5px;
      white-space: nowrap;
      cursor: pointer;
    }
    .action-chip:active { background: #1c2230; }

    .stream-feed {
      flex: 1;
      overflow-y: auto;
      padding: 14px 12px;
      display: flex;
      flex-direction: column;
      gap: 12px;
      scroll-behavior: smooth;
    }
    .feed-bubble {
      max-width: 90%;
      padding: 10px 14px;
      border-radius: 10px;
      font-size: 13.5px;
      line-height: 1.6;
      word-break: break-word;
    }
    .feed-user {
      align-self: flex-end;
      background: #2563eb;
      color: #fff;
      border-bottom-right-radius: 2px;
    }
    .feed-bot {
      align-self: flex-start;
      background: var(--surface-elevated);
      border: 1px solid var(--surface-border);
      color: #e2e8f0;
      border-bottom-left-radius: 2px;
      width: 100%;
      max-width: 96%;
    }
    .feed-bot strong { color: #fff; }
    .feed-bot code {
      background: #0c0e14;
      color: var(--accent);
      padding: 2px 5px;
      border-radius: 4px;
      font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
      font-size: 12px;
    }
    .feed-bot pre {
      background: #090b0f;
      border: 1px solid var(--surface-border);
      padding: 10px;
      border-radius: 6px;
      overflow-x: auto;
      margin: 8px 0;
    }
    .feed-bot pre code { background: transparent; padding: 0; }

    .reasoning-panel {
      margin-bottom: 8px;
      background: #0b0d13;
      border: 1px solid rgba(56, 189, 248, 0.2);
      border-radius: 6px;
      overflow: hidden;
      font-size: 11.5px;
    }
    .reasoning-trigger {
      padding: 6px 10px;
      cursor: pointer;
      color: var(--accent);
      font-weight: 600;
      user-select: none;
      letter-spacing: 0.3px;
    }
    .reasoning-body {
      padding: 8px 10px;
      color: #94a3b8;
      border-top: 1px solid rgba(255, 255, 255, 0.05);
      white-space: pre-wrap;
      font-family: ui-monospace, Menlo, monospace;
      line-height: 1.5;
    }

    .input-dock {
      padding: 8px;
      background: #0c0e14;
      border-top: 1px solid var(--surface-border);
      display: flex;
      gap: 6px;
      align-items: center;
    }
    .dock-field {
      flex: 1;
      background: #141822;
      border: 1px solid var(--surface-border);
      color: #fff;
      padding: 9px 12px;
      border-radius: 8px;
      font-size: 13.5px;
      outline: none;
    }
    .dock-field:focus { border-color: rgba(255, 255, 255, 0.3); }
    .dock-icon-btn {
      width: 36px;
      height: 36px;
      background: #141822;
      border: 1px solid var(--surface-border);
      border-radius: 8px;
      color: #cbd5e1;
      display: flex;
      align-items: center;
      justify-content: center;
      cursor: pointer;
      font-size: 15px;
    }
    .dock-icon-btn.recording { background: #dc2626; border-color: #ef4444; color: #fff; }
    .dock-send-btn {
      height: 36px;
      padding: 0 14px;
      background: #fff;
      color: #0b0d12;
      border: none;
      border-radius: 8px;
      font-size: 12.5px;
      font-weight: 700;
      letter-spacing: 0.3px;
      cursor: pointer;
    }
    .dock-send-btn:disabled { opacity: 0.4; }

    .image-preview-bar {
      padding: 6px 12px;
      background: #11141c;
      border-top: 1px solid var(--surface-border);
      display: none;
      align-items: center;
      gap: 8px;
    }
    .image-thumb {
      width: 34px;
      height: 34px;
      border-radius: 5px;
      object-fit: cover;
      border: 1px solid var(--surface-border);
    }

    .radar-deck {
      display: flex;
      flex-direction: column;
      align-items: center;
      padding: 32px 16px 20px;
    }
    .radar-core-container {
      position: relative;
      width: 130px;
      height: 130px;
      display: flex;
      align-items: center;
      justify-content: center;
      margin-bottom: 20px;
    }
    .radar-trigger-btn {
      position: relative;
      z-index: 2;
      width: 96px;
      height: 96px;
      border-radius: 50%;
      background: #141822;
      border: 1px solid rgba(56, 189, 248, 0.4);
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 34px;
      color: var(--accent);
      cursor: pointer;
      box-shadow: 0 10px 30px rgba(0, 0, 0, 0.6);
      transition: transform 0.1s ease;
    }
    .radar-wave {
      position: absolute;
      width: 100%;
      height: 100%;
      border-radius: 50%;
      border: 1px solid var(--accent);
      opacity: 0;
      pointer-events: none;
    }
    .is-listening .radar-wave {
      animation: wave-expand 1.6s cubic-bezier(0.2, 0.8, 0.2, 1) infinite;
    }
    @keyframes wave-expand {
      0% { transform: scale(0.7); opacity: 0.8; }
      100% { transform: scale(1.5); opacity: 0; }
    }
    .radar-caption {
      font-size: 13px;
      font-weight: 600;
      letter-spacing: 0.5px;
      color: var(--text-dim);
      text-transform: uppercase;
      min-height: 22px;
    }

    .song-result-card {
      background: #131720;
      border: 1px solid var(--surface-border);
      border-radius: 10px;
      padding: 12px;
      margin-top: 20px;
      display: flex;
      flex-direction: column;
      gap: 10px;
      width: 100%;
    }
    .song-primary { display: flex; align-items: center; gap: 12px; }
    .song-art { width: 56px; height: 56px; border-radius: 6px; object-fit: cover; background: #0c0e14; }
    .song-title { font-size: 14.5px; font-weight: 700; color: #fff; }
    .song-artist { font-size: 12.5px; color: var(--text-dim); margin-top: 2px; }
    .song-links { display: flex; gap: 6px; margin-top: 6px; }
    .song-link-pill {
      font-size: 11px;
      font-weight: 600;
      padding: 3px 8px;
      border-radius: 4px;
      text-decoration: none;
      color: #cbd5e1;
      background: #1d2433;
      border: 1px solid var(--surface-border);
    }

    .classic-modal {
      position: fixed;
      top: 0; left: 0; right: 0; bottom: 0;
      background: rgba(0, 0, 0, 0.75);
      backdrop-filter: blur(6px);
      display: none;
      align-items: center;
      justify-content: center;
      z-index: 100;
      padding: 16px;
    }
    .modal-box {
      background: #11141b;
      border: 1px solid var(--surface-border);
      border-radius: 10px;
      padding: 22px 18px;
      width: 100%;
      max-width: 340px;
    }
    .modal-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 14px;
      font-size: 14px;
      font-weight: 700;
      color: #fff;
    }
    .modal-close-icon { cursor: pointer; color: var(--text-dim); font-size: 18px; }
    .modal-btn-confirm {
      width: 100%;
      background: #fff;
      color: #0b0d13;
      border: none;
      padding: 10px;
      border-radius: 6px;
      font-size: 13px;
      font-weight: 700;
      cursor: pointer;
      margin-top: 10px;
    }
    .modal-field {
      width: 100%;
      background: #0c0e14;
      border: 1px solid var(--surface-border);
      color: #fff;
      padding: 10px;
      border-radius: 6px;
      font-size: 13px;
      margin-bottom: 12px;
      outline: none;
    }
    .modal-toggle-row {
      display: flex;
      justify-content: space-between;
      align-items: center;
      font-size: 12.5px;
      color: #cbd5e1;
      margin: 10px 0;
    }
  </style>
</head>
<body>

  <header class="app-header">
    <div class="brand-section">
      <div class="brand-badge">⚡</div>
      <div class="brand-title">HELLO Gelo</div>
    </div>
    <div class="account-meta">
      <div class="user-pill" onclick="openSettings()">👤 {{ display_name }}</div>
      <span class="logout-btn" onclick="window.location.href='/logout'">Sign Out</span>
    </div>
  </header>

  <nav class="tab-segment">
    <button class="tab-btn active" id="tabBrain" onclick="switchView('brain')">Ask Gelo</button>
    <button class="tab-btn" id="tabMusic" onclick="switchView('music')">Music Radar</button>
  </nav>

  <main class="main-workspace active-view" id="viewBrain">
    <div class="workspace-subbar">
      <div class="status-indicator">
        <span class="status-dot"></span>
        <span>Online</span>
      </div>
      <span class="action-link" onclick="resetChat()">Clear Session</span>
    </div>

    <div class="action-chips-container">
      <span class="action-chip" onclick="quickPrompt('Teach me Python step-by-step from scratch')">Python Mastery</span>
      <span class="action-chip" onclick="quickPrompt('Synthesize the key points of quantum mechanics simply')">Quantum Mechanics</span>
      <span class="action-chip" onclick="quickPrompt('Draft a concise, executive-level project update email')">Executive Email</span>
      <span class="action-chip" onclick="quickPrompt('Explain modal chord progressions in music theory')">Music Theory</span>
    </div>

    <div class="stream-feed" id="chatStream">
      {% if history %}
        {% for msg in history %}
          <div class="feed-bubble {% if msg.role == 'user' %}feed-user{% else %}feed-bot{% endif %}">
            {% if msg.thinking %}
              <details class="reasoning-panel">
                <summary class="reasoning-trigger">🧠 Thought Chain</summary>
                <div class="reasoning-body">{{ msg.thinking }}</div>
              </details>
            {% endif %}
            <div class="bubble-content">{{ msg.text }}</div>
          </div>
        {% endfor %}
      {% else %}
        <div class="feed-bubble feed-bot">
          Good day, {{ display_name }}. What inquiry or project are we tackling today?
        </div>
      {% endif %}
    </div>

    <div class="image-preview-bar" id="previewTray">
      <img id="imageThumb" class="image-thumb" src="" alt="preview">
      <span style="font-size: 11.5px; color: #94a3b8; flex: 1;">Image attached</span>
      <span style="color: #ef4444; font-size: 16px; cursor: pointer;" onclick="clearAttachedImage()">&times;</span>
    </div>

    <div class="input-dock">
      <button class="dock-icon-btn" onclick="document.getElementById('imgInput').click()" title="Attach Image">📎</button>
      <input type="file" id="imgInput" accept="image/*" style="display: none;" onchange="handleImagePicked(this.files[0])">
      <button class="dock-icon-btn" id="micBtn" onclick="toggleVoice()" title="Dictate">🎙️</button>
      <input type="text" class="dock-field" id="chatInput" placeholder="Send an inquiry..." onkeydown="handleKey(event)">
      <button class="dock-send-btn" id="sendBtn" onclick="sendChat()">Send</button>
    </div>
  </main>

  <section class="main-workspace" id="viewMusic">
    <div class="radar-deck">
      <div class="radar-core-container" id="pulseContainer">
        <div class="radar-wave"></div>
        <div class="radar-wave" style="animation-delay: 0.5s;"></div>
        <button class="radar-trigger-btn" id="radarBtn" onclick="startShazam()">⚡</button>
      </div>
      <div class="radar-caption" id="radarStatus">Tap to Scan</div>
      <div id="resultSlot" style="width: 100%;"></div>

      <div style="width: 100%; margin-top: 24px; padding-top: 14px; border-top: 1px solid var(--surface-border);">
        <div style="font-size: 11px; font-weight: 700; color: var(--text-dim); text-transform: uppercase; letter-spacing: 0.6px; display: flex; justify-content: space-between; margin-bottom: 8px;">
          <span>Recent Discoveries</span>
          <span style="cursor: pointer; text-decoration: underline;" onclick="clearHistory()">Clear</span>
        </div>
        <div id="historyList"></div>
      </div>
    </div>
  </section>

  <div class="classic-modal" id="settingsModal">
    <div class="modal-box">
      <div class="modal-header">
        <span>Account Preferences</span>
        <span class="modal-close-icon" onclick="closeSettings()">&times;</span>
      </div>
      <label style="font-size: 11px; text-transform: uppercase; letter-spacing: 0.6px; color: var(--text-dim); display: block; margin-bottom: 4px;">Display Name</label>
      <input type="text" class="modal-field" id="newDisplayName" value="{{ display_name }}">
      <div class="modal-toggle-row">
        <span>Audible Speech (TTS)</span>
        <input type="checkbox" id="ttsToggle" onchange="localStorage.setItem('gelo_tts', this.checked)">
      </div>
      <button class="modal-btn-confirm" onclick="updateDisplayName()">Save</button>
    </div>
  </div>

  <script>
    let attachedImageBase64 = null;
    let recognition = null;
    let isRecording = false;
    let audioCtx, analyser, sourceNode, animFrame;

    document.addEventListener("DOMContentLoaded", () => {
      renderHistory();
      formatExistingHistory();
      document.getElementById('ttsToggle').checked = localStorage.getItem('gelo_tts') === 'true';
      const stream = document.getElementById('chatStream');
      stream.scrollTop = stream.scrollHeight;
    });

    function formatExistingHistory() {
      document.querySelectorAll('.feed-bot .bubble-content').forEach(el => {
        el.innerHTML = renderBasicMarkdown(el.innerText);
      });
    }

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
        if (res.ok) window.location.reload();
      } catch (e) {
        alert(e.message);
      }
    }

    function renderBasicMarkdown(text) {
      let escaped = text.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
      escaped = escaped.replace(/```([\\s\\S]*?)```/g, '<pre><code>$1</code></pre>');
      escaped = escaped.replace(/`([^`]+)`/g, '<code>$1</code>');
      escaped = escaped.replace(/\\*\\*([^\\*]+)\\*\\*/g, '<strong>$1</strong>');
      escaped = escaped.replace(/^### (.*$)/gim, '<h3 style="color:#fff; margin:6px 0;">$1</h3>');
      escaped = escaped.replace(/^## (.*$)/gim, '<h2 style="color:#fff; margin:8px 0;">$1</h2>');
      escaped = escaped.replace(/^# (.*$)/gim, '<h1 style="color:#fff; margin:10px 0;">$1</h1>');
      escaped = escaped.replace(/^\\* (.*$)/gim, '• $1');
      return escaped.replace(/\\n/g, '<br>');
    }

    function handleKey(e) { if (e.key === 'Enter') sendChat(); }

    function quickPrompt(text) {
      document.getElementById('chatInput').value = text;
      sendChat();
    }

    async function resetChat() {
      await fetch('/api/clear-history', { method: 'POST' });
      document.getElementById('chatStream').innerHTML = '<div class="feed-bubble feed-bot">Session cleared. Ready for your next inquiry.</div>';
    }

    function handleImagePicked(file) {
      if (!file) return;
      const reader = new FileReader();
      reader.onload = (e) => {
        const img = new Image();
        img.onload = () => {
          // Downscale to max 800px to ensure fast upload & instant AI vision
          const maxDim = 800;
          let width = img.width;
          let height = img.height;
          if (width > maxDim || height > maxDim) {
            if (width > height) {
              height = Math.round((height * maxDim) / width);
              width = maxDim;
            } else {
              width = Math.round((width * maxDim) / height);
              height = maxDim;
            }
          }
          const canvas = document.createElement('canvas');
          canvas.width = width;
          canvas.height = height;
          const ctx = canvas.getContext('2d');
          ctx.drawImage(img, 0, 0, width, height);

          // Compress to lightweight 0.72 quality JPEG
          attachedImageBase64 = canvas.toDataURL('image/jpeg', 0.72);
          document.getElementById('imageThumb').src = attachedImageBase64;
          document.getElementById('previewTray').style.display = 'flex';
        };
        img.src = e.target.result;
      };
      reader.readAsDataURL(file);
    }

    function clearAttachedImage() {
      attachedImageBase64 = null;
      document.getElementById('previewTray').style.display = 'none';
      document.getElementById('imgInput').value = '';
    }

    function toggleVoice() {
      const micBtn = document.getElementById('micBtn');
      const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
      if (!SpeechRecognition) {
        alert("Speech dictation not supported on this browser.");
        return;
      }

      if (isRecording) {
        recognition.stop();
        return;
      }

      recognition = new SpeechRecognition();
      recognition.lang = 'en-US';
      recognition.interimResults = false;

      recognition.onstart = () => {
        isRecording = true;
        micBtn.classList.add('recording');
      };

      recognition.onresult = (e) => {
        const transcript = e.results[0][0].transcript;
        document.getElementById('chatInput').value = transcript;
      };

      recognition.onerror = () => {
        isRecording = false;
        micBtn.classList.remove('recording');
      };

      recognition.onend = () => {
        isRecording = false;
        micBtn.classList.remove('recording');
        if (document.getElementById('chatInput').value.trim()) {
          sendChat();
        }
      };

      recognition.start();
    }

    function speakText(text) {
      if (!('speechSynthesis' in window)) return;
      window.speechSynthesis.cancel();
      const clean = text.replace(/<[^>]*>?/gm, '').replace(/[*#`]/g, '');
      const utter = new SpeechSynthesisUtterance(clean);
      window.speechSynthesis.speak(utter);
    }

    async function sendChat() {
      const input = document.getElementById('chatInput');
      const text = input.value.trim();
      const sendBtn = document.getElementById('sendBtn');
      const stream = document.getElementById('chatStream');
      const imagePayload = attachedImageBase64;

      if (!text && !imagePayload) return;

      const userBubble = document.createElement('div');
      userBubble.className = 'feed-bubble feed-user';
      if (imagePayload) {
        userBubble.innerHTML = `<img src="${imagePayload}" style="max-width:180px; max-height:140px; border-radius:6px; margin-bottom:6px; display:block;">` + (text ? `<div>${text}</div>` : '');
      } else {
        userBubble.innerText = text;
      }
      stream.appendChild(userBubble);

      input.value = "";
      clearAttachedImage();
      sendBtn.disabled = true;

      const botBubble = document.createElement('div');
      botBubble.className = 'feed-bubble feed-bot';
      botBubble.innerHTML = `
        <details class="reasoning-panel" id="currentThoughtDetails" style="display: none;">
          <summary class="reasoning-trigger">🧠 Thought Chain</summary>
          <div class="reasoning-body" id="currentThought"></div>
        </details>
        <div class="bubble-content" id="currentAnswer"><em>Reflecting...</em></div>
      `;
      stream.appendChild(botBubble);
      stream.scrollTop = stream.scrollHeight;

      let thoughtBuffer = "";
      let answerBuffer = "";
      let inThought = false;

      try {
        const response = await fetch('/ask-stream', {
          method: 'POST',
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify({ prompt: text, image: imagePayload })
        });

        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        const thoughtDetails = botBubble.querySelector('#currentThoughtDetails');
        const thoughtEl = botBubble.querySelector('#currentThought');
        const answerEl = botBubble.querySelector('#currentAnswer');

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;
          const chunk = decoder.decode(value);
          const lines = chunk.split('\\n');

          for (const line of lines) {
            if (line.startsWith('data: ')) {
              const payload = line.replace('data: ', '').trim();
              if (payload === '[DONE]') continue;
              try {
                const parsed = JSON.parse(payload);
                const delta = parsed.delta || '';

                if (delta.includes('<thought>')) {
                  inThought = true;
                  thoughtDetails.style.display = 'block';
                  continue;
                }
                if (delta.includes('</thought>')) {
                  inThought = false;
                  answerEl.innerHTML = '';
                  continue;
                }

                if (inThought) {
                  thoughtBuffer += delta;
                  thoughtEl.innerText = thoughtBuffer;
                } else {
                  answerBuffer += delta;
                  answerEl.innerHTML = renderBasicMarkdown(answerBuffer);
                }
                stream.scrollTop = stream.scrollHeight;
              } catch (e) {}
            }
          }
        }

        if (localStorage.getItem('gelo_tts') === 'true' && answerBuffer) {
          speakText(answerBuffer);
        }
      } catch (err) {
        botBubble.innerHTML = `<span style="color:#ef4444;">Session error: ${err.message}</span>`;
      } finally {
        sendBtn.disabled = false;
        stream.scrollTop = stream.scrollHeight;
      }
    }

    function getCover(track) {
      if (track.spotify?.album?.images?.[0]) return track.spotify.album.images[0].url;
      if (track.apple_music?.artwork) return track.apple_music.artwork.url.replace('{w}x{h}', '300x300');
      return 'https://via.placeholder.com/150/11141b/cbd5e1?text=Classic';
    }

    function renderShazamResult(track) {
      const slot = document.getElementById('resultSlot');
      const coverUrl = getCover(track);
      const spotify = track.spotify?.external_urls?.spotify;
      const apple = track.apple_music?.url;
      const lyrics = track.lyrics?.lyrics;

      slot.innerHTML = `
        <div class="song-result-card">
          <div class="song-primary">
            <img class="song-art" src="${coverUrl}" alt="Artwork">
            <div>
              <div class="song-title">${track.title}</div>
              <div class="song-artist">${track.artist}</div>
              <div class="song-links">
                ${spotify ? `<a class="song-link-pill" href="${spotify}" target="_blank">Spotify</a>` : ''}
                ${apple ? `<a class="song-link-pill" href="${apple}" target="_blank">Apple</a>` : ''}
              </div>
            </div>
          </div>
          ${lyrics ? `
            <details class="reasoning-panel" style="margin-top: 6px;">
              <summary class="reasoning-trigger">📜 Lyrics Notation</summary>
              <div class="reasoning-body">${lyrics}</div>
            </details>
          ` : ''}
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
        list.innerHTML = '<div style="font-size: 11.5px; color: var(--text-dim); padding: 4px 0;">No entries in catalogue.</div>';
        return;
      }
      list.innerHTML = history.map(item => `
        <div class="song-result-card" style="margin-top: 6px; padding: 8px;">
          <div class="song-primary">
            <img class="song-art" style="width: 38px; height: 38px;" src="${item.cover}">
            <div style="flex:1; overflow:hidden;">
              <div class="song-title" style="font-size: 13px; text-overflow:ellipsis; white-space:nowrap; overflow:hidden;">${item.title}</div>
              <div class="song-artist" style="font-size: 11px;">${item.artist}</div>
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
        btn.style.transform = `scale(${1 + ((sum / bufferLength) / 255) * 0.15})`;
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
      status.innerText = "Analyzing Acoustic Signature...";
      container.classList.remove('is-listening');
      stopVisualizer();

      const formData = new FormData();
      formData.append('file', blob, 'audio.webm');

      try {
        const res = await fetch('/identify', { method: 'POST', body: formData });
        const data = await res.json();
        if (data.result && data.result.title) {
          status.innerText = "Composition Identified";
          renderShazamResult(data.result);
        } else {
          status.innerText = "No Record Found";
        }
      } catch (e) {
        status.innerText = "Scan Failed: " + e.message;
      }
    }

    async function startShazam() {
      const status = document.getElementById('radarStatus');
      const container = document.getElementById('pulseContainer');
      document.getElementById('resultSlot').innerHTML = "";

      if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
        status.innerText = "Audio sensor unavailable.";
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
        status.innerText = `Sampling... (${secondsLeft}s)`;
        const timer = setInterval(() => {
          secondsLeft--;
          if (secondsLeft > 0) {
            status.innerText = `Sampling... (${secondsLeft}s)`;
          } else {
            clearInterval(timer);
            if (mediaRecorder.state !== 'inactive') mediaRecorder.stop();
            stream.getTracks().forEach(t => t.stop());
          }
        }, 1000);
      } catch (err) {
        container.classList.remove('is-listening');
        stopVisualizer();
        status.innerHTML = `<span style="color:#ef4444;">Sensor permission denied.</span>`;
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
        return jsonify({"error": "Credentials required."}), 400
    if len(password) < 6:
        return jsonify({"error": "Password requires at least 6 characters."}), 400

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
        return jsonify({"error": "Account exists."}), 409
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
    return jsonify({"error": "Invalid credentials."}), 401

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

@app.route("/api/clear-history", methods=["POST"])
def clear_history():
    if "user" not in session:
        return jsonify({"error": "Unauthorized"}), 401
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("DELETE FROM messages WHERE username = ?", (session["user"],))
    conn.commit()
    conn.close()
    return jsonify({"status": "cleared"})

@app.route("/logout")
def logout():
    session.pop("user", None)
    session.pop("display_name", None)
    return redirect("/login")

# --- PROTECTED APP ROUTE ---
@app.route("/")
def index():
    if "user" not in session:
        return redirect("/login")
    display_name = session.get("display_name") or clean_name(session["user"])

    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT role, text, thinking FROM messages WHERE username = ? ORDER BY id ASC LIMIT 50", (session["user"],))
    rows = c.fetchall()
    conn.close()

    history = [{"role": r[0], "text": r[1], "thinking": r[2]} for r in rows]

    rendered = render_template_string(MAIN_TEMPLATE, display_name=display_name, history=history)
    resp = make_response(rendered)
    resp.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    return resp

# --- SSE STREAMING & VISION ROUTE ---
@app.route("/ask-stream", methods=["POST"])
def ask_stream():
    if "user" not in session:
        return jsonify({"error": "Unauthorized"}), 401

    req_data = request.json or {}
    user_prompt = req_data.get("prompt", "").strip()
    image_base64 = req_data.get("image", None)

    if not user_prompt and not image_base64:
        return jsonify({"error": "Empty inquiry"}), 400
    if not GEMINI_API_KEY:
        return jsonify({"error": "GEMINI_API_KEY missing."}), 500

    username = session["user"]
    display_name = session.get("display_name") or clean_name(username)
    now_utc = datetime.now(timezone.utc).strftime('%A, %B %d, %Y, %H:%M:%S UTC')

    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT role, text FROM messages WHERE username = ? ORDER BY id DESC LIMIT 6", (username,))
    past_rows = c.fetchall()
    past_rows.reverse()

    c.execute("INSERT INTO messages (username, role, text) VALUES (?, ?, ?)", 
              (username, "user", user_prompt if user_prompt else "[Attached Image]"))
    conn.commit()
    conn.close()

    contents = []
    for r in past_rows:
        role = "user" if r[0] == "user" else "model"
        contents.append({"role": role, "parts": [{"text": r[1]}]})

    current_parts = []
    if image_base64 and "," in image_base64:
        header, b64data = image_base64.split(",", 1)
        mime = "image/jpeg"
        if "image/png" in header: mime = "image/png"
        elif "image/webp" in header: mime = "image/webp"
        current_parts.append({
            "inline_data": {
                "mime_type": mime,
                "data": b64data
            }
        })
    if user_prompt:
        current_parts.append({"text": user_prompt})

    contents.append({"role": "user", "parts": current_parts})

    payload = {
        "system_instruction": {
            "parts": [{
                "text": (
                    f"You are Gelo, a high-precision, refined AI collaborator. The user's name is {display_name}. "
                    f"The current reference time is {now_utc}. Engage with professional clarity and zero unnecessary fluff. "
                    "Conduct your step-by-step reasoning process enclosed in <thought>...</thought> tags, "
                    "then deliver your clean final response outside the tags in pristine markdown."
                )
            }]
        },
        "contents": contents
    }

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.8-flash:streamGenerateContent?alt=sse"
    headers = {"Content-Type": "application/json", "x-goog-api-key": GEMINI_API_KEY}

    def generate():
        full_text = ""
        try:
            with requests.post(url, headers=headers, json=payload, stream=True, timeout=35) as res:
                for line in res.iter_lines():
                    if not line:
                        continue
                    line_str = line.decode("utf-8")
                    if line_str.startswith("data: "):
                        data_json = line_str[6:]
                        try:
                            chunk = json.loads(data_json)
                            candidates = chunk.get("candidates", [])
                            if candidates:
                                parts = candidates[0].get("content", {}).get("parts", [])
                                for p in parts:
                                    txt = p.get("text", "")
                                    if txt:
                                        full_text += txt
                                        yield f"data: {json.dumps({'delta': txt})}\\n\\n"
                        except json.JSONDecodeError:
                            continue
            yield "data: [DONE]\\n\\n"

            thought_match = re.search(r'<thought>(.*?)</thought>', full_text, re.DOTALL)
            if thought_match:
                thinking = thought_match.group(1).strip()
                final_answer = re.sub(r'<thought>.*?</thought>', '', full_text, flags=re.DOTALL).strip()
            else:
                thinking = None
                final_answer = full_text.strip()

            c_conn = sqlite3.connect(DB_FILE)
            c_cur = c_conn.cursor()
            c_cur.execute("INSERT INTO messages (username, role, text, thinking) VALUES (?, ?, ?, ?)",
                          (username, "model", final_answer, thinking))
            c_conn.commit()
            c_conn.close()

        except Exception as e:
            yield f"data: {json.dumps({'delta': f'Error: {str(e)}'})}\\n\\n"
            yield "data: [DONE]\\n\\n"

    return Response(stream_with_context(generate()), mimetype="text/event-stream")

@app.route("/ask-fast", methods=["POST"])
def ask_fast():
    if "user" not in session:
        return jsonify({"error": "Unauthorized"}), 401

    req_data = request.json or {}
    user_prompt = req_data.get("prompt", "").strip()
    image_base64 = req_data.get("image", None)

    if not user_prompt and not image_base64:
        return jsonify({"error": "Empty inquiry"}), 400
    if not GEMINI_API_KEY:
        return jsonify({"error": "GEMINI_API_KEY missing."}), 500

    username = session["user"]
    display_name = session.get("display_name") or clean_name(username)
    now_utc = datetime.now(timezone.utc).strftime('%A, %B %d, %Y, %H:%M:%S UTC')

    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT role, text FROM messages WHERE username = ? ORDER BY id DESC LIMIT 6", (username,))
    past_rows = c.fetchall()
    past_rows.reverse()

    c.execute("INSERT INTO messages (username, role, text) VALUES (?, ?, ?)", 
              (username, "user", user_prompt if user_prompt else "[Attached Image]"))
    conn.commit()

    contents = []
    for r in past_rows:
        role = "user" if r[0] == "user" else "model"
        contents.append({"role": role, "parts": [{"text": r[1]}]})

    current_parts = []
    if image_base64 and "," in image_base64:
        header, b64data = image_base64.split(",", 1)
        mime = "image/jpeg"
        if "image/png" in header: mime = "image/png"
        elif "image/webp" in header: mime = "image/webp"
        current_parts.append({"inline_data": {"mime_type": mime, "data": b64data}})
    if user_prompt:
        current_parts.append({"text": user_prompt})

    contents.append({"role": "user", "parts": current_parts})

    payload = {
        "system_instruction": {
            "parts": [{
                "text": (
                    f"You are Gelo, a high-precision AI collaborator. The user's name is {display_name}. "
                    f"The current reference time is {now_utc}. Engage with concise clarity. "
                    "Conduct your step-by-step reasoning process enclosed in <thought>...</thought> tags, "
                    "then deliver your clean final response outside the tags in clean markdown."
                )
            }]
        },
        "contents": contents
    }

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.8-flash:generateContent"
    headers = {"Content-Type": "application/json", "x-goog-api-key": GEMINI_API_KEY}

    try:
        res = requests.post(url, headers=headers, json=payload, timeout=40)
        data = res.json()
        if "candidates" in data and data["candidates"]:
            full_text = data["candidates"][0]["content"]["parts"][0]["text"]
            thought_match = re.search(r'<thought>(.*?)</thought>', full_text, re.DOTALL)
            if thought_match:
                thinking = thought_match.group(1).strip()
                final_answer = re.sub(r'<thought>.*?</thought>', '', full_text, flags=re.DOTALL).strip()
            else:
                thinking = None
                final_answer = full_text.strip()

            c.execute("INSERT INTO messages (username, role, text, thinking) VALUES (?, ?, ?, ?)",
                      (username, "model", final_answer, thinking))
            conn.commit()
            conn.close()

            return jsonify({"thinking": thinking, "answer": final_answer})
    except Exception as e:
        conn.close()
        return jsonify({"error": str(e)}), 500

    conn.close()
    return jsonify({"error": "No response received"}), 500

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
