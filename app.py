import os
import requests
from flask import Flask, request, jsonify, render_template_string

app = Flask(__name__)

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
AUDD_API_KEY = os.getenv("AUDD_API_KEY", "")

def get_active_model() -> str:
    """Fetch the first active model that supports generateContent."""
    if not GEMINI_API_KEY:
        return "gemini-2.5-flash"
    try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models?key={GEMINI_API_KEY}"
        res = requests.get(url, timeout=10).json()
        if "models" in res:
            for m in res["models"]:
                methods = m.get("supportedGenerationMethods", [])
                name = m.get("name", "").replace("models/", "")
                if "generateContent" in methods and "flash" in name:
                    return name
            for m in res["models"]:
                methods = m.get("supportedGenerationMethods", [])
                if "generateContent" in methods:
                    return m.get("name", "").replace("models/", "")
    except Exception:
        pass
    return "gemini-2.5-flash"

def call_gemini(prompt: str) -> str:
    if not GEMINI_API_KEY:
        return "Gemini API key is missing. Please set GEMINI_API_KEY in Render environment variables."
    
    primary_model = get_active_model()
    fallback_models = [primary_model, "gemini-2.5-flash", "gemini-3.6-flash", "gemini-1.5-flash"]
    # Preserve order while deduplicating
    models_to_try = list(dict.fromkeys(fallback_models))
    
    last_err = ""
    for model in models_to_try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={GEMINI_API_KEY}"
        payload = {"contents": [{"parts": [{"text": prompt}]}]}
        try:
            res = requests.post(url, json=payload, timeout=25).json()
            if "candidates" in res and res["candidates"]:
                return res["candidates"][0]["content"]["parts"][0]["text"]
            elif "error" in res:
                last_err = res["error"].get("message", "")
                continue
        except Exception as e:
            last_err = str(e)
            continue
            
    return f"Gemini Error: {last_err or 'No responsive model found.'}"

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Hello Gelo</title>
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
      background: #238636;
      border: none;
      color: #fff;
      padding: 10px 14px;
      border-radius: 8px;
      font-size: 14px;
      font-weight: 600;
      cursor: pointer;
    }
    button.btn-blue {
      background: #1f6feb;
    }
    button:disabled {
      opacity: 0.5;
    }
    .output {
      margin-top: 10px;
      font-size: 13px;
      color: #8b949e;
      white-space: pre-wrap;
      word-break: break-word;
    }
    .error {
      color: #f85149;
    }
    .inputs-grid {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 8px;
    }
  </style>
</head>
<body>

  <div class="header">⚡ Hello Gelo</div>

  <!-- Conversational Brain -->
  <div class="card">
    <div class="card-title">💬 Conversational Brain</div>
    <textarea id="promptInput" rows="3" placeholder="Ask me anything..."></textarea>
    <div class="btn-row">
      <button class="btn-blue" onclick="askGelo()">Ask Gelo</button>
      <button onclick="readAloud()">🗣️ Read Aloud</button>
    </div>
    <div id="aiOutput" class="output"></div>
  </div>

  <!-- Audio & Media Recognition -->
  <div class="card">
    <div class="card-title">🎵 Audio & Media Recognition</div>
    <button class="btn-blue" id="micBtn" onclick="startAudioCapture()">Identify Music (6s)</button>
    <div id="audioOutput" class="output"></div>
  </div>

  <!-- Pattern Analysis -->
  <div class="card">
    <div class="card-title">⚙️ Pattern Analysis</div>
    <div class="inputs-grid">
      <input type="number" id="paramA" value="15" placeholder="Value A">
      <input type="number" id="paramB" value="1.5" placeholder="Value B">
    </div>
    <button class="btn-blue" onclick="analyzePattern()">Analyze Pattern</button>
    <div id="patternOutput" class="output"></div>
  </div>

  <script>
    async function askGelo() {
      const prompt = document.getElementById('promptInput').value.trim();
      const output = document.getElementById('aiOutput');
      if (!prompt) return;
      output.innerText = "Thinking...";
      output.className = "output";
      try {
        const res = await fetch('/ask', {
          method: 'POST',
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify({ prompt })
        });
        const data = await res.json();
        output.innerText = data.answer || data.error;
        if (data.error) output.className = "output error";
      } catch (err) {
        output.innerText = "Error: " + err.message;
        output.className = "output error";
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
              out.innerText = "No clear song detected. Move closer to the speaker.";
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

    function analyzePattern() {
      const a = parseFloat(document.getElementById('paramA').value) || 0;
      const b = parseFloat(document.getElementById('paramB').value) || 0;
      const res = ((a * b) / 10).toFixed(2);
      document.getElementById('patternOutput').innerText = `Calculated Index: ${res} | Volatility Normal`;
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
    answer = call_gemini(prompt)
    return jsonify({"answer": answer})

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
