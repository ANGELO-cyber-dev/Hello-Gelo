import os
import json
import requests
from flask import Flask, request, jsonify, render_template_string, Response, stream_with_context

app = Flask(__name__)

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
AUDD_API_KEY = os.getenv("AUDD_API_KEY", "")

def get_active_model() -> str:
    """Detect available model or fallback."""
    if not GEMINI_API_KEY:
        return "gemini-2.5-flash"
    try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models?key={GEMINI_API_KEY}"
        res = requests.get(url, timeout=5).json()
        if "models" in res:
            for m in res["models"]:
                methods = m.get("supportedGenerationMethods", [])
                name = m.get("name", "").replace("models/", "")
                if "generateContent" in methods and "flash" in name:
                    return name
    except Exception:
        pass
    return "gemini-2.5-flash"

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Hello Gelo - Live AI</title>
  <style>
    body {
      background-color: #0d1117;
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
      font-weight: bold;
      color: #58a6ff;
      margin-bottom: 20px;
    }
    .card {
      background: #161b22;
      border: 1px solid #30363d;
      border-radius: 12px;
      padding: 16px;
      width: 100%;
      max-width: 440px;
      margin-bottom: 16px;
      box-sizing: border-box;
    }
    .card-title {
      font-size: 16px;
      font-weight: 600;
      margin-bottom: 12px;
      display: flex;
      align-items: center;
      gap: 8px;
    }
    textarea, input {
      width: 100%;
      background: #0d1117;
      border: 1px solid #30363d;
      color: #e6edf3;
      padding: 10px;
      border-radius: 8px;
      font-size: 14px;
      box-sizing: border-box;
      margin-bottom: 10px;
    }
    .btn-row {
      display: flex;
      gap: 10px;
    }
    button {
      background: #1f6feb;
      border: none;
      color: #fff;
      padding: 10px 14px;
      border-radius: 8px;
      font-size: 14px;
      font-weight: 600;
      cursor: pointer;
    }
    button.btn-green {
      background: #238636;
    }
    button:disabled {
      opacity: 0.5;
    }
    .output {
      margin-top: 12px;
      font-size: 14px;
      line-height: 1.5;
      color: #c9d1d9;
      white-space: pre-wrap;
      word-break: break-word;
      min-height: 24px;
    }
    .cursor::after {
      content: "▋";
      color: #58a6ff;
      animation: blink 1s infinite;
    }
    @keyframes blink {
      0%, 100% { opacity: 1; }
      50% { opacity: 0; }
    }
    .error {
      color: #f85149;
    }
  </style>
</head>
<body>

  <div class="header">⚡ Hello Gelo Live</div>

  <!-- Live Conversational Brain -->
  <div class="card">
    <div class="card-title">💬 Conversational Brain (Live Stream)</div>
    <textarea id="promptInput" rows="3" placeholder="Type here to chat live..."></textarea>
    <div class="btn-row">
      <button id="askBtn" onclick="askLive()">Ask Gelo</button>
      <button class="btn-green" onclick="readAloud()">🗣️ Read</button>
    </div>
    <div id="aiOutput" class="output"></div>
  </div>

  <!-- Audio & Media Recognition -->
  <div class="card">
    <div class="card-title">🎵 Audio & Media Recognition</div>
    <button id="micBtn" onclick="startAudioCapture()">Identify Music (6s)</button>
    <div id="audioOutput" class="output"></div>
  </div>

  <script>
    async function askLive() {
      const prompt = document.getElementById('promptInput').value.trim();
      const output = document.getElementById('aiOutput');
      const askBtn = document.getElementById('askBtn');
      if (!prompt) return;

      output.innerText = "";
      output.className = "output cursor";
      askBtn.disabled = true;

      try {
        const response = await fetch('/stream', {
          method: 'POST',
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify({ prompt })
        });

        const reader = response.body.getReader();
        const decoder = new TextDecoder('utf-8');

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;
          output.innerText += decoder.decode(value, { stream: true });
        }
      } catch (err) {
        output.innerText = "Connection error: " + err.message;
        output.className = "output error";
      } finally {
        output.className = "output";
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

    async function startAudioCapture() {
      const btn = document.getElementById('micBtn');
      const out = document.getElementById('audioOutput');
      out.className = "output";
      try {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        const mediaRecorder = new MediaRecorder(stream);
        const audioChunks = [];
        
        mediaRecorder.ondataavailable = e => audioChunks.push(e.data);
        mediaRecorder.onstop = async () => {
          out.innerText = "Identifying music...";
          const audioBlob = new Blob(audioChunks, { type: 'audio/webm' });
          const formData = new FormData();
          formData.append('file', audioBlob);

          try {
            const res = await fetch('/identify', { method: 'POST', body: formData });
            const data = await res.json();
            if (data.result) {
              out.innerText = `🎵 ${data.result.title} — ${data.result.artist}`;
            } else {
              out.innerText = "No song identified.";
              out.className = "output error";
            }
          } catch (e) {
            out.innerText = "Recognition error: " + e.message;
            out.className = "output error";
          }
          btn.disabled = false;
          btn.innerText = "Identify Music (6s)";
        };

        mediaRecorder.start();
        btn.disabled = true;
        let count = 6;
        btn.innerText = `Listening (${count}s)...`;
        const interval = setInterval(() => {
          count--;
          if (count > 0) {
            btn.innerText = `Listening (${count}s)...`;
          } else {
            clearInterval(interval);
            mediaRecorder.stop();
            stream.getTracks().forEach(t => t.stop());
          }
        }, 1000);
      } catch (err) {
        out.innerText = "Microphone error: " + err.message;
        out.className = "output error";
      }
    }
  </script>
</body>
</html>
"""

@app.route("/")
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route("/stream", methods=["POST"])
def stream_ai():
    prompt = request.json.get("prompt", "")
    if not prompt:
        return "Please provide a prompt.", 400

    def generate():
        model = get_active_model()
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:streamGenerateContent?alt=sse&key={GEMINI_API_KEY}"
        payload = {"contents": [{"parts": [{"text": prompt}]}]}
        
        try:
            with requests.post(url, json=payload, stream=True, timeout=60) as resp:
                for line in resp.iter_lines():
                    if line:
                        decoded = line.decode('utf-8')
                        if decoded.startswith("data: "):
                            data_str = decoded[6:]
                            try:
                                chunk = json.loads(data_str)
                                candidates = chunk.get("candidates", [])
                                if candidates:
                                    part = candidates[0].get("content", {}).get("parts", [{}])[0]
                                    text = part.get("text", "")
                                    if text:
                                        yield text
                            except Exception:
                                continue
        except Exception as e:
            yield f" [Stream Error: {str(e)}]"

    return Response(stream_with_context(generate()), mimetype="text/plain")

@app.route("/identify", methods=["POST"])
def identify():
    if "file" not in request.files:
        return jsonify({"error": "Missing audio file"}), 400
    file = request.files["file"]
    data = {"api_token": AUDD_API_KEY, "return": "apple_music,spotify"}
    try:
        res = requests.post("https://api.audd.io/", data=data, files={"file": file.read()}, timeout=25)
        return jsonify(res.json())
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
