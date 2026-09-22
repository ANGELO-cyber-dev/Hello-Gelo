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
      gap: 8px;
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
      transition: background 0.2s;
    }
    button.action-btn:active {
      transform: scale(0.98);
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

    /* Shazam UI Styling */
    .shazam-container {
      display: flex;
      flex-direction: column;
      align-items: center;
      padding: 20px 0 10px 0;
    }
    .pulse-wrapper {
      position: relative;
      width: 130px;
      height: 130px;
      display: flex;
      align-items: center;
      justify-content: center;
      margin-bottom: 16px;
    }
    .shazam-circle {
      position: relative;
      z-index: 2;
      width: 100px;
      height: 100px;
      border-radius: 50%;
      background: linear-gradient(135deg, #0088ff, #0051ff);
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      cursor: pointer;
      box-shadow: 0 0 25px rgba(0, 136, 255, 0.45);
      user-select: none;
      transition: transform 0.2s;
    }
    .shazam-circle:active {
      transform: scale(0.94);
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

    /* Track Result Card */
    .track-card {
      margin-top: 16px;
      width: 100%;
      background: #1f2937;
      border-radius: 12px;
      padding: 12px;
      display: flex;
      align-items: center;
      gap: 14px;
      box-sizing: border-box;
    }
    .track-cover {
      width: 64px;
      height: 64px;
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
      font-size: 16px;
      font-weight: 700;
      color: #fff;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }
    .track-artist {
      font-size: 14px;
      color: #94a3b8;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
      margin-top: 2px;
    }
    .track-links {
      display: flex;
      gap: 10px;
      margin-top: 8px;
    }
    .track-link-btn {
      font-size: 12px;
      padding: 4px 8px;
      border-radius: 6px;
      text-decoration: none;
      color: #fff;
      background: #0284c7;
      font-weight: 600;
    }
    #filePicker {
      display: none;
    }
    .sub-link {
      font-size: 12px;
      color: #64748b;
      margin-top: 10px;
      cursor: pointer;
      text-decoration: underline;
    }
  </style>
</head>
<body>

  <div class="header">⚡ HELLO Gelo</div>

  <div class="card">
    <div class="card-title">💬 Conversational Brain</div>
    <textarea id="promptInput" rows="3" placeholder="Ask me anything...">I want to learn Forex Trading can you give me a website I can learn from</textarea>
    <div class="btn-row">
      <button class="action-btn" id="askBtn" onclick="askAi()">Ask Gelo</button>
      <button class="action-btn btn-green" onclick="readAloud()">🗣️ Read</button>
    </div>
    <div id="aiOutput" class="output"></div>
  </div>

  <div class="card">
    <div class="card-title">🎵 Music Recognition</div>
    
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
    </div>
  </div>

  <script>
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
          if (data.answer) {
            output.innerText = data.answer;
          } else {
            output.innerText = data.error || "No response received.";
            output.className = "output error";
          }
        } else {
          output.innerText = "Server is warming up or timed out. Please try again.";
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

    function renderShazamResult(track) {
      const container = document.getElementById('resultContainer');
      const coverUrl = (track.spotify && track.spotify.album && track.spotify.album.images && track.spotify.album.images[0])
        ? track.spotify.album.images[0].url
        : (track.apple_music && track.apple_music.artwork)
          ? track.apple_music.artwork.url.replace('{w}x{h}', '300x300')
          : 'https://via.placeholder.com/150/1e293b/38bdf8?text=Song';

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
    }

    async function uploadAudio(file) {
      if (!file) return;
      const status = document.getElementById('shazamStatus');
      const wrapper = document.getElementById('pulseWrapper');
      status.innerText = "Searching database...";
      status.className = "shazam-status";
      wrapper.classList.remove('pulsing');

      const formData = new FormData();
      formData.append('file', file);

      try {
        const res = await fetch('/identify', { method: 'POST', body: formData });
        const data = await res.json();
        if (data.result && data.result.title) {
          status.innerText = "Track Identified!";
          renderShazamResult(data.result);
        } else if (data.error) {
          status.innerText = "Error: " + (data.error.error_message || "Recognition failed");
          status.className = "shazam-status error";
        } else {
          status.innerText = "No match found. Try playing closer to speaker.";
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

        let secondsLeft = 6;
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

    # Try 2.5-flash first; if unavailable, fallback directly to 3.6-flash
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
