from flask import Flask, request, jsonify, render_template_string, send_from_directory
import os
import re
import threading
import uuid
import shutil
import yt_dlp

app = Flask(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DOWNLOAD_DIR = os.path.join(BASE_DIR, "downloads")
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

tasks = {}

HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Video Downloader</title>
  <style>
    :root{
      --bg1:#09101d;
      --bg2:#121b31;
      --card:rgba(255,255,255,.08);
      --border:rgba(255,255,255,.12);
      --text:#f4f7fb;
      --muted:#aeb8cc;
      --accent:#7c9cff;
      --accent2:#74f0c2;
      --danger:#ff8e8e;
      --success:#8df5a8;
      --shadow:0 22px 50px rgba(0,0,0,.35);
      --radius:24px;
    }

    *{box-sizing:border-box}

    body{
      margin:0;
      min-height:100vh;
      font-family:Inter,Segoe UI,Arial,sans-serif;
      color:var(--text);
      background:
        radial-gradient(circle at top left, rgba(124,156,255,.22), transparent 28%),
        radial-gradient(circle at bottom right, rgba(116,240,194,.15), transparent 22%),
        linear-gradient(135deg, var(--bg1), var(--bg2));
      display:flex;
      align-items:center;
      justify-content:center;
      padding:20px;
    }

    .wrap{
      width:100%;
      max-width:780px;
    }

    .card{
      background:var(--card);
      border:1px solid var(--border);
      border-radius:var(--radius);
      backdrop-filter: blur(18px);
      -webkit-backdrop-filter: blur(18px);
      box-shadow:var(--shadow);
      padding:28px;
    }

    h1{
      margin:0 0 10px;
      font-size:clamp(30px,5vw,48px);
      line-height:1.05;
    }

    .sub{
      color:var(--muted);
      font-size:15px;
      line-height:1.7;
      margin-bottom:22px;
    }

    .field{margin-bottom:16px}

    label{
      display:block;
      margin-bottom:8px;
      font-size:14px;
      font-weight:700;
      color:#dfe7f7;
    }

    input, select{
      width:100%;
      padding:15px 16px;
      border-radius:16px;
      border:1px solid rgba(255,255,255,.1);
      background:rgba(255,255,255,.05);
      color:var(--text);
      outline:none;
      font-size:15px;
    }

    input:focus, select:focus{
      border-color:rgba(124,156,255,.7);
      box-shadow:0 0 0 4px rgba(124,156,255,.12);
    }

    .row{
      display:grid;
      grid-template-columns:1fr 1fr;
      gap:14px;
    }

    .btn{
      width:100%;
      border:0;
      border-radius:16px;
      padding:15px 18px;
      font-size:15px;
      font-weight:800;
      cursor:pointer;
      text-decoration:none;
      display:inline-flex;
      align-items:center;
      justify-content:center;
      background:linear-gradient(135deg, var(--accent), #9c7cff);
      color:white;
      transition:transform .15s ease, opacity .15s ease;
    }

    .btn:hover{transform:translateY(-1px)}
    .btn:active{transform:translateY(0)}

    .btn-secondary{
      margin-top:12px;
      background:var(--accent2);
      color:#08111d;
      display:none;
    }

    .status{
      margin-top:18px;
      padding:16px;
      border-radius:18px;
      background:rgba(255,255,255,.04);
      border:1px solid rgba(255,255,255,.08);
      display:none;
    }

    .status.show{display:block}

    .status-title{
      font-size:14px;
      font-weight:800;
      margin-bottom:10px;
    }

    .status-text{
      color:var(--muted);
      font-size:14px;
      line-height:1.65;
      word-break:break-word;
    }

    .bar-wrap{
      width:100%;
      height:10px;
      background:rgba(255,255,255,.08);
      border-radius:999px;
      overflow:hidden;
      margin:14px 0 8px;
    }

    .bar{
      height:100%;
      width:0%;
      border-radius:999px;
      background:linear-gradient(90deg, var(--accent2), var(--accent));
      transition:width .25s ease;
    }

    .note{
      margin-top:14px;
      font-size:12px;
      color:var(--muted);
      line-height:1.7;
    }

    .success{color:var(--success)}
    .error{color:var(--danger)}

    @media (max-width:560px){
      .row{grid-template-columns:1fr}
      .card{padding:22px}
    }
  </style>
</head>
<body>
  <div class="wrap">
    <div class="card">
      <h1>Video Downloader</h1>
      <div class="sub">
        Paste a supported link, choose quality, then download on PC or mobile.
      </div>

      <form id="downloadForm">
        <div class="field">
          <label for="videoUrl">Video URL</label>
          <input id="videoUrl" name="url" type="url" placeholder="Paste video URL here" required />
        </div>

        <div class="row">
          <div class="field">
            <label for="quality">Quality</label>
            <select id="quality" name="quality">
              <option value="best">Best available</option>
              <option value="1080">1080p</option>
              <option value="720">720p</option>
              <option value="480">480p</option>
              <option value="360">360p</option>
              <option value="audio">Audio only (mp3)</option>
            </select>
          </div>

          <div class="field">
            <label for="deviceType">Device</label>
            <select id="deviceType" name="device_type">
              <option value="pc">PC / Laptop</option>
              <option value="mobile">Mobile</option>
            </select>
          </div>
        </div>

        <button class="btn" type="submit" id="submitBtn">Download Now</button>
      </form>

      <div class="status" id="statusBox">
        <div class="status-title" id="statusTitle">Preparing...</div>
        <div class="bar-wrap"><div class="bar" id="progressBar"></div></div>
        <div class="status-text" id="statusText">Waiting for server response.</div>
        <a id="finalDownloadBtn" class="btn btn-secondary" href="#">Save File</a>
      </div>

      <div class="note">
        On mobile, the final button downloads through the browser. Most phones save it in Downloads, and many show it in Gallery automatically.
      </div>
    </div>
  </div>

<script>
  const form = document.getElementById("downloadForm");
  const statusBox = document.getElementById("statusBox");
  const statusTitle = document.getElementById("statusTitle");
  const statusText = document.getElementById("statusText");
  const progressBar = document.getElementById("progressBar");
  const submitBtn = document.getElementById("submitBtn");
  const finalDownloadBtn = document.getElementById("finalDownloadBtn");

  let poller = null;

  function showStatus(title, text, progress=0) {
    statusBox.classList.add("show");
    statusTitle.textContent = title;
    statusText.innerHTML = text;
    progressBar.style.width = progress + "%";
  }

  async function pollTask(taskId) {
    poller = setInterval(async () => {
      try {
        const res = await fetch(`/status/${taskId}`);
        const data = await res.json();

        if (!res.ok) {
          showStatus("Server error", `<span class="error">${data.message || "Could not read task status."}</span>`, 100);
          clearInterval(poller);
          submitBtn.disabled = false;
          submitBtn.style.opacity = "1";
          return;
        }

        if (data.status === "queued" || data.status === "starting" || data.status === "processing") {
          showStatus("Preparing...", data.message || "Preparing...", data.progress || 5);
        } else if (data.status === "downloading") {
          showStatus("Downloading...", data.message || "Downloading...", data.progress || 0);
        } else if (data.status === "finished") {
          showStatus("Download complete", `<span class="success">${data.message}</span>`, 100);
          if (data.file_url) {
            finalDownloadBtn.href = data.file_url;
            finalDownloadBtn.style.display = "inline-flex";
            finalDownloadBtn.textContent = data.device_type === "mobile" ? "Save to Mobile" : "Save to PC";
          }
          clearInterval(poller);
          submitBtn.disabled = false;
          submitBtn.style.opacity = "1";
        } else if (data.status === "error") {
          showStatus("Download failed", `<span class="error">${data.message}</span>`, 100);
          finalDownloadBtn.style.display = "none";
          clearInterval(poller);
          submitBtn.disabled = false;
          submitBtn.style.opacity = "1";
        }
      } catch (e) {
        showStatus("Server error", `<span class="error">Could not read task status.</span>`, 100);
        clearInterval(poller);
        submitBtn.disabled = false;
        submitBtn.style.opacity = "1";
      }
    }, 1500);
  }

  form.addEventListener("submit", async (e) => {
    e.preventDefault();

    if (poller) clearInterval(poller);

    finalDownloadBtn.style.display = "none";
    finalDownloadBtn.href = "#";

    submitBtn.disabled = true;
    submitBtn.style.opacity = "0.7";

    const payload = {
      url: document.getElementById("videoUrl").value.trim(),
      quality: document.getElementById("quality").value,
      device_type: document.getElementById("deviceType").value
    };

    showStatus("Preparing...", "Creating task...", 8);

    try {
      const res = await fetch("/download", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify(payload)
      });

      const data = await res.json();

      if (!res.ok) {
        showStatus("Request failed", `<span class="error">${data.error || "Something went wrong."}</span>`, 100);
        submitBtn.disabled = false;
        submitBtn.style.opacity = "1";
        return;
      }

      showStatus("Starting...", "Download started. Please wait...", 12);
      pollTask(data.task_id);

    } catch (err) {
      showStatus("Server error", `<span class="error">Unable to connect to the server.</span>`, 100);
      submitBtn.disabled = false;
      submitBtn.style.opacity = "1";
    }
  });
</script>
</body>
</html>
"""

def clean_filename(name: str) -> str:
    name = re.sub(r'[\\\\/:*?"<>|]+', '', name)
    name = re.sub(r'[^\w\s.-]', '', name)
    name = re.sub(r'\s+', ' ', name).strip()
    return name[:150] if name else "video"

def unique_filename(base_name: str, ext: str) -> str:
    filename = f"{base_name}.{ext}"
    path = os.path.join(DOWNLOAD_DIR, filename)
    counter = 1
    while os.path.exists(path):
        filename = f"{base_name}_{counter}.{ext}"
        path = os.path.join(DOWNLOAD_DIR, filename)
        counter += 1
    return filename

def format_selector(quality: str, ffmpeg_ready: bool) -> str:
    if quality == "audio":
        return "bestaudio/best"

    if ffmpeg_ready:
        if quality == "1080":
            return "bestvideo[height<=1080]+bestaudio/best[height<=1080]/best"
        if quality == "720":
            return "bestvideo[height<=720]+bestaudio/best[height<=720]/best"
        if quality == "480":
            return "bestvideo[height<=480]+bestaudio/best[height<=480]/best"
        if quality == "360":
            return "bestvideo[height<=360]+bestaudio/best[height<=360]/best"
        return "bestvideo+bestaudio/best"

    if quality == "1080":
        return "best[height<=1080]/best"
    if quality == "720":
        return "best[height<=720]/best"
    if quality == "480":
        return "best[height<=480]/best"
    if quality == "360":
        return "best[height<=360]/best"
    return "best"

def normalize_error_message(error_text: str) -> str:
    lower = error_text.lower()

    if "sign in to confirm you’re not a bot" in lower or "sign in to confirm you're not a bot" in lower:
        return "YouTube blocked this request on the hosting server. Public cloud servers are often flagged. Try this link locally on your own PC."

    if "rate-limit reached" in lower or "login required" in lower:
        return "This platform blocked the request or requires login. Public hosting servers are often restricted for Instagram and similar sites."

    if "requested content is not available" in lower:
        return "The video is unavailable from this server, or the platform blocked access."

    if "ffmpeg is not installed" in lower:
        return "FFmpeg is missing on the server. Install FFmpeg for merged video/audio downloads."

    return error_text

def progress_hook_factory(task_id):
    def hook(d):
        if task_id not in tasks:
            return

        if d["status"] == "downloading":
            percent_str = (d.get("_percent_str") or "0%").replace("%", "").strip()
            try:
                percent = float(percent_str)
            except Exception:
                percent = 0.0

            speed = d.get("_speed_str", "")
            eta = d.get("_eta_str", "")
            msg = (d.get("_percent_str", "").strip() or "Downloading...")

            if speed:
                msg += f" • Speed: {speed}"
            if eta:
                msg += f" • ETA: {eta}"

            tasks[task_id]["status"] = "downloading"
            tasks[task_id]["progress"] = max(1, min(99, int(percent)))
            tasks[task_id]["message"] = msg

        elif d["status"] == "finished":
            tasks[task_id]["status"] = "processing"
            tasks[task_id]["progress"] = 99
            tasks[task_id]["message"] = "Download finished. Finalizing file..."
    return hook

def do_download(task_id, url, quality, device_type):
    try:
        ffmpeg_ready = shutil.which("ffmpeg") is not None

        tasks[task_id] = {
            "status": "starting",
            "progress": 5,
            "message": "Starting download...",
            "file_url": None,
            "device_type": device_type,
            "filename": None
        }

        selector = format_selector(quality, ffmpeg_ready)
        temp_id = str(uuid.uuid4())[:8]
        temp_template = os.path.join(DOWNLOAD_DIR, f"{temp_id}_%(title).150s.%(ext)s")

        ydl_opts = {
            "format": selector,
            "outtmpl": temp_template,
            "noplaylist": True,
            "quiet": True,
            "no_warnings": True,
            "progress_hooks": [progress_hook_factory(task_id)],
            "windowsfilenames": True,
            "restrictfilenames": False,
            "socket_timeout": 30,
        }

        if ffmpeg_ready:
            ydl_opts["merge_output_format"] = "mp4"

        if quality == "audio":
            if not ffmpeg_ready:
                raise Exception("FFmpeg is required for audio conversion.")
            ydl_opts["postprocessors"] = [{
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "192",
            }]

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.extract_info(url, download=True)

        downloaded_files = []
        for item in os.listdir(DOWNLOAD_DIR):
            if item.startswith(f"{temp_id}_"):
                downloaded_files.append(item)

        if not downloaded_files:
            raise Exception("Downloaded file was not found.")

        downloaded_files.sort(
            key=lambda name: os.path.getsize(os.path.join(DOWNLOAD_DIR, name)),
            reverse=True
        )

        source_name = downloaded_files[0]
        source_path = os.path.join(DOWNLOAD_DIR, source_name)

        name_without_prefix = source_name[len(temp_id) + 1:] if source_name.startswith(f"{temp_id}_") else source_name
        base_name, ext = os.path.splitext(name_without_prefix)

        clean_base = clean_filename(base_name)
        real_ext = ext.lower().lstrip(".")

        if not real_ext:
            real_ext = "mp3" if quality == "audio" else "mp4"

        final_filename = unique_filename(clean_base, real_ext)
        final_path = os.path.join(DOWNLOAD_DIR, final_filename)

        os.replace(source_path, final_path)

        for extra in downloaded_files[1:]:
            extra_path = os.path.join(DOWNLOAD_DIR, extra)
            if os.path.exists(extra_path):
                try:
                    os.remove(extra_path)
                except Exception:
                    pass

        tasks[task_id]["status"] = "finished"
        tasks[task_id]["progress"] = 100
        tasks[task_id]["message"] = "File is ready. Tap the button below to save it."
        tasks[task_id]["file_url"] = f"/download_file/{final_filename}"
        tasks[task_id]["device_type"] = device_type
        tasks[task_id]["filename"] = final_filename

    except Exception as e:
        tasks[task_id]["status"] = "error"
        tasks[task_id]["progress"] = 100
        tasks[task_id]["message"] = normalize_error_message(str(e))
        tasks[task_id]["file_url"] = None
        tasks[task_id]["device_type"] = device_type
        tasks[task_id]["filename"] = None

@app.route("/")
def home():
    return render_template_string(HTML)

@app.route("/download", methods=["POST"])
def download():
    data = request.get_json(silent=True) or {}
    url = (data.get("url") or "").strip()
    quality = (data.get("quality") or "best").strip()
    device_type = (data.get("device_type") or "pc").strip().lower()

    if not url:
        return jsonify({"error": "Please enter a video URL."}), 400

    if not (url.startswith("http://") or url.startswith("https://")):
        return jsonify({"error": "Please enter a valid URL starting with http:// or https://"}), 400

    if device_type not in ["pc", "mobile"]:
        device_type = "pc"

    task_id = str(uuid.uuid4())

    tasks[task_id] = {
        "status": "queued",
        "progress": 1,
        "message": "Task created...",
        "file_url": None,
        "device_type": device_type,
        "filename": None
    }

    thread = threading.Thread(target=do_download, args=(task_id, url, quality, device_type), daemon=True)
    thread.start()

    return jsonify({
        "message": "Download started.",
        "task_id": task_id
    })

@app.route("/status/<task_id>")
def status(task_id):
    task = tasks.get(task_id)
    if not task:
        return jsonify({
            "status": "error",
            "progress": 100,
            "message": "Task not found.",
            "file_url": None,
            "device_type": "pc",
            "filename": None
        }), 404
    return jsonify(task)

@app.route("/download_file/<path:filename>")
def download_file(filename):
    safe_name = os.path.basename(filename)
    full_path = os.path.join(DOWNLOAD_DIR, safe_name)

    if not os.path.exists(full_path):
        return jsonify({
            "error": "File not found on server.",
            "requested_file": safe_name
        }), 404

    return send_from_directory(DOWNLOAD_DIR, safe_name, as_attachment=True)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)