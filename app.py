import os
import requests
from flask import Flask, request, jsonify, render_template_string

app = Flask(__name__)

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
AUDD_API_KEY = os.getenv("AUDD_API_KEY", "").strip()

# Models tried in sequence if quota or traffic limits are reached
MODELS_TO_TRY = [
    "gemini-3.6-flash",
    "gemini-1.5-pro",
    "gemini-2.5-pro",
    "gemini-pro"
]

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>HELLO Gelo</title>
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
      flex-wrap: wrap;
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
    button.btn-gray {
      background: #30363d;
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
      <button id="askBtn" onclick="askAi()">Ask Gelo</button>
      <button class="btn-green" onclick="readAloud()">🗣️ Read</button>
    </div>
    <div id="aiOutput" class="output"></div>
  </div>

  <div class="card">
    <div class="card-title">🎵 Audio & Media Recognition</div>
    <div class="btn-row">
      <button id="micBtn" onclick="recordAudio()">Identify Music (7s)</button>
      <button class="btn-gray" onclick="document.getElementById('filePicker').click()">Choose Audio File</button>
    </div>
    <input type="file" id="filePicker" accept="audio/*" onchange="uploadAudioFile(this.files[0])">
    <div id="audioOutput" class="output"></div>
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

    async function uploadAudioFile(file) {
      if (!file) return;
      const out = document.getElementById('audioOutput');
      out.innerText = "Identifying audio via AudD...";
      out.className = "output";

      const formData = new FormData();
      formData.append('file', file);

      try {
        const res = await fetch('/identify', { method: 'POST', body: formData });
        const data = await res.json();
        if (data.result && data.result.title) {
          out.innerText = "🎵 " + data.result.title + " — " + data.result.artist;
        } else if (data.error) {
          out.innerText = "AudD Error: " + (data.error.error_message || JSON.stringify(data.error));
          out.className = "output error";
        } else {
          out.innerText = "No exact match found.";
          out.className = "output error";
        }
      } catch (e) {
        out.innerText = "Upload error: " + e.message;
        out.className = "output error";
      }
    }

    async function recordAudio() {
      const btn = document.getElementById('micBtn');
      const out = document.getElementById('audioOutput');
      out.className = "output";

      try {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        const mediaRecorder = new MediaRecorder(stream);
        const audioChunks = [];

        mediaRecorder.ondataavailable = e => {
          if (e.data && e.data.size > 0) audioChunks.push(e.data);
        };

        mediaRecorder.onstop = () => {
          const audioBlob = new Blob(audioChunks, { type: mediaRecorder.mimeType || 'audio/webm' });
          uploadAudioFile(audioBlob);
          btn.disabled = false;
          btn.innerText = "Identify Music (7s)";
        };

        mediaRecorder.start(250);
        btn.disabled = true;
        let count = 7;
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
        out.innerText = "Mic Error: " + err.message + ". Tap 'Choose Audio File' to select a recorded clip instead.";
        out.className = "output error";
        btn.disabled = false;
        btn.innerText = "Identify Music (7s)";
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
        return jsonify({"error": "GEMINI_API_KEY missing on Render."}), 500

    headers = {
        "Content-Type": "application/json",
        "x-goog-api-key": GEMINI_API_KEY
    }
    payload = {"contents": [{"parts": [{"text": prompt}]}]}

    last_error = ""
    for model in MODELS_TO_TRY:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
        try:
            res = requests.post(url, headers=headers, json=payload, timeout=20)
            data = res.json()
            if "candidates" in data and data["candidates"]:
                text = data["candidates"][0]["content"]["parts"][0]["text"]
                return jsonify({"answer": text})
            elif "error" in data:
                err_msg = data["error"].get("message", "")
                last_error = err_msg
                # If rate-limited/quota exceeded, immediately fall through to the next model
                if "quota" in err_msg.lower() or "limit" in err_msg.lower() or "demand" in err_msg.lower():
                    continue
                else:
                    continue
        except Exception as e:
            last_error = str(e)
            continue

    return jsonify({"error": f"Quota limit reached across fallback models. Please wait 60 seconds: {last_error}"}), 429

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
