import os
import requests
from flask import Flask, request, jsonify, render_template_string

app = Flask(__name__)

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
AUDD_API_KEY = os.getenv("AUDD_API_KEY", "test").strip()

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Hello Gelo Live</title>
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
    textarea {
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
    .error {
      color: #f85149;
    }
  </style>
</head>
<body>

  <div class="header">⚡ Hello Gelo Live</div>

  <div class="card">
    <div class="card-title">💬 Conversational Brain</div>
    <textarea id="promptInput" rows="3" placeholder="Ask me anything...">Hello</textarea>
    <div class="btn-row">
      <button id="askBtn" onclick="askLive()">Ask Gelo</button>
      <button class="btn-green" onclick="readAloud()">🗣️ Read</button>
    </div>
    <div id="aiOutput" class="output"></div>
  </div>

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

      output.innerText = "Thinking...";
      output.className = "output";
      askBtn.disabled = true;

      try {
        const response = await fetch('/ask', {
          method: 'POST',
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify({ prompt })
        });
        const data = await response.json();
        if (data.answer) {
          output.innerText = data.answer;
        } else {
          output.innerText = data.error || "No response received.";
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
          out.innerText = "Processing audio...";
          const audioBlob = new Blob(audioChunks, { type: 'audio/webm' });
          const formData = new FormData();
          formData.append('file', audioBlob);

          try {
            const res = await fetch('/identify', { method: 'POST', body: formData });
            const data = await res.json();
            if (data.result && data.result.title) {
              out.innerText = `🎵 ${data.result.title} — ${data.result.artist}`;
            } else if (data.error) {
              out.innerText = "AudD: " + (data.error.error_message || JSON.stringify(data.error));
              out.className = "output error";
            } else {
              out.innerText = "No match found. Hold closer to the speaker.";
              out.className = "output error";
            }
          } catch (e) {
            out.innerText = "Error: " + e.message;
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

@app.route("/ask", methods=["POST"])
def ask():
    prompt = request.json.get("prompt", "")
    if not prompt:
        return jsonify({"error": "Empty prompt"}), 400
    if not GEMINI_API_KEY:
        return jsonify({"error": "GEMINI_API_KEY missing in Render environment."}), 500

    headers = {
        "Content-Type": "application/json",
        "x-goog-api-key": GEMINI_API_KEY
    }
    payload = {"contents": [{"parts": [{"text": prompt}]}]}

    for model in ["gemini-1.5-flash", "gemini-2.0-flash", "gemini-1.5-pro"]:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
        try:
            res = requests.post(url, headers=headers, json=payload, timeout=20)
            data = res.json()
            if "candidates" in data and data["candidates"]:
                text = data["candidates"][0]["content"]["parts"][0]["text"]
                return jsonify({"answer": text})
            elif "error" in data:
                err_msg = data["error"].get("message", "")
                if "not found" not in err_msg.lower():
                    return jsonify({"error": f"Gemini Error: {err_msg}"}), 400
        except Exception as e:
            continue

    return jsonify({"error": "All model endpoints failed. Check API key permissions."}), 500

@app.route("/identify", methods=["POST"])
def identify():
    if "file" not in request.files:
        return jsonify({"error": {"error_message": "Missing audio file"}}), 400
    file = request.files["file"]
    token = AUDD_API_KEY if AUDD_API_KEY else "test"
    data = {"api_token": token, "return": "apple_music,spotify"}
    try:
        res = requests.post("https://api.audd.io/", data=data, files={"file": file.read()}, timeout=25)
        return jsonify(res.json())
    except Exception as e:
        return jsonify({"error": {"error_message": str(e)}}), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
