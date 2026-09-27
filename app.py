import os
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
      padding: 20px 16px 40px;
    }

    .brand {
      display: flex;
      align-items: center;
      gap: 10px;
      margin: 8px 0 20px;
    }

    .brand-icon {
      font-size: 26px;
      filter: drop-shadow(0 0 12px var(--accent));
    }

    .brand-title {
      font-size: 24px;
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
      border-radius: 14px;
      width: 100%;
      max-width: 440px;
      margin-bottom: 18px;
    }

    .tab-btn {
      flex: 1;
      border: none;
      background: transparent;
      color: var(--text-muted);
      padding: 10px 14px;
      border-radius: 10px;
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
      border-radius: 20px;
      padding: 20px;
      width: 100%;
      max-width: 440px;
      display: none;
    }

    .glass-card.active-view {
      display: block;
    }

    textarea {
      width: 100%;
      background: rgba(8, 12, 22, 0.7);
      border: 1px solid rgba(255, 255, 255, 0.12);
      color: var(--text);
      padding: 14px;
      border-radius: 14px;
      font-size: 14.5px;
      outline: none;
      resize: vertical;
      margin-bottom: 14px;
    }

    textarea:focus {
      border-color: var(--accent);
    }

    .btn-row {
      display: flex;
      gap: 10px;
    }

    .btn {
      border: none;
      padding: 12px 20px;
      border-radius: 12px;
      font-size: 14px;
      font-weight: 600;
      color: #fff;
      cursor: pointer;
      display: inline-flex;
      align-items: center;
      justify-content: center;
      gap: 6px;
    }

    .btn:active { transform: scale(0.97); }
    .btn:disabled { opacity: 0.5; pointer-events: none; }

    .btn-primary {
      background: linear-gradient(135deg, #2563eb, #1d4ed8);
      box-shadow: 0 4px 14px rgba(37, 99, 235, 0.35);
    }

    .btn-green {
      background: linear-gradient(135deg, #10b981, #059669);
    }

    .ai-output {
      margin-top: 16px;
      padding-top: 14px;
      border-top: 1px solid var(--card-border);
      font-size: 14.5px;
      line-height: 1.65;
      color: #cbd5e1;
      white-space: pre-wrap;
      word-break: break-word;
    }

    .ai-output strong { color: #fff; }
    .ai-output code {
      background: rgba(0, 0, 0, 0.5);
      color: var(--accent);
      padding: 2px 6px;
      border-radius: 5px;
      font-family: monospace;
    }

    .error-box {
      color: #f87171;
      background: rgba(239, 68, 68, 0.1);
      padding: 12px;
      border-radius: 10px;
      border: 1px solid rgba(239, 68, 68, 0.2);
    }

    /* Radar View */
    .radar-wrapper {
      display: flex;
      flex-direction: column;
      align-items: center;
      padding: 28px 0 16px;
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
      align-items: center;
      gap: 14px;
      width: 100%;
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

    #filePicker { display: none; }
  </style>
</head>
<body>

  <div class="brand">
    <span class="brand-icon">⚡</span>
    <span class="brand-title">HELLO Gelo</span>
  </div>

  <div class="tab-bar">
    <button class="tab-btn active" id="tabBrain" onclick="switchView('brain')">💬 Brain</button>
    <button class="tab-btn" id="tabMusic" onclick="switchView('music')">🎵 Music Search</button>
  </div>

  <div class="glass-card active-view" id="viewBrain">
    <textarea id="promptInput" rows="3" placeholder="Ask Gelo anything...">Teach me python programming</textarea>
    <div class="btn-row">
      <button class="btn btn-primary" id="askBtn" onclick="askAi()">Ask Gelo</button>
      <button class="btn btn-green" onclick="readAloud()">🗣️ Read</button>
    </div>
    <div id="aiOutput" class="ai-output" style="display: none;"></div>
  </div>

  <div class="glass-card" id="viewMusic">
    <div class="radar-wrapper">
      <div class="pulse-container" id="pulseContainer">
        <div class="pulse-ring"></div>
        <div class="pulse-ring" style="animation-delay: 0.5s;"></div>
        <button class="radar-btn" id="radarBtn" onclick="startShazam()">⚡</button>
      </div>
      <div class="radar-status" id="radarStatus">Tap to Search</div>
      <div class="upload-link" onclick="document.getElementById('filePicker').click()">or choose an audio file</div>
      <input type="file" id="filePicker" accept="audio/*" onchange="uploadAudio(this.files[0])">
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
    let audioCtx, analyser, sourceNode, animFrame;

    document.addEventListener("DOMContentLoaded", renderHistory);

    function switchView(tab) {
      document.getElementById('viewBrain').classList.toggle('active-view', tab === 'brain');
      document.getElementById('viewMusic').classList.toggle('active-view', tab === 'music');
      document.getElementById('tabBrain').classList.toggle('active', tab === 'brain');
      document.getElementById('tabMusic').classList.toggle('active', tab === 'music');
    }

    // Built-in lightweight markdown formatter (zero external dependencies)
    function renderBasicMarkdown(text) {
      let escaped = text.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
      escaped = escaped.replace(/```([\\s\\S]*?)```/g, '<pre><code>$1</code></pre>');
      escaped = escaped.replace(/`([^`]+)`/g, '<code>$1</code>');
      escaped = escaped.replace(/\\*\\*([^\\*]+)\\*\\*/g, '<strong>$1</strong>');
      escaped = escaped.replace(/^### (.*$)/gim, '<h3 style="color:#38bdf8; margin:8px 0;">$1</h3>');
      escaped = escaped.replace(/^## (.*$)/gim, '<h2 style="color:#38bdf8; margin:10px 0;">$1</h2>');
      escaped = escaped.replace(/^# (.*$)/gim, '<h1 style="color:#38bdf8; margin:12px 0;">$1</h1>');
      return escaped;
    }

    async function askAi() {
      const prompt = document.getElementById('promptInput').value.trim();
      const output = document.getElementById('aiOutput');
      const askBtn = document.getElementById('askBtn');
      if (!prompt) return;

      output.style.display = "block";
      output.innerHTML = "<em>⚡ Gelo is thinking...</em>";
      askBtn.disabled = true;

      try {
        const response = await fetch('/ask', {
          method: 'POST',
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify({ prompt: prompt })
        });

        const data = await response.json();
        if (data.answer) {
          output.innerHTML = renderBasicMarkdown(data.answer);
        } else {
          output.innerHTML = '<div class="error-box">' + (data.error || "No response received.") + '</div>';
        }
      } catch (err) {
        output.innerHTML = '<div class="error-box">Connection failed: ' + err.message + '</div>';
      } finally {
        askBtn.disabled = false;
      }
    }

    function readAloud() {
      const text = document.getElementById('aiOutput').innerText;
      if (!text) return;
      window.speechSynthesis.cancel();
      const utterance = new SpeechSynthesisUtterance(text);
      window.speechSynthesis.speak(utterance);
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

      slot.innerHTML = `
        <div class="track-result-card">
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
      status.innerText = "Searching database...";
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
      document.getElementById('resultSlot').innerHTML = "";

      if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
        document.getElementById('filePicker').click();
        return;
      }

      try {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        startVisualizer(stream);

        let mimeType = 'audio/webm';
        if (MediaRecorder.isTypeSupported('audio/mp4')) mimeType = 'audio/mp4';

        const mediaRecorder = new MediaRecorder(stream);
        const audioChunks = [];

        mediaRecorder.ondataavailable = e => {
          if (e.data && e.data.size > 0) audioChunks.push(e.data);
        };

        mediaRecorder.onstop = () => {
          const audioBlob = new Blob(audioChunks, { type: mimeType });
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
            mediaRecorder.stop();
            stream.getTracks().forEach(t => t.stop());
          }
        }, 1000);
      } catch (err) {
        container.classList.remove('is-listening');
        stopVisualizer();
        document.getElementById('filePicker').click();
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
    prompt = request.json.get("prompt", "")
    if not prompt:
        return jsonify({"error": "Empty prompt"}), 400
    if not GEMINI_API_KEY:
        return jsonify({"error": "GEMINI_API_KEY is missing on Render."}), 500

    headers = {
        "Content-Type": "application/json",
        "x-goog-api-key": GEMINI_API_KEY
    }

    payload = {
        "system_instruction": {
            "parts": [{
                "text": "You are Gelo, a high-speed AI assistant. Answer directly and concisely in sentence one without generic filler. Format using clean markdown."
            }]
        },
        "contents": [{"parts": [{"text": prompt}]}]
    }

    # Short per-model timeout prevents Render gateway timeouts
    models = ["gemini-2.5-flash", "gemini-3.6-flash", "gemini-1.5-flash"]
    last_err = ""

    for model in models:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
        try:
            res = requests.post(url, headers=headers, json=payload, timeout=8)
            data = res.json()
            if "candidates" in data and data["candidates"]:
                text = data["candidates"][0]["content"]["parts"][0]["text"]
                return jsonify({"answer": text})
            elif "error" in data:
                last_err = data["error"].get("message", "")
                continue
        except Exception as e:
            last_err = str(e)
            continue

    return jsonify({"error": f"Service busy, please retry: {last_err}"}), 503

@app.route("/identify", methods=["POST"])
def identify():
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
