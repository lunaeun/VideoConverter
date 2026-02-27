"""
🎬 Video Downloader & Converter - 로컬 WebUI 서버
파이프라인: yt-dlp(720p) → FFmpeg(1080p) → HandBrakeCLI(코덱변환)
"""

import os
import sys
import uuid
import subprocess
import threading
import shutil
import time
import glob
from datetime import datetime
from flask import Flask, render_template, request, jsonify, send_file

app = Flask(__name__)

# ═══════════════════════════════════════
# 설정
# ═══════════════════════════════════════
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DOWNLOAD_DIR = os.path.join(BASE_DIR, "downloads")
CONVERTED_DIR = os.path.join(BASE_DIR, "converted")
FINAL_DIR = os.path.join(BASE_DIR, "final")
TOOLS_DIR = os.path.join(BASE_DIR, "tools")

for d in [DOWNLOAD_DIR, CONVERTED_DIR, FINAL_DIR]:
    os.makedirs(d, exist_ok=True)

# tools 폴더 내 바이너리도 PATH에 추가
if os.path.exists(TOOLS_DIR):
    for root, dirs, files in os.walk(TOOLS_DIR):
        if any(f.startswith("ffmpeg") or f.startswith("HandBrakeCLI") for f in files):
            os.environ["PATH"] = root + os.pathsep + os.environ.get("PATH", "")

# 작업 상태
tasks = {}
MAX_DURATION = 600  # 최대 10분


def find_tool(name):
    """도구 경로 찾기 (시스템 PATH + tools 폴더)"""
    path = shutil.which(name)
    if path:
        return path
    # tools 폴더에서 검색
    if os.path.exists(TOOLS_DIR):
        for root, dirs, files in os.walk(TOOLS_DIR):
            for f in files:
                if f.lower().startswith(name.lower()):
                    return os.path.join(root, f)
    return name  # fallback


FFMPEG = os.path.join(BASE_DIR, "ffmpeg.exe")
FFPROBE = os.path.join(BASE_DIR, "ffprobe.exe")
HANDBRAKE = os.path.join(BASE_DIR, "HandBrakeCLI.exe")


def update_task(task_id, **kwargs):
    if task_id in tasks:
        tasks[task_id].update(kwargs)
        tasks[task_id]["updated_at"] = datetime.now().isoformat()


def cleanup_old_files(max_age=3600):
    """1시간 이상 지난 파일 정리"""
    now = time.time()
    for d in [DOWNLOAD_DIR, CONVERTED_DIR, FINAL_DIR]:
        for f in glob.glob(os.path.join(d, "*")):
            try:
                if now - os.path.getmtime(f) > max_age:
                    os.remove(f)
            except Exception:
                pass


def get_duration(filepath):
    """영상 길이 (초) 확인"""
    try:
        cmd = [FFPROBE, "-v", "quiet", "-print_format", "json",
               "-show_format", filepath]
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        import json
        info = json.loads(r.stdout)
        return float(info.get("format", {}).get("duration", 0))
    except Exception:
        return 0


