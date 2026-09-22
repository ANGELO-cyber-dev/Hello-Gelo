import os
import urllib.parse
import requests
from flask import Flask, request, jsonify, render_template_string

app = Flask(__name__)
API_KEY = os.environ.get("GEMINI_API_KEY", "AQ.Ab8RN6JXBCkvuIQfLF327QuNxlE8iumwjGeK6uX7LuhOmwKJdQ")

CANDIDATE_MODELS = [
    "gemini-1.5-flash",
    "gemini-1.5-pro",
    "gemini-2.0-flash-exp"
]

def call_gemini(prompt: str) -> str:
    last_err = ""
    for model in CANDIDATE_MODELS:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={API_KEY}"
        payload = {"contents": [{"parts": [{"text": prompt}]}]}
        try:
            res = requests.post(url, json=payload, timeout=20).json()
            if "candidates" in res:
                return res["candidates"][0]["content"]["parts"][0]["text"]
            elif "error" in res:
                last_err = res["error"].get("message", "")
                # Skip to next model on high demand, unavailable, or deprecated model messages
                skip_keywords = ["high demand", "unavailable", "no longer available", "not found"]
                if any(k in last_err.lower() for k in skip_keywords) or res["error"].get("code") in [404, 503]:
                    continue
                return f"Gemini Error: {last_err}"
        except Exception as e:
            last_err = str(e)
            continue
    return f"Gemini Error: All model clusters currently busy. ({last_err})"

def recognize_audio_api(file_path):
    try:
        with open(file_path, 'rb') as f:
            res = requests.post(
                'https://api.audd.io/',
                data={'api_token': 'test', 'return': 'apple_music,spotify'},
                files={'file': f},
                timeout=15
            ).json()

        if res.get('status') == 'success' and res.get('result'):
            track = res['result']
            title = track.get('title', 'Unknown')
            artist = track.get('artist', 'Unknown')
            album = track.get('album', '')
            
            stream_link = track.get('song_link')
            spotify_info = track.get('spotify') or {}
            spotify_url = spotify_info.get('external_urls', {}).get('spotify', '')
            
            query = urllib.parse.quote(f"{title} {artist}")
            youtube_url = f"https://www.youtube.com/results?search_query={query}"
            download_url = f"https://www.google.com/search?q={query}+mp3+download"
            
            prompt = f"Give a concise 2-sentence summary of the song '{title}' by '{artist}', including its genre and cultural impact or famous movie placement."
            gemini_insight = call_gemini(prompt)

            return {
                "song": title,
                "artist": artist,
                "album": album,
                "ai_insight": gemini_insight,
                "stream_url": stream_link or spotify_url or youtube_url,
                "youtube_url": youtube_url,
                "download_url": download_url
            }
        else:
            return {"error": "No clear song detected. Move closer to the speaker."}
    except Exception as e:
        return {"error": f"Audio processing error: {str(e)}"}

