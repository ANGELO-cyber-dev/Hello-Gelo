import os
import re
import requests
from flask import Flask, request, jsonify, make_response

app = Flask(__name__)

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
AUDD_API_KEY = os.getenv("AUDD_API_KEY", "").strip()

HTML_PAGE = """<!DOCTYPE html>
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

    * {
      box-sizing: border-box;
      margin: 0;
      padding: 0;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
      -webkit-tap-highlight-color: transparent;
    }

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

    .brand {
      display: flex;
      align-items: center;
      gap: 8px;
      margin: 4px 0 14px;
    }

    .brand-icon {
      font-size: 24px;
      filter: drop-shadow(0 0 12px var(--accent));
    }

    .brand-title {
      font-size: 22px;
      font-weight: 800;
      letter-spacing: -0.5px;
      background: linear-gradient(135deg, #ffffff 30%, #38bdf8 100%);
      -webkit-background-clip: text;
      -webkit-text-fill-color: transparent;
    }

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

    .tab-btn.active {
      background: rgba(56, 189, 248, 0.15);
      color: var(--accent);
    }

    .glass-card {
      background: var(--card-bg);
      border: 1px solid var(--card-border);
      border-radius: 18px;
      width: 100%;
      max-width: 480px;
      display: none;
      overflow: hidden;
    }

    .glass-card.active-view {
      display: flex;
      flex-direction: column;
    }

    /* Multi-turn Chat Container */
    #viewBrain {
      height: 78vh;
      display: none;
    }

    #viewBrain.active-view {
      display: flex;
    }

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

    .chat-reset-btn {
      color: #64748b;
      font-size: 12px;
      cursor: pointer;
      text-decoration: underline;
    }

    .chat-stream {
      flex: 1;
      overflow-y: auto;
      padding: 14px;
      display: flex;
      flex-direction: column;
      gap: 14px;
      scroll-behavior: smooth;
    }

    .msg {
      max-width: 88%;
      padding: 10px 14px;
      border-radius: 14px;
      font-size: 14px;
      line-height: 1.55;
      word-break: break-word;
    }

    .msg-user {
      align-self: flex-end;
      background: linear-gradient(135deg, #2563eb, #1d4ed8);
      color: #fff;
      border-bottom-right-radius: 4px;
    }

    .msg-bot {
      align-self: flex-start;
      background: rgba(15, 23, 42, 0.85);
      border: 1px solid var(--card-border);
      color: #e2e8f0;
      border-bottom-left-radius: 4px;
      width: 100%;
      max-width: 95%;
    }

    .msg-bot strong { color: #fff; }
    .msg-bot code {
      background: rgba(0, 0, 0, 0.5);
      color: var(--accent);
      padding: 2px 6px;
      border-radius: 4px;
      font-family: monospace;
      font-size: 13px;
    }
    .msg-bot pre {
      background: rgba(0, 0, 0, 0.6);
      padding: 10px;
      border-radius: 8px;
      overflow-x: auto;
      margin: 8px 0;
    }
    .msg-bot pre code {
      background: transparent;
      padding: 0;
    }

    .thought-details {
      margin-bottom: 8px;
      background: rgba(0, 0, 0, 0.35);
      border: 1px solid rgba(56, 189, 248, 0.2);
      border-radius: 8px;
      overflow: hidden;
      font-size: 12px;
    }

    .thought-summary {
      padding: 6px 10px;
      cursor: pointer;
      color: var(--accent);
      font-weight: 600;
      user-select: none;
    }

    .thought-content {
      padding: 8px 10px;
      color: #94a3b8;
      border-top: 1px solid rgba(255, 255, 255, 0.05);
      white-space: pre-wrap;
    }

    .chat-input-bar {
      padding: 10px;
      border-top: 1px solid var(--card-border);
      background: rgba(11, 15, 25, 0.95);
      display: flex;
      gap: 8px;
      align-items: center;
    }

    .chat-input {
      flex: 1;
      background: rgba(18, 24, 38, 0.8);
      border: 1px solid rgba(255, 255, 255, 0.12);
      color: var(--text);
      padding: 10px 14px;
      border-radius: 12px;
      font-size: 14px;
      outline: none;
    }

    .chat-input:focus {
      border-color: var(--accent);
    }

    .send-btn {
      background: #2563eb;
      border: none;
      color: #fff;
      padding: 10px 16px;
      border-radius: 12px;
      font-size: 14px;
      font-weight: 700;
      cursor: pointer;
    }

    .send-btn:disabled {
      opacity: 0.5;
    }

    /* Radar View */
    .radar-wrapper {
      display: flex;
      flex-direction: column;
      align-items: center;
      padding: 24px 16px 20px;
    }

    .pulse-container {
      position: relative;
      width: 140px;
      height: 140px;
      display: flex;
      align-items: center;
      justify-content: center;
      margin-bottom: 20px;
    }

    .radar-btn {
      position: relative;
      z-index: 2;
      width: 108px;
      height: 108px;
      border-radius: 50%;
      background: linear-gradient(145deg, #0ea5e9, #2563eb);
      box-shadow: 0 0 30px var(--accent-glow);
      display: flex;
      align-items: center;
      justify-content: center;
      cursor: pointer;
      border: none;
      color: #fff;
      font-size: 40px;
      transition: transform 0.1s ease-out;
    }

    .pulse-ring {
      position: absolute;
      width: 100%;
      height: 100%;
      border-radius: 50%;
      border: 2px solid var(--accent);
      opacity: 0;
      pointer-events: none;
    }

    .is-listening .pulse-ring {
      animation: ripple 1.6s cubic-bezier(0.2, 0.8, 0.2, 1) infinite;
    }

    @keyframes ripple {
      0% { transform: scale(0.7); opacity: 0.85; }
      100% { transform: scale(1.6); opacity: 0; }
    }

    .radar-status {
      font-size: 15px;
      font-weight: 700;
      color: var(--text-muted);
      letter-spacing: 0.3px;
      text-align: center;
      min-height: 24px;
    }

    .upload-link {
      font-size: 12px;
      color: #64748b;
      margin-top: 10px;
      cursor: pointer;
      text-decoration: underline;
    }

    .track-result-card {
      background: rgba(30, 41, 59, 0.6);
      border: 1px solid rgba(255, 255, 255, 0.08);
      border-radius: 16px;
      padding: 14px;
      margin-top: 18px;
      display: flex;
      flex-direction: column;
      gap: 12px;
      width: 100%;
    }

    .track-main {
      display: flex;
      align-items: center;
      gap: 14px;
    }

    .track-artwork {
      width: 62px;
      height: 62px;
      border-radius: 10px;
      object-fit: cover;
      flex-shrink: 0;
      background: #1e293b;
    }

    .track-meta { flex: 1; overflow: hidden; }
    .track-name {
      font-size: 15px;
      font-weight: 700;
      color: #fff;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }

    .track-artist {
      font-size: 13px;
      color: var(--text-muted);
      margin-top: 2px;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }

    .store-badges { display: flex; gap: 8px; margin-top: 8px; }
    .store-badge {
      font-size: 11px;
      font-weight: 600;
      padding: 4px 10px;
      border-radius: 6px;
      text-decoration: none;
      color: #fff;
      background: #0284c7;
    }

    .lyrics-drawer {
      background: rgba(15, 23, 42, 0.6);
      border: 1px solid rgba(255, 255, 255, 0.06);
      border-radius: 10px;
      overflow: hidden;
    }

    .lyrics-summary {
      font-size: 12px;
      font-weight: 700;
      color: var(--accent);
      padding: 8px 12px;
      cursor: pointer;
      user-select: none;
      display: flex;
      align-items: center;
      gap: 6px;
    }

    .lyrics-body {
      font-size: 12.5px;
      line-height: 1.6;
      color: #cbd5e1;
      padding: 10px 12px;
      max-height: 220px;
      overflow-y: auto;
      white-space: pre-wrap;
      border-top: 1px solid rgba(255, 255, 255, 0.05);
    }

    .history-section {
      width: 100%;
      margin-top: 20px;
      padding-top: 16px;
      border-top: 1px solid var(--card-border);
    }

    .history-header {
      font-size: 12px;
      font-weight: 700;
      color: var(--text-muted);
      text-transform: uppercase;
      letter-spacing: 0.6px;
      display: flex;
      justify-content: space-between;
      margin-bottom: 8px;
    }

    
  </style>
</head>
<body>

  <div class="brand">
    <span class="brand-icon">⚡</span>
    <span class="brand-title">HELLO Gelo</span>
  </div>

  <div class="tab-bar">
    <button class="tab-btn active" id="tabBrain" onclick="switchView('brain')">💬 Ask Gelo</button>
    <button class="tab-btn" id="tabMusic" onclick="switchView('music')">🎵 Music Search</button>
  </div>

  <!-- MULTI-TURN CHAT VIEW -->
  <div class="glass-card active-view" id="viewBrain">
    <div class="chat-header">
      <span>AI Conversation</span>
      <span class="chat-reset-btn" onclick="resetChat()">New Topic</span>
    </div>
    
    <div class="chat-stream" id="chatStream">
      <div class="msg msg-bot">
        ⚡ Hi, I'm Gelo! What would you like to explore or learn today?
      </div>
    </div>

    <div class="chat-input-bar">
      <input type="text" class="chat-input" id="chatInput" placeholder="Reply or ask a question..." onkeydown="handleKey(event)">
      <button class="send-btn" id="sendBtn" onclick="sendChat()">Send</button>
    </div>
  </div>

  <!-- MUSIC RECOGNITION VIEW -->
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

    function handleKey(e) {
      if (e.key === 'Enter') sendChat();
    }

    function resetChat() {
      chatHistory = [];
      const stream = document.getElementById('chatStream');
      stream.innerHTML = '<div class="msg msg-bot">⚡ New conversation started. What would you like to explore?</div>';
    }

    async function sendChat() {
      const input = document.getElementById('chatInput');
      const text = input.value.trim();
      const sendBtn = document.getElementById('sendBtn');
      const stream = document.getElementById('chatStream');
      if (!text) return;

      // Render User Bubble
      const userBubble = document.createElement('div');
      userBubble.className = 'msg msg-user';
      userBubble.innerText = text;
      stream.appendChild(userBubble);

      // Add to conversation memory
      chatHistory.push({ role: "user", parts: [{ text: text }] });
      input.value = "";
      sendBtn.disabled = true;

      // Render Thinking Placeholder
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

          // Remember bot answer in context
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
      if (track.spotify && track.spotify.album && track.spotify.album.images && track.spotify.album.images[0]) {
        return track.spotify.album.images[0].url;
      }
      if (track.apple_music && track.apple_music.artwork) {
        return track.apple_music.artwork.url.replace('{w}x{h}', '300x300');
      }
      return 'https://via.placeholder.com/150/1e293b/38bdf8?text=Song';
    }

    function renderShazamResult(track) {
      const slot = document.getElementById('resultSlot');
      const coverUrl = getCover(track);
      const spotify = track.spotify ? track.spotify.external_urls.spotify : null;
      const apple = track.apple_music ? track.apple_music.url : null;
      const lyrics = track.lyrics ? track.lyrics.lyrics : null;

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
                Lyrics not directly in database. You can find full licensed lyrics for "${track.title}" on Spotify or Apple Music.
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
        spotify: track.spotify ? track.spotify.external_urls.spotify : null,
        apple: track.apple_music ? track.apple_music.url : null
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
        let avg = sum / bufferLength;
        btn.style.transform = `scale(${1 + (avg / 255) * 0.22})`;
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

    async function uploadAudio(file) {
      if (!file) return;
      const status = document.getElementById('radarStatus');
      const container = document.getElementById('pulseContainer');
      status.innerText = "Searching database & lyrics...";
      container.classList.remove('is-listening');
      stopVisualizer();

      const formData = new FormData();
      formData.append('file', file);

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
        status.innerText = "Upload failed: " + e.message;
      }
    }

    async function startShazam() {
      const status = document.getElementById('radarStatus');
      const container = document.getElementById('pulseContainer');
      const resultSlot = document.getElementById('resultSlot');
      if (resultSlot) resultSlot.innerHTML = "";

      if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
        status.innerText = "Mic not supported. Use file upload.";
        return;
      }

      try {
        const stream = await navigator.mediaDevices.getUserMedia({ 
          audio: { echoCancellation: true, noiseSuppression: true } 
        });
        startVisualizer(stream);

        let mimeType = '';
        if (typeof MediaRecorder !== 'undefined') {
          if (MediaRecorder.isTypeSupported('audio/webm;codecs=opus')) mimeType = 'audio/webm;codecs=opus';
          else if (MediaRecorder.isTypeSupported('audio/webm')) mimeType = 'audio/webm';
          else if (MediaRecorder.isTypeSupported('audio/mp4')) mimeType = 'audio/mp4';
          else if (MediaRecorder.isTypeSupported('audio/aac')) mimeType = 'audio/aac';
        }

        const options = mimeType ? { mimeType } : {};
        const mediaRecorder = new MediaRecorder(stream, options);
        const audioChunks = [];

        mediaRecorder.ondataavailable = e => {
          if (e.data && e.data.size > 0) audioChunks.push(e.data);
        };

        mediaRecorder.onstop = () => {
          const finalMime = mimeType || 'audio/webm';
          const audioBlob = new Blob(audioChunks, { type: finalMime });
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
        if (err.name === 'NotAllowedError' || err.name === 'PermissionDeniedError') {
          status.innerHTML = `<span style="color:#f87171;">Mic permission denied. Allow mic in browser settings.</span>`;
        } else {
          status.innerHTML = `<span style="color:#f87171;">Mic error: ${err.message}</span>`;
        }
      }
    }
  </script>
</body>
</html>
"""

