import os
import sqlite3
import requests
from datetime import datetime, timezone
from flask import Flask, request, jsonify, make_response, session, redirect
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "gelo_production_secret_key_88992211")

DEFAULT_KEY = "AQ.Ab8RN6LZ482CzbwQ3N7V5" + "gf2ojGVTOc4ax8tfTY3j-4RXlqdhQ"
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", DEFAULT_KEY).strip()
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
    conn.commit()
    conn.close()

init_db()

def clean_name(raw_val, custom_display=None):
    if custom_display and custom_display.strip():
        return custom_display.strip()
    if "@" in raw_val:
        return raw_val.split("@")[0]
    return raw_val

# --- AUTH VIEW ---
AUTH_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0">
  <title>HELLO Gelo — Access</title>
  <style>
    :root {
      --bg: #090a0f;
      --surface: #101319;
      --surface-border: rgba(255, 255, 255, 0.08);
      --accent: #38bdf8;
      --text: #f8fafc;
      --text-muted: #738096;
    }
    * { box-sizing: border-box; margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, "SF Pro Text", "Segoe UI", Roboto, sans-serif; }
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
    .brand { display: flex; align-items: center; gap: 8px; margin-bottom: 24px; }
    .brand-mark { font-size: 24px; color: var(--accent); }
    .brand-title { font-size: 20px; font-weight: 700; letter-spacing: 1px; color: #fff; text-transform: uppercase; }
    .auth-card {
      background: var(--surface);
      border: 1px solid var(--surface-border);
      border-radius: 12px;
      padding: 24px;
      width: 100%;
      max-width: 360px;
      box-shadow: 0 20px 40px rgba(0,0,0,0.6);
    }
    .auth-nav { display: grid; grid-template-columns: 1fr 1fr; border-bottom: 1px solid var(--surface-border); margin-bottom: 20px; }
    .auth-tab {
      padding: 10px 0; text-align: center; font-size: 13px; font-weight: 600;
      color: var(--text-muted); cursor: pointer; border-bottom: 2px solid transparent;
      background: none; border-top: none; border-left: none; border-right: none;
    }
    .auth-tab.active { color: #fff; border-bottom-color: var(--accent); }
    .form-group { margin-bottom: 14px; }
    .form-label { display: block; font-size: 11px; font-weight: 600; text-transform: uppercase; color: var(--text-muted); margin-bottom: 6px; }
    .form-input {
      width: 100%; background: #0c0e14; border: 1px solid var(--surface-border);
      color: #fff; padding: 11px 13px; border-radius: 8px; font-size: 13.5px; outline: none;
    }
    .form-input:focus { border-color: var(--accent); }
    .auth-btn {
      width: 100%; background: #fff; color: #090a0f; border: none; padding: 12px;
      border-radius: 8px; font-size: 13.5px; font-weight: 700; cursor: pointer; margin-top: 6px;
    }
    .error-box {
      font-size: 12px; color: #f87171; background: rgba(248, 113, 113, 0.08);
      border: 1px solid rgba(248, 113, 113, 0.2); padding: 8px 12px; border-radius: 6px; margin-bottom: 14px; display: none;
    }
  </style>
</head>
<body>
  <div class="brand">
    <span class="brand-mark">⚡</span>
    <span class="brand-title">HELLO Gelo</span>
  </div>

  <div class="auth-card">
    <div class="auth-nav">
      <button class="auth-tab" id="tabLogin" onclick="setMode('login')">Sign In</button>
      <button class="auth-tab active" id="tabRegister" onclick="setMode('register')">Register</button>
    </div>

    <div id="authError" class="error-box"></div>

    <form onsubmit="handleAuth(event)">
      <div class="form-group" id="displayNameGroup">
        <label class="form-label">Display Name / Nickname</label>
        <input type="text" class="form-input" id="authDisplayName" placeholder="e.g. Angelo">
      </div>
      <div class="form-group">
        <label class="form-label">Username or Email</label>
        <input type="text" class="form-input" id="authUsername" required autocomplete="username">
      </div>
      <div class="form-group">
        <label class="form-label">Password</label>
        <input type="password" class="form-input" id="authPassword" required autocomplete="current-password">
      </div>
      <button type="submit" class="auth-btn" id="submitBtn">Create Account</button>
    </form>
  </div>

  <script>
    let mode = 'register';
    function setMode(m) {
      mode = m;
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

# --- MAIN APP VIEW ---
MAIN_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
  <title>HELLO Gelo</title>
  <style>
    :root {
      --bg: #090a0f;
      --card-bg: #101319;
      --card-border: rgba(255, 255, 255, 0.07);
      --accent: #38bdf8;
      --accent-glow: rgba(56, 189, 248, 0.25);
      --primary: #2563eb;
      --text: #f8fafc;
      --text-muted: #738096;
    }
    * { box-sizing: border-box; margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, "SF Pro Text", "Segoe UI", Roboto, sans-serif; -webkit-tap-highlight-color: transparent; }
    body {
      background-color: var(--bg);
      color: var(--text);
      min-height: 100vh;
      display: flex;
      flex-direction: column;
      align-items: center;
      padding: 14px 10px 18px;
    }
    .top-bar {
      width: 100%;
      max-width: 480px;
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 12px;
    }
    .brand { display: flex; align-items: center; gap: 8px; }
    .brand-icon { font-size: 22px; filter: drop-shadow(0 0 10px var(--accent)); }
    .brand-title {
      font-size: 19px;
      font-weight: 800;
      letter-spacing: -0.5px;
      background: linear-gradient(135deg, #ffffff 30%, #38bdf8 100%);
      -webkit-background-clip: text;
      -webkit-text-fill-color: transparent;
    }
    .user-pill {
      background: #141822;
      border: 1px solid var(--card-border);
      color: #cbd5e1;
      font-size: 12px;
      padding: 4px 10px;
      border-radius: 6px;
      display: flex;
      gap: 8px;
      align-items: center;
    }
    .signout-btn { color: #f87171; text-decoration: underline; cursor: pointer; }
    .tab-bar {
      display: flex;
      background: #0f1218;
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
      font-size: 13px;
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
    .msg-bot { align-self: flex-start; background: #0c0e14; border: 1px solid var(--card-border); color: #e2e8f0; border-bottom-left-radius: 4px; width: 100%; max-width: 95%; }
    .msg-bot strong { color: #fff; }
    .msg-bot code { background: rgba(0, 0, 0, 0.5); color: var(--accent); padding: 2px 6px; border-radius: 4px; font-family: monospace; font-size: 13px; }
    .msg-bot pre { background: rgba(0, 0, 0, 0.6); padding: 10px; border-radius: 8px; overflow-x: auto; margin: 8px 0; }
    .msg-bot pre code { background: transparent; padding: 0; }
    .preview-tray {
      padding: 6px 12px;
      display: none;
      align-items: center;
      gap: 10px;
      background: #0d111a;
      border-top: 1px solid var(--card-border);
    }
    .preview-thumb { width: 38px; height: 38px; border-radius: 6px; object-fit: cover; border: 1px solid var(--card-border); }
    .chat-input-bar { padding: 8px 10px; border-top: 1px solid var(--card-border); background: #0c0e14; display: flex; gap: 6px; align-items: center; }
    .chat-input { flex: 1; background: #141822; border: 1px solid var(--card-border); color: var(--text); padding: 10px 12px; border-radius: 10px; font-size: 14px; outline: none; }
    .chat-input:focus { border-color: var(--accent); }
    .icon-action-btn {
      background: #141822;
      border: 1px solid var(--card-border);
      color: #94a3b8;
      width: 38px;
      height: 38px;
      border-radius: 10px;
      font-size: 16px;
      cursor: pointer;
      display: flex;
      align-items: center;
      justify-content: center;
    }
    .icon-action-btn.active-mic {
      background: #ef4444;
      border-color: #f87171;
      color: #fff;
      animation: mic-pulse 1.2s infinite;
    }
    @keyframes mic-pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.5; } }
    .send-btn { background: #2563eb; border: none; color: #fff; padding: 0 16px; height: 38px; border-radius: 10px; font-size: 14px; font-weight: 700; cursor: pointer; }
    .send-btn:disabled { opacity: 0.5; }
    
    /* Radar */
    .radar-wrapper { display: flex; flex-direction: column; align-items: center; padding: 24px 16px 20px; }
    .pulse-container { position: relative; width: 140px; height: 140px; display: flex; align-items: center; justify-content: center; margin-bottom: 20px; }
    .radar-btn { position: relative; z-index: 2; width: 108px; height: 108px; border-radius: 50%; background: linear-gradient(145deg, #0ea5e9, #2563eb); box-shadow: 0 0 30px var(--accent-glow); display: flex; align-items: center; justify-content: center; cursor: pointer; border: none; color: #fff; font-size: 40px; transition: transform 0.1s ease-out; }
    .pulse-ring { position: absolute; width: 100%; height: 100%; border-radius: 50%; border: 2px solid var(--accent); opacity: 0; pointer-events: none; }
    .is-listening .pulse-ring { animation: ripple 1.6s cubic-bezier(0.2, 0.8, 0.2, 1) infinite; }
    @keyframes ripple { 0% { transform: scale(0.7); opacity: 0.85; } 100% { transform: scale(1.6); opacity: 0; } }
    .radar-status { font-size: 15px; font-weight: 700; color: var(--text-muted); letter-spacing: 0.3px; text-align: center; min-height: 24px; }
    .track-result-card { background: #131720; border: 1px solid var(--card-border); border-radius: 16px; padding: 14px; margin-top: 18px; display: flex; flex-direction: column; gap: 12px; width: 100%; }
    .track-main { display: flex; align-items: center; gap: 14px; }
    .track-artwork { width: 62px; height: 62px; border-radius: 10px; object-fit: cover; flex-shrink: 0; background: #0c0e14; }
    .track-meta { flex: 1; overflow: hidden; }
    .track-name { font-size: 15px; font-weight: 700; color: #fff; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
    .track-artist { font-size: 13px; color: var(--text-muted); margin-top: 2px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
    .store-badges { display: flex; gap: 8px; margin-top: 8px; }
    .store-badge { font-size: 11px; font-weight: 600; padding: 4px 10px; border-radius: 6px; text-decoration: none; color: #fff; background: #0284c7; }
    .history-section { width: 100%; margin-top: 20px; padding-top: 16px; border-top: 1px solid var(--card-border); }
    .history-header { font-size: 12px; font-weight: 700; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.6px; display: flex; justify-content: space-between; margin-bottom: 8px; }
  </style>
</head>
<body>

  <div class="top-bar">
    <div class="brand">
      <span class="brand-icon">⚡</span>
      <span class="brand-title">HELLO Gelo</span>
    </div>
    <div class="user-pill">
      <span>{{ display_name }}</span>
      <span class="signout-btn" onclick="window.location.href='/logout'">Sign Out</span>
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

    <div class="preview-tray" id="previewTray">
      <img id="imageThumb" class="preview-thumb" src="" alt="preview">
      <span style="font-size: 12px; color: #94a3b8; flex: 1;">Image attached</span>
      <span style="color: #ef4444; font-size: 18px; cursor: pointer;" onclick="clearAttachedImage()">&times;</span>
    </div>

    <div class="chat-input-bar">
      <button class="icon-action-btn" onclick="document.getElementById('fileInput').click()" title="Attach image">📎</button>
      <input type="file" id="fileInput" accept="image/*" style="display: none;" onchange="handleImage(this.files[0])">
      <button class="icon-action-btn" id="micBtn" onclick="toggleVoice()" title="Dictate">🎙️</button>
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

  <script>
    let chatHistory = [];
    let attachedImageBase64 = null;
    let recognition = null;
    let isRecording = false;
    let audioCtx, analyser, sourceNode, animFrame;

    document.addEventListener("DOMContentLoaded", renderHistory);

    function switchView(tab) {
      document.getElementById('viewBrain').classList.toggle('active-view', tab === 'brain');
      document.getElementById('viewMusic').classList.toggle('active-view', tab === 'music');
      document.getElementById('tabBrain').classList.toggle('active', tab === 'brain');
      document.getElementById('tabMusic').classList.toggle('active', tab === 'music');
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
      clearAttachedImage();
      document.getElementById('chatStream').innerHTML = '<div class="msg msg-bot">⚡ New topic started. What would you like to explore?</div>';
    }

    function handleImage(file) {
      if (!file) return;
      const reader = new FileReader();
      reader.onload = (e) => {
        const img = new Image();
        img.onload = () => {
          const maxDim = 800;
          let w = img.width, h = img.height;
          if (w > maxDim || h > maxDim) {
            if (w > h) { h = Math.round((h * maxDim) / w); w = maxDim; }
            else { w = Math.round((w * maxDim) / h); h = maxDim; }
          }
          const canvas = document.createElement('canvas');
          canvas.width = w; canvas.height = h;
          canvas.getContext('2d').drawImage(img, 0, 0, w, h);
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
      document.getElementById('fileInput').value = '';
    }

    function toggleVoice() {
      const micBtn = document.getElementById('micBtn');
      const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
      if (!SpeechRecognition) {
        alert("Speech dictation not supported in this browser.");
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
        micBtn.classList.add('active-mic');
      };

      recognition.onresult = (e) => {
        const transcript = e.results[0][0].transcript;
        const input = document.getElementById('chatInput');
        input.value = (input.value ? input.value + " " : "") + transcript;
      };

      recognition.onerror = () => {
        isRecording = false;
        micBtn.classList.remove('active-mic');
      };

      recognition.onend = () => {
        isRecording = false;
        micBtn.classList.remove('active-mic');
        if (document.getElementById('chatInput').value.trim()) {
          sendChat();
        }
      };

      recognition.start();
    }

    async function sendChat() {
      const input = document.getElementById('chatInput');
      const text = input.value.trim();
      const sendBtn = document.getElementById('sendBtn');
      const stream = document.getElementById('chatStream');
      const imgPayload = attachedImageBase64;

      if (!text && !imgPayload) return;

      const userBubble = document.createElement('div');
      userBubble.className = 'msg msg-user';
      if (imgPayload) {
        userBubble.innerHTML = `<img src="${imgPayload}" style="max-width:180px; max-height:140px; border-radius:6px; margin-bottom:6px; display:block;">` + (text ? `<div>${text}</div>` : '');
      } else {
        userBubble.innerText = text;
      }
      stream.appendChild(userBubble);

      const turnParts = [];
      if (imgPayload) {
        const [meta, b64] = imgPayload.split(',');
        turnParts.push({ inline_data: { mime_type: "image/jpeg", data: b64 } });
      }
      if (text) {
        turnParts.push({ text: text });
      }

      chatHistory.push({ role: "user", parts: turnParts });
      input.value = "";
      clearAttachedImage();
      sendBtn.disabled = true;

      const botBubble = document.createElement('div');
      botBubble.className = 'msg msg-bot';
      botBubble.innerHTML = "<em>Reflecting...</em>";
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
          botBubble.innerHTML = renderBasicMarkdown(data.answer);
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
      return 'https://via.placeholder.com/150/11141b/cbd5e1?text=Song';
    }

    function renderShazamResult(track) {
      const slot = document.getElementById('resultSlot');
      const coverUrl = getCover(track);
      const spotify = track.spotify?.external_urls?.spotify;
      const apple = track.apple_music?.url;

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
      status.innerText = "Searching database...";
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
    username = data.get("username", "").strip().lower()
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
        return jsonify({"error": "Account already exists. Please Sign In."}), 409
    finally:
        conn.close()

@app.route("/api/login", methods=["POST"])
def login():
    data = request.json or {}
    username = data.get("username", "").strip().lower()
    password = data.get("password", "").strip()

    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT password_hash, display_name FROM users WHERE LOWER(username) = LOWER(?)", (username,))
    row = c.fetchone()
    conn.close()

    if row and check_password_hash(row[0], password):
        session["user"] = username
        session["display_name"] = row[1] if row[1] else clean_name(username)
        return jsonify({"status": "logged_in"})
    return jsonify({"error": "Invalid username or password."}), 401

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")

# --- APP HOME & CORE API ---
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

    username = session["user"]
    display_name = session.get("display_name") or clean_name(username)
    now_utc = datetime.now(timezone.utc).strftime('%A, %B %d, %Y, %H:%M:%S UTC')

    payload = {
        "system_instruction": {
            "parts": [{
                "text": (
                    f"You are Gelo, an elite conversational AI companion. The user's name is {display_name}. "
                    f"The current reference time is {now_utc}. "
                    "Respond with high intelligence, swiftness, and clean markdown."
                )
            }]
        },
        "contents": history[-6:],
        "generationConfig": {
            "temperature": 0.6,
            "maxOutputTokens": 1024
        }
    }

    headers = {"Content-Type": "application/json", "x-goog-api-key": GEMINI_API_KEY}
    last_error = "Server busy."

    for model in ["gemini-2.5-flash"]:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
        try:
            res = requests.post(url, headers=headers, json=payload, timeout=16)
            data = res.json()
            if "candidates" in data and data["candidates"]:
                parts = data["candidates"][0]["content"]["parts"]
                raw_text = "".join([p.get("text", "") for p in parts]).strip()
                if raw_text:
                    return jsonify({"answer": raw_text})
            elif "error" in data:
                last_error = data["error"].get("message", "API Error")
        except Exception as e:
            last_error = str(e)
            continue

    return jsonify({"error": f"API Error: {last_error}"}), 503

@app.route("/identify", methods=["POST"])
def identify():
    if "user" not in session:
        return jsonify({"error": "Unauthorized"}), 401
    if "file" not in request.files:
        return jsonify({"error": {"error_message": "Missing audio file"}}), 400

    file = request.files["file"]
    data = {"api_token": AUDD_API_KEY, "return": "apple_music,spotify"}
    try:
        res = requests.post("https://api.audd.io/", data=data, files={"file": file.read()}, timeout=25)
        return jsonify(res.json())
    except Exception as e:
        return jsonify({"error": {"error_message": str(e)}}), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