def process_video(task_id, url, codec, quality, preset):
    """메인 파이프라인"""
    cleanup_old_files()

    try:
        # ═══════════════════════════════════════
        # STEP 1: yt-dlp 720p 다운로드
        # ═══════════════════════════════════════
        update_task(task_id, step=1, status="downloading",
                    message="720p 동영상 다운로드 중...", progress=0)

        dl_template = os.path.join(DOWNLOAD_DIR, f"{task_id}_720p.%(ext)s")

        cmd1 = [
            sys.executable, "-m", "yt_dlp",
            "-f", "bestvideo[height<=720]+bestaudio/best[height<=720]",
            "--merge-output-format", "mp4",
            "-o", dl_template,
            "--no-playlist",
            "--socket-timeout", "30",
            "--retries", "3",
            "--progress", "--newline",
            url
        ]

        p = subprocess.Popen(cmd1, stdout=subprocess.PIPE,
                             stderr=subprocess.STDOUT, text=True,
                             encoding="utf-8", errors="ignore")

        for line in p.stdout:
            line = line.strip()
            if "[download]" in line and "%" in line:
                try:
                    pct = float(line.split("%")[0].split()[-1])
                    update_task(task_id, progress=pct,
                                message=f"다운로드 중... {pct:.1f}%")
                except (ValueError, IndexError):
                    pass

        p.wait()
        if p.returncode != 0:
            update_task(task_id, status="error",
                        message="다운로드 실패! URL을 확인해주세요.")
            return

        # 다운로드 파일 찾기
        dl_file = None
        for f in os.listdir(DOWNLOAD_DIR):
            if f.startswith(task_id):
                dl_file = os.path.join(DOWNLOAD_DIR, f)
                break

        if not dl_file or not os.path.exists(dl_file):
            update_task(task_id, status="error",
                        message="다운로드 파일을 찾을 수 없습니다.")
            return

        # 영상 길이 체크
        dur = get_duration(dl_file)
        if dur > MAX_DURATION:
            os.remove(dl_file)
            update_task(task_id, status="error",
                        message=f"영상이 너무 깁니다 ({dur:.0f}초). "
                                f"최대 {MAX_DURATION // 60}분까지 허용됩니다.")
            return

        update_task(task_id, step=1, status="downloaded",
                    message="720p 다운로드 완료!", progress=100)

        # ═══════════════════════════════════════
        # STEP 2: FFmpeg 1080p 업스케일
        # ═══════════════════════════════════════
        update_task(task_id, step=2, status="upscaling",
                    message="1080p 업스케일 변환 중...", progress=0)

        up_file = os.path.join(CONVERTED_DIR, f"{task_id}_1080p.mp4")

        cmd2 = [
            FFMPEG, "-i", dl_file,
            "-vf", "scale=1920:1080:flags=lanczos",
            "-c:v", "libx264", "-preset", "medium", "-crf", "18",
            "-c:a", "aac", "-b:a", "192k",
            "-movflags", "+faststart",
            "-y", up_file
        ]

        p = subprocess.Popen(cmd2, stdout=subprocess.PIPE,
                             stderr=subprocess.STDOUT, text=True,
                             encoding="utf-8", errors="ignore")
        for line in p.stdout:
            if "time=" in line:
                update_task(task_id, message="1080p 업스케일 중...")
        p.wait()

        if p.returncode != 0 or not os.path.exists(up_file):
            update_task(task_id, status="error",
                        message="1080p 업스케일 실패!")
            return

        # 다운로드 원본 삭제
        try: os.remove(dl_file)
        except: pass

        update_task(task_id, step=2, status="upscaled",
                    message="1080p 업스케일 완료!", progress=100)

                # ═══════════════════════════════════════
        # STEP 3: HandBrakeCLI 코덱 변환
        # ═══════════════════════════════════════
        update_task(task_id, step=3, status="encoding",
                    message="HandBrake 코덱 변환 중...", progress=0)

        ext_map = {"x264": "mp4", "x265": "mp4", "VP9": "mkv",
                   "VP8": "mkv", "mpeg4": "mp4", "SVT-AV1": "mkv",
                   "theora": "mkv"}
        hb_map = {"x264": "x264", "x265": "x265", "VP9": "VP9",
                  "VP8": "VP8", "mpeg4": "mpeg4", "SVT-AV1": "svt_av1",
                  "theora": "theora"}

        out_ext = ext_map.get(codec, "mp4")
        hb_codec = hb_map.get(codec, "x264")
        final_file = os.path.join(FINAL_DIR, f"{task_id}_final.{out_ext}")

        cmd3 = [
            HANDBRAKE, "-i", up_file, "-o", final_file,
            "-e", hb_codec, "-q", str(quality),
            "--width", "1920", "--height", "1080",
            "-B", "192", "--aencoder", "av_aac",
            "-r", "30", "--optimize"
        ]
        if hb_codec in ["x264", "x265"]:
            cmd3 += ["--encoder-profile", "main", "--encoder-level", "4.1"]

        p = subprocess.Popen(cmd3, stdout=subprocess.PIPE,
                             stderr=subprocess.STDOUT)
        for raw_line in p.stdout:
            try:
                line = raw_line.decode("utf-8", errors="ignore").strip()
            except:
                continue
            if "Encoding:" in line and "%" in line:
                try:
                    pct = float(line.split(",")[0].split()[-2].replace("%", ""))
                    update_task(task_id, progress=pct,
                                message=f"코덱 변환 중... {pct:.1f}%")
                except (ValueError, IndexError):
                    pass
        p.wait()

        if p.returncode != 0 or not os.path.exists(final_file):
            update_task(task_id, status="error",
                        message="HandBrake 변환 실패! HandBrakeCLI 설치를 확인하세요.")
            return

        # 중간 파일 삭제
        try: os.remove(up_file)
        except: pass


        # 완료
        fsize = round(os.path.getsize(final_file) / (1024 * 1024), 2)
        update_task(task_id, step=3, status="completed", progress=100,
                    message=f"모든 변환 완료! ({fsize} MB)",
                    file_size=fsize, final_file=final_file,
                    filename=os.path.basename(final_file))

    except Exception as e:
        update_task(task_id, status="error", message=f"오류: {str(e)}")