HTML_PAGE = """
<!DOCTYPE html>
<html>
<head>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <meta name="apple-mobile-web-app-capable" content="yes">
    <meta name="mobile-web-app-capable" content="yes">
    <meta name="theme-color" content="#0f172a">
    <title>Hello Gelo</title>
    <style>
        body { font-family: system-ui, sans-serif; background: #0f172a; color: #f8fafc; padding: 15px; margin: 0; box-sizing: border-box; }
        .container { max-width: 600px; margin: 0 auto; width: 100%; }
        .card { background: #1e293b; border-radius: 12px; padding: 18px; margin-bottom: 15px; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.3); overflow: hidden; }
        h2 { text-align: center; color: #38bdf8; margin-top: 10px; }
        button, .btn-link { 
            background: #2563eb; color: #fff; border: none; padding: 10px 16px; border-radius: 8px; 
            cursor: pointer; font-size: 14px; font-weight: 600; text-decoration: none; display: inline-block; 
            text-align: center;
        }
        button:disabled { background: #475569; }
        .btn-green { background: #059669; }
        .btn-amber { background: #d97706; }
        textarea, input { width: 100%; box-sizing: border-box; padding: 10px; border-radius: 6px; border: 1px solid #475569; background: #0f172a; color: white; margin-bottom: 10px; font-family: inherit; }
        .output { 
            margin-top: 12px; font-size: 14px; background: #0f172a; padding: 12px; 
            border-radius: 8px; white-space: pre-wrap; word-break: break-word; overflow-wrap: anywhere; line-height: 1.5; 
        }
        .meta-tag { color: #38bdf8; font-weight: bold; margin-bottom: 2px; }
        .meta-val { color: #e2e8f0; margin-bottom: 10px; }
        .action-row { display: flex; gap: 8px; flex-wrap: wrap; margin-top: 12px; }
    </style>
</head>
<body>
    <div class="container">
        <h2>⚡ Hello Gelo</h2>

        <div class="card">
            <h3>💬 Conversational Brain</h3>
            <textarea id="chatInput" rows="3" placeholder="Ask me anything..."></textarea>
            <div style="display: flex; gap: 8px;">
                <button onclick="askGemini()">Ask Gelo</button>
                <button class="btn-green" onclick="speakResponse()">🔊 Read Aloud</button>
            </div>
            <div id="chatResult" class="output" style="display:none;"></div>
        </div>

        <div class="card">
            <h3>🎵 Audio & Media Recognition</h3>
            <button id="recBtn" onclick="recordAudio()">Identify Music (6s)</button>
            <div id="audioStatus" style="margin-top:8px; color:#38bdf8;"></div>
            <div id="audioResult" class="output" style="display:none;"></div>
        </div>

        <div class="card">
            <h3>⚙️ Pattern Analysis</h3>
            <div style="display:flex; gap:10px;">
                <input id="val1" type="number" value="15">
                <input id="val2" type="number" value="1.5">
            </div>
            <button onclick="runPredict()">Analyze Pattern</button>
            <div id="mlResult" class="output" style="display:none;"></div>
        </div>
    </div>

    <script>
        let latestAiText = "";

        async function askGemini() {
            const prompt = document.getElementById('chatInput').value;
            if (!prompt) return;
            const resDiv = document.getElementById('chatResult');
            resDiv.style.display = "block";
            resDiv.innerText = "Thinking...";

            const res = await fetch('/api/chat', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ prompt: prompt })
            });
            const data = await res.json();
            latestAiText = data.response;
            resDiv.innerText = latestAiText;
        }

        function speakResponse() {
            if (!latestAiText) return;
            const utterance = new SpeechSynthesisUtterance(latestAiText);
            window.speechSynthesis.speak(utterance);
        }

        async function recordAudio() {
            const btn = document.getElementById('recBtn');
            const status = document.getElementById('audioStatus');
            const result = document.getElementById('audioResult');
            try {
                const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
                const recorder = new MediaRecorder(stream);
                const chunks = [];
                btn.disabled = true;
                status.innerText = "Listening to music (6s)...";
                result.style.display = "none";
                recorder.ondataavailable = e => chunks.push(e.data);
                recorder.onstop = async () => {
                    status.innerText = "Analyzing song and pulling download links...";
                    const blob = new Blob(chunks, { type: 'audio/mp3' });
                    const form = new FormData();
                    form.append("file", blob, "sample.mp3");
                    const res = await fetch('/api/detect-song', { method: 'POST', body: form });
                    const data = await res.json();
                    status.innerText = "";
                    btn.disabled = false;
                    result.style.display = "block";
                    
                    if (data.error) {
                        result.innerHTML = `<div style="color:#ef4444;">${data.error}</div>`;
                    } else {
                        result.innerHTML = `
                            <div class="meta-tag">🎵 Song:</div><div class="meta-val">${data.song}</div>
                            <div class="meta-tag">👤 Artist:</div><div class="meta-val">${data.artist}</div>
                            <div class="meta-tag">💿 Album:</div><div class="meta-val">${data.album || 'N/A'}</div>
                            <div class="meta-tag">💡 AI Insight:</div><div class="meta-val">${data.ai_insight || 'No insight available.'}</div>
                            <div class="action-row">
                                <a href="${data.stream_url}" target="_blank" class="btn-link">🎧 Listen Online</a>
                                <a href="${data.download_url}" target="_blank" class="btn-link btn-amber">⬇️ Download MP3</a>
                                <a href="${data.youtube_url}" target="_blank" class="btn-link btn-green">▶️ YouTube</a>
                            </div>
                        `;
                    }
                };
                recorder.start();
                setTimeout(() => {
                    recorder.stop();
                    stream.getTracks().forEach(t => t.stop());
                }, 6000);
            } catch(e) {
                status.innerText = "Error: Grant microphone permissions in browser.";
                btn.disabled = false;
            }
        }

        async function runPredict() {
            const v1 = parseFloat(document.getElementById('val1').value);
            const v2 = parseFloat(document.getElementById('val2').value);
            const res = await fetch(`/api/predict?val1=${v1}&val2=${v2}`);
            const data = await res.json();
            const result = document.getElementById('mlResult');
            result.style.display = "block";
            result.innerHTML = `
                <div><strong>Inputs:</strong> [${data.input.join(', ')}]</div>
                <div><strong>Score:</strong> ${data.calculated_score}</div>
                <div><strong>Assessment:</strong> ${data.assessment}</div>
            `;
        }
    </script>
</body>
</html>
"""

@app.route("/")
def index():
    return render_template_string(HTML_PAGE)

@app.route("/api/chat", methods=["POST"])
def chat_endpoint():
    data = request.get_json() or {}
    user_prompt = data.get("prompt", "")
    if not user_prompt:
        return jsonify({"response": "Please enter a query."}), 400
    answer = call_gemini(user_prompt)
    return jsonify({"response": answer})

@app.route("/api/detect-song", methods=["POST"])
def detect_song_endpoint():
    audio_file = request.files.get("file")
    if not audio_file:
        return jsonify({"error": "No file uploaded"}), 400
    temp_path = "temp_rec.mp3"
    audio_file.save(temp_path)
    try:
        return jsonify(recognize_audio_api(temp_path))
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)

@app.route("/api/predict", methods=["GET"])
def predict_endpoint():
    try:
        val1 = float(request.args.get("val1", 0))
        val2 = float(request.args.get("val2", 0))
    except ValueError:
        return jsonify({"error": "Invalid numbers"}), 400
    score = (val1 * 0.4) + (val2 * 2.5)
    label = "High Alert / Anomaly" if score > 20 else "Normal / Stable"
    return jsonify({"input": [val1, val2], "calculated_score": round(score, 2), "assessment": label})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