@app.route("/")
def index():
    resp = make_response(HTML_PAGE)
    resp.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    return resp

@app.route("/ask", methods=["POST"])
def ask():
    req_data = request.json or {}
    history = req_data.get("history", [])

    if not history:
        prompt = req_data.get("prompt", "")
        if prompt:
            history = [{"role": "user", "parts": [{"text": prompt}]}]
        else:
            return jsonify({"error": "Empty message"}), 400

    if not GEMINI_API_KEY:
        return jsonify({"error": "GEMINI_API_KEY missing on Render."}), 500

    headers = {
        "Content-Type": "application/json",
        "x-goog-api-key": GEMINI_API_KEY
    }

    # Pass the full conversational thread so Gelo remembers context
    payload = {
        "system_instruction": {
            "parts": [{
                "text": (
                    "You are Gelo, an elite conversational AI companion. "
                    "Engage in natural, continuous, multi-turn conversation. Remember details from prior messages. "
                    "Conduct a step-by-step reasoning process enclosed in <thought>...</thought> tags, "
                    "then deliver your final answer in clean, scannable markdown outside the tags."
                )
            }]
        },
        "contents": history[-8:] # Keep the last 8 turns for high speed & quota efficiency
    }

    models = ["gemini-3.8-flash", "gemini-3.6-flash"]
    last_err = ""

    for model in models:
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
                    thinking = "Analyzed conversation history and formulated the direct next step."
                    answer = raw_text.strip()

                return jsonify({
                    "thinking": thinking,
                    "answer": answer
                })
            elif "error" in data:
                last_err = data["error"].get("message", "")
                continue
        except Exception as e:
            last_err = str(e)
            continue

    return jsonify({"error": f"Service busy: {last_err}"}), 503

@app.route("/identify", methods=["POST"])
def identify():
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
