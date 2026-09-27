import os
import requests
from flask import Flask, request, jsonify, render_template_string

app = Flask(__name__)

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
AUDD_API_KEY = os.getenv("AUDD_API_KEY", "").strip()

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>HELLO Gelo</title>
  <style>
    body {
      background-color: #0b0f19;
      color: #e6edf3;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
      margin: 0;
      padding: 16px;
      display: flex;
      flex-direction: column;
      align-items: center;
    }
    .header {
      font-size: 24px;
      font-weight: 800;
      color: #38bdf8;
      margin: 12px 0 20px 0;
      letter-spacing: 0.5px;
    }
    .card {
      background: #111827;
      border: 1px solid #1f2937;
      border-radius: 16px;
      padding: 18px;
      width: 100%;
      max-width: 440px;
      margin-bottom: 20px;
      box-sizing: border-box;
      box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.5);
    }
    .card-title {
      font-size: 15px;
      font-weight: 700;
      margin-bottom: 14px;
      color: #94a3b8;
      text-transform: uppercase;
      letter-spacing: 0.8px;
      display: flex;
      align-items: center;
      justify-content: space-between;
    }
    textarea {
      width: 100%;
      background: #030712;
      border: 1px solid #374151;
      color: #f3f4f6;
      padding: 12px;
      border-radius: 10px;
      font-size: 14px;
      box-sizing: border-box;
      margin-bottom: 12px;
      resize: vertical;
    }
    .btn-row {
      display: flex;
      gap: 10px;
    }
    button.action-btn {
      background: #2563eb;
      border: none;
      color: #fff;
      padding: 10px 16px;
      border-radius: 8px;
      font-size: 14px;
      font-weight: 600;
      cursor: pointer;
    }
    button.btn-green {
      background: #059669;
    }
    .output {
      margin-top: 14px;
      font-size: 14px;
      line-height: 1.6;
      color: #cbd5e1;
      white-space: pre-wrap;
      word-break: break-word;
    }
    .error {
      color: #f87171;
    }

    /* Shazam Radar & Visualizer */
    .shazam-container {
      display: flex;
      flex-direction: column;
      align-items: center;
      padding: 16px 0 6px 0;
    }
    .pulse-wrapper {
      position: relative;
      width: 130px;
      height: 130px;
      display: flex;
      align-items: center;
      justify-content: center;
      margin-bottom: 14px;
    }
    .shazam-circle {
      position: relative;
      z-index: 2;
      width: 96px;
      height: 96px;
      border-radius: 50%;
      background: linear-gradient(135deg, #0088ff, #0051ff);
      display: flex;
      align-items: center;
      justify-content: center;
      cursor: pointer;
      box-shadow: 0 0 25px rgba(0, 136, 255, 0.45);
      user-select: none;
      transition: transform 0.1s ease-out;
    }
    .shazam-icon {
      font-size: 38px;
      line-height: 1;
    }
    .pulse-ring {
      position: absolute;
      top: 0;
      left: 0;
      width: 100%;
      height: 100%;
      border-radius: 50%;
      border: 3px solid #0088ff;
      opacity: 0;
      pointer-events: none;
      box-sizing: border-box;
    }
    .pulsing .pulse-ring {
      animation: ripple 1.6s cubic-bezier(0.2, 0.8, 0.2, 1) infinite;
    }
    @keyframes ripple {
      0% {
        transform: scale(0.7);
        opacity: 0.9;
      }
      100% {
        transform: scale(1.6);
        opacity: 0;
      }
    }
    .shazam-status {
      font-size: 15px;
      font-weight: 600;
      color: #94a3b8;
      text-align: center;
      min-height: 22px;
    }
    .sub-link {
      font-size: 12px;
      color: #64748b;
      margin-top: 8px;
      cursor: pointer;
      text-decoration: underline;
    }

    /* Track Cards */
    .track-card {
      margin-top: 14px;
      width: 100%;
      background: #1f2937;
      border-radius: 12px;
      padding: 12px;
      display: flex;
      align-items: center;
      gap: 12px;
      box-sizing: border-box;
      border-left: 4px solid #0088ff;
    }
    .track-cover {
      width: 58px;
      height: 58px;
      border-radius: 8px;
      background: #374151;
      object-fit: cover;
      flex-shrink: 0;
    }
    .track-info {
      flex-grow: 1;
      overflow: hidden;
    }
    .track-title {
      font-size: 15px;
      font-weight: 700;
      color: #fff;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }
    .track-artist {
      font-size: 13px;
      color: #94a3b8;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
      margin-top: 2px;
    }
    .track-links {
      display: flex;
      gap: 8px;
      margin-top: 6px;
    }
    .track-link-btn {
      font-size: 11px;
      padding: 3px 8px;
      border-radius: 5px;
      text-decoration: none;
      color: #fff;
      background: #0284c7;
      font-weight: 600;
    }
    .history-card {
      background: #172033;
      padding: 10px;
      margin-top: 8px;
      border-left: 3px solid #3b82f6;
    }
    .history-header {
      font-size: 13px;
      color: #60a5fa;
      font-weight: 600;
      margin-top: 16px;
      margin-bottom: 6px;
      display: flex;
      justify-content: space-between;
      align-items: center;
    }
    .clear-btn {
      font-size: 11px;
      color: #94a3b8;
      cursor: pointer;
      text-decoration: underline;
    }
    #filePicker {
      display: none;
    }
  </style>
</head>
<body>

  <div class="header">⚡ HELLO Gelo</div>

  <div class="card">
    <div class="card-title">💬 Conversational Brain</div>
    <textarea id="promptInput" rows="3" placeholder="Ask me anything...">Hello Gelo</textarea>
    <div class="btn-row">
      <button class="action-btn" id="askBtn" onclick="askAi()">Ask Gelo</button>
      <button class="action-btn btn-green" onclick="readAloud()">🗣️ Read</button>
    </div>
    <div id="aiOutput" class="output"></div>
  </div>

  <div class="card">
    <div class="card-title">
      <span>🎵 Music Recognition</span>
    </div>
    
    <div class="shazam-container">
      <div id="pulseWrapper" class="pulse-wrapper">
        <div class="pulse-ring"></div>
        <div class="pulse-ring" style="animation-delay: 0.6s;"></div>
        <div class="shazam-circle" id="shazamBtn" onclick="startShazam()">
          <span class="shazam-icon">⚡</span>
        </div>
      </div>
      <div class="shazam-status" id="shazamStatus">Tap to Search</div>
      <div class="sub-link" onclick="document.getElementById('filePicker').click()">or upload audio file</div>
      <input type="file" id="filePicker" accept="audio/*" onchange="uploadAudio(this.files[0])">
      <div id="resultContainer" style="width: 100%;"></div>

      <div style="width: 100%;">
        <div class="history-header">
          <span>Search History</span>
          <span class="clear-btn" onclick="clearHistory()">Clear</span>
        </div>
        <div id="historyList"></div>
      </div>
    </div>
  </div>

  <script>
    let audioCtx, analyser, sourceNode, animationId;

    document.addEventListener("DOMContentLoaded", renderHistory);

    async function askAi() {
      const prompt = document.getElementById('promptInput').value.trim();
      const output = document.getElementById('aiOutput');
      const askBtn = document.getElementById('askBtn');
      if (!prompt) return;

      output.innerText = "Thinking...";
      output.className = "output";
      askBtn.disabled = true;

      try {
        const response = await fetch('/ask', {
          method: 'POST',
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify({ prompt })
        });
        const contentType = response.headers.get("content-type");
        if (contentType && contentType.includes("application/json")) {
          const data = await response.json();
          output.innerText = data.answer || data.error || "No response received.";
          if (data.error) output.className = "output error";
        } else {
          output.innerText = "Server is warming up. Please try again.";
          output.className = "output error";
        }
      } catch (err) {
        output.innerText = "Connection error: " + err.message;
        output.className = "output error";
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
      const container = document.getElementById('resultContainer');
      const coverUrl = getCover(track);
      const spotifyLink = track.spotify ? track.spotify.external_urls.spotify : null;
      const appleLink = track.apple_music ? track.apple_music.url : null;

      container.innerHTML = `
        <div class="track-card">
          <img class="track-cover" src="${coverUrl}" alt="Album Art">
          <div class="track-info">
            <div class="track-title">${track.title}</div>
            <div class="track-artist">${track.artist}</div>
            <div class="track-links">
              ${spotifyLink ? `<a class="track-link-btn" href="${spotifyLink}" target="_blank">Spotify</a>` : ''}
              ${appleLink ? `<a class="track-link-btn" href="${appleLink}" target="_blank">Apple Music</a>` : ''}
            </div>
          </div>
        </div>
      `;
      saveToHistory(track);
    }

    function saveToHistory(track) {
      const history = JSON.parse(localStorage.getItem('gelo_music_history') || '[]');
      const filtered = history.filter(item => item.title !== track.title);
      filtered.unshift({
        title: track.title,
        artist: track.artist,
        cover: getCover(track),
        spotify: track.spotify ? track.spotify.external_urls.spotify : null,
        apple: track.apple_music ? track.apple_music.url : null
      });
      localStorage.setItem('gelo_music_history', JSON.stringify(filtered.slice(0, 6)));
      renderHistory();
    }

    function renderHistory() {
      const list = document.getElementById('historyList');
      const history = JSON.parse(localStorage.getItem('gelo_music_history') || '[]');
      if (history.length === 0) {
        list.innerHTML = `<div style="font-size: 12px; color: #475569; padding: 4px 0;">No searches yet.</div>`;
        return;
      }
      list.innerHTML = history.map(item => `
        <div class="track-card history-card">
          <img class="track-cover" style="width: 44px; height: 44px;" src="${item.cover}">
          <div class="track-info">
            <div class="track-title" style="font-size: 14px;">${item.title}</div>
            <div class="track-artist" style="font-size: 12px;">${item.artist}</div>
            <div class="track-links">
              ${item.spotify ? `<a class="track-link-btn" style="font-size: 10px; padding: 2px 6px;" href="${item.spotify}" target="_blank">Spotify</a>` : ''}
              ${item.apple ? `<a class="track-link-btn" style="font-size: 10px; padding: 2px 6px;" href="${item.apple}" target="_blank">Apple</a>` : ''}
            </div>
          </div>
        </div>
      `).join('');
    }

    function clearHistory() {
      localStorage.removeItem('gelo_music_history');
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
      const button = document.getElementById('shazamBtn');

      function draw() {
        animationId = requestAnimationFrame(draw);
        analyser.getByteFrequencyData(dataArray);
        let sum = 0;
        for (let i = 0; i < bufferLength; i++) sum += dataArray[i];
        let average = sum / bufferLength;
        let scale = 1 + (average / 255) * 0.22;
        button.style.transform = `scale(${scale})`;
      }
      draw();
    }

    function stopVisualizer() {
      if (animationId) cancelAnimationFrame(animationId);
      if (sourceNode) sourceNode.disconnect();
      if (audioCtx && audioCtx.state !== 'closed') audioCtx.close();
      const button = document.getElementById('shazamBtn');
      if (button) button.style.transform = 'scale(1)';
    }

    async function uploadAudio(file) {
      if (!file) return;
      const status = document.getElementById('shazamStatus');
      const wrapper = document.getElementById('pulseWrapper');
      status.innerText = "Searching database...";
      status.className = "shazam-status";
      wrapper.classList.remove('pulsing');
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
          status.innerText = "No exact match. Try playing closer.";
          status.className = "shazam-status error";
        }
      } catch (e) {
        status.innerText = "Upload failed: " + e.message;
        status.className = "shazam-status error";
      }
    }

    async function startShazam() {
      const status = document.getElementById('shazamStatus');
      const wrapper = document.getElementById('pulseWrapper');
      const resContainer = document.getElementById('resultContainer');
      resContainer.innerHTML = "";

      if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
        document.getElementById('filePicker').click();
        return;
      }

      try {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        startVisualizer(stream);

        let mimeType = 'audio/webm';
        if (MediaRecorder.isTypeSupported('audio/mp4')) {
          mimeType = 'audio/mp4';
        }

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
        wrapper.classList.add('pulsing');

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
        wrapper.classList.remove('pulsing');
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
    return render_template_string(HTML_TEMPLATE)

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
    payload = {"contents": [{"parts": [{"text": prompt}]}]}

    for model in ["gemini-2.5-flash", "gemini-3.6-flash"]:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
        try:
            res = requests.post(url, headers=headers, json=payload, timeout=18)
            data = res.json()
            if "candidates" in data and data["candidates"]:
                text = data["candidates"][0]["content"]["parts"][0]["text"]
                return jsonify({"answer": text})
            elif "error" in data:
                continue
        except Exception:
            continue

    return jsonify({"error": "Gemini servers are busy. Please tap Ask Gelo again in a moment."}), 503

@app.route("/identify", methods=["POST"])
def identify():
    if "file" not in request.files:
        return jsonify({"error": {"error_message": "Missing audio file"}}), 400
    file = request.files["file"]
    data = {"api_token": AUDD_API_KEY, "return": "apple_music,spotify"}
    try:
        res = requests.post("https://api.audd.io/", data=data, files={"file": file.read()}, timeout=30)
        return jsonify(res.json())
    except Exception as e:
        return jsonify({"error": {"error_message": str(e)}}), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