# ═══════════════════════════════════════
# 라우트
# ═══════════════════════════════════════

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/check")
def check_tools():
    """도구 설치 상태 확인"""
    def is_ok(name):
        return shutil.which(name) is not None or \
               any(name.lower() in f.lower()
                   for r, d, files in os.walk(TOOLS_DIR)
                   for f in files) if os.path.exists(TOOLS_DIR) else \
               shutil.which(name) is not None

    return jsonify({
        "python": True,
        "ytdlp": True,  # pip으로 설치됨
        "ffmpeg": is_ok("ffmpeg"),
        "handbrake": is_ok("HandBrakeCLI")
    })


@app.route("/api/start", methods=["POST"])
def start_task():
    data = request.get_json()
    url = data.get("url", "").strip()
    codec = data.get("codec", "x265")
    quality = data.get("quality", 22)
    preset = data.get("preset", "medium")

    if not url:
        return jsonify({"error": "URL을 입력해주세요."}), 400
    if not url.startswith(("http://", "https://")):
        return jsonify({"error": "올바른 URL이 아닙니다."}), 400

    quality = max(15, min(35, int(quality)))
    task_id = str(uuid.uuid4())[:8]

    tasks[task_id] = {
        "id": task_id, "url": url, "codec": codec,
        "step": 0, "status": "queued", "message": "준비 중...",
        "progress": 0, "created_at": datetime.now().isoformat()
    }

    t = threading.Thread(target=process_video,
                         args=(task_id, url, codec, quality, preset),
                         daemon=True)
    t.start()
    return jsonify({"task_id": task_id})


@app.route("/api/status/<task_id>")
def task_status(task_id):
    task = tasks.get(task_id)
    if not task:
        return jsonify({"error": "작업을 찾을 수 없습니다."}), 404
    return jsonify(task)


@app.route("/api/download/<task_id>")
def download_file(task_id):
    task = tasks.get(task_id)
    if not task or task.get("status") != "completed":
        return jsonify({"error": "파일이 준비되지 않았습니다."}), 404
    fp = task.get("final_file")
    if not fp or not os.path.exists(fp):
        return jsonify({"error": "파일 없음"}), 404
    return send_file(fp, as_attachment=True,
                     download_name=task.get("filename", "video.mp4"))


if __name__ == "__main__":
    print()
    print("═" * 56)
    print("  🎬 Video Downloader & Converter - 로컬 WebUI")
    print(f"  FFmpeg:      {FFMPEG}")
    print(f"  HandBrake:   {HANDBRAKE}")
    print("  ──────────────────────────────────────────────")
    print("  🌐 http://localhost:5000")
    print("═" * 56)
    print()
    app.run(debug=False, host="127.0.0.1", port=5000)
