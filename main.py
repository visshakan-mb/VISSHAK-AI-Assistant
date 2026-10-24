import tkinter as tk
from tkinter import scrolledtext
import threading
import queue
import math
import time
import os
import re
import json
import subprocess
import sys
import random
import wave
import struct
import winsound
import requests
import http.server
import socketserver
import secrets
import sounddevice as sd
import speech_recognition as sr

from datetime import datetime
from urllib.parse import quote_plus

from playwright.sync_api import sync_playwright
from pycaw.pycaw import AudioUtilities


# =========================================================
# VISSHAK // JARVIS-STYLE PERSONAL AI ASSISTANT
# Combined GUI + Voice + Memory + Ollama + YouTube
# =========================================================


# =========================================================
# CONFIGURATION
# =========================================================

MEMORY_FILE = "memory.json"

OLLAMA_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "llama3.2"

WAKE_WORDS = [
    "boss",
    "bosch",
    "bus",
    "mbv",
    "visshak"
]

SAMPLE_RATE = 16000
RECORD_DURATION = 3

YOUTUBE_PROFILE = os.path.abspath(
    "visshak_youtube_profile"
)


# =========================================================
# GLOBAL STATE
# =========================================================

running = True

voice_enabled = True
sound_enabled = True
tts_busy = False

status_value = "INITIALIZING"

animation_angle = 0
pulse_value = 0
scan_offset = 0
particle_angle = 0

STARTUP_FORMATION_SECONDS = 10.0
STARTUP_INTERFACE_SECONDS = 2.0
formation_overlay = None
formation_canvas = None
shutdown_confirmation_pending = False
restart_confirmation_pending = False

recognizer = sr.Recognizer()

command_queue = queue.Queue()

youtube_playwright = None
youtube_context = None
youtube_page = None

youtube_lock = threading.Lock()

# =========================================================
# REMOTE PHONE ACCESS // TAILSCALE
# =========================================================

REMOTE_PORT = 8765

# Safety: Windows auto-start is OFF by default. Set True only if you want it.
ENABLE_AUTOSTART = False
remote_last_response = ""
remote_response_version = 0
remote_response_lock = threading.Lock()
remote_server = None
# A fresh per-run token is injected into the private mobile page.
REMOTE_AUTH_TOKEN = secrets.token_urlsafe(32)


def get_tailscale_ip():
    try:
        tailscale_exe = r"C:\Program Files\Tailscale\tailscale.exe"

        result = subprocess.run(
            [tailscale_exe, "ip", "-4"],
            capture_output=True,
            text=True,
            timeout=5
        )

        ip = result.stdout.strip().splitlines()[0] if result.stdout.strip() else ""

        if re.match(r"^100\.\d+\.\d+\.\d+$", ip):
            return ip

    except Exception as e:
        print("Tailscale IP error:", e)

    return None


REMOTE_HTML = r'''<!DOCTYPE html>
<html>
<head>
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<meta name="theme-color" content="#050611">
<title>VISSHAK // MOBILE CORE</title>
<style>
*{box-sizing:border-box;-webkit-tap-highlight-color:transparent}
body{margin:0;min-height:100vh;background:#02030a;color:#e9fbff;font-family:Arial,sans-serif;display:flex;justify-content:center;padding:14px;overflow-x:hidden}
body:before{content:"";position:fixed;inset:-30%;background:radial-gradient(circle,#18265f 0,rgba(15,12,52,.35) 28%,transparent 62%);animation:drift 8s ease-in-out infinite alternate;pointer-events:none}
@keyframes drift{to{transform:scale(1.15) rotate(5deg)}}
.panel{position:relative;width:min(650px,100%);margin:auto;padding:18px;border:1px solid rgba(0,246,255,.55);border-radius:28px;background:rgba(5,7,20,.88);box-shadow:0 0 45px rgba(0,246,255,.12),inset 0 0 35px rgba(168,85,247,.05);backdrop-filter:blur(16px)}
.top{display:flex;align-items:center;justify-content:space-between;gap:12px;margin-bottom:12px}.brand{display:flex;align-items:center;gap:12px}.core{width:48px;height:48px;border-radius:50%;display:grid;place-items:center;color:#00f6ff;font-weight:900;font-size:20px;border:1px solid #00f6ff;box-shadow:0 0 16px rgba(0,246,255,.45),inset 0 0 15px rgba(0,246,255,.15);animation:pulse 2s infinite}@keyframes pulse{50%{transform:scale(1.06);box-shadow:0 0 28px rgba(0,246,255,.6)}}
h1{margin:0;font-size:24px;letter-spacing:4px;color:#00f6ff}.sub{font-size:10px;letter-spacing:2px;color:#6873ad;margin-top:3px}.status{font-size:10px;letter-spacing:1px;color:#00ff9d;text-align:right}
.chat{height:300px;overflow:auto;padding:15px;border:1px solid #181d50;border-radius:18px;background:rgba(1,2,8,.75);white-space:pre-wrap;font-size:14px;line-height:1.55;scroll-behavior:smooth}
.row{display:flex;gap:8px;margin-top:11px}input{flex:1;min-width:0;background:#0d1030;color:#f2fbff;border:1px solid #2d66c7;border-radius:15px;padding:14px;font-size:16px;outline:none}input:focus{border-color:#00f6ff;box-shadow:0 0 15px rgba(0,246,255,.12)}
button{border:0;border-radius:15px;font-weight:800;font-size:13px;min-height:48px;cursor:pointer}.send{padding:0 17px;background:#00f6ff;color:#02030a}.mic{width:100%;margin-top:10px;padding:14px;background:linear-gradient(90deg,#121b4c,#241143);color:#00f6ff;border:1px solid #8d5cff;box-shadow:0 0 20px rgba(141,92,255,.15)}.mic.listening{background:#103329;color:#00ff9d;border-color:#00ff9d;box-shadow:0 0 24px rgba(0,255,157,.2)}
.controls{display:grid;grid-template-columns:repeat(4,1fr);gap:7px;margin-top:10px}.controls button{background:#0c1634;color:#7defff;border:1px solid #254d8f;padding:11px 4px}.controls button:active,.send:active,.mic:active{transform:scale(.97)}
.voiceHint{text-align:center;color:#6974a8;font-size:11px;margin:7px 0}.footer{text-align:center;color:#46517f;font-size:10px;letter-spacing:1px;margin-top:13px}
@media(max-width:430px){body{padding:9px}.panel{padding:13px;border-radius:22px}.chat{height:270px}.top{align-items:flex-start}.status{font-size:9px}.controls button{font-size:11px}.core{width:43px;height:43px}h1{font-size:21px}}
</style>
</head>
<body>
<div class="panel">
  <div class="top"><div class="brand"><div class="core">V</div><div><h1>VISSHAK</h1><div class="sub">MOBILE COMMAND CORE</div></div></div><div class="status" id="status">● LINK ONLINE</div></div>
  <div class="chat" id="chat">Phone connected to VISSHAK.</div>
  <div class="row"><input id="cmd" placeholder="Command VISSHAK..." autocomplete="off"><button class="send" onclick="sendCommand()">SEND</button></div>
  <button id="micBtn" class="mic" onclick="toggleMic()">🎤 VOICE COMMAND</button>
  <div class="voiceHint" id="voiceHint">Tap once → Allow microphone → speak. BOSS word not needed.</div>
  <div class="controls"><button onclick="quick('pause')">⏸ PAUSE</button><button onclick="quick('resume')">▶ RESUME</button><button onclick="quick('next song')">⏭ NEXT</button><button onclick="quick('previous song')">⏮ PREVIOUS</button></div>
  <div class="footer">PRIVATE TAILSCALE LINK • VISSHAK ONLINE</div>
</div>
<script>
const input=document.getElementById("cmd"),chat=document.getElementById("chat"),statusEl=document.getElementById("status"),micBtn=document.getElementById("micBtn"),voiceHint=document.getElementById("voiceHint");
const REMOTE_TOKEN="__VISSHAK_REMOTE_TOKEN__";
let recognition=null,listening=false;
function add(who,msg){chat.textContent+="\n\n"+who+": "+msg;chat.scrollTop=chat.scrollHeight}
function setupVoice(){const SR=window.SpeechRecognition||window.webkitSpeechRecognition;if(!SR){voiceHint.textContent="This browser does not support voice. Use Chrome on Android.";micBtn.disabled=true;return}recognition=new SR();recognition.lang="en-IN";recognition.continuous=false;recognition.interimResults=false;recognition.onstart=()=>{listening=true;micBtn.classList.add("listening");micBtn.textContent="🛑 LISTENING...";voiceHint.textContent="Speak now...";statusEl.textContent="● LISTENING"};recognition.onresult=e=>{const text=e.results[0][0].transcript.trim();if(text){input.value=text;sendCommand()}};recognition.onerror=e=>{listening=false;micBtn.classList.remove("listening");micBtn.textContent="🎤 VOICE COMMAND";let msg="Voice error: "+e.error+". ";if(e.error==="not-allowed"||e.error==="service-not-allowed")msg+="Open site microphone permission and Allow.";else if(e.error==="network")msg+="Check internet/browser speech service.";else msg+="Tap again and speak.";voiceHint.textContent=msg;statusEl.textContent="● LINK ONLINE"};recognition.onend=()=>{listening=false;micBtn.classList.remove("listening");micBtn.textContent="🎤 VOICE COMMAND";if(statusEl.textContent==="● LISTENING")statusEl.textContent="● LINK ONLINE"}}
function toggleMic(){if(!recognition){setupVoice();if(!recognition)return}if(listening){recognition.stop();return}try{recognition.start()}catch(e){voiceHint.textContent="Tap once and try again."}}
async function sendCommand(){const command=input.value.trim();if(!command)return;input.value="";add("YOU",command);statusEl.textContent="● PROCESSING";try{const r=await fetch("/command",{method:"POST",headers:{"Content-Type":"application/json","Authorization":"Bearer "+REMOTE_TOKEN},body:JSON.stringify({command})});const data=await r.json();add("VISSHAK",data.response||"Command sent to PC.");statusEl.textContent="● LINK ONLINE"}catch(e){add("SYSTEM","Connection error.");statusEl.textContent="● LINK ERROR"}}
function quick(command){input.value=command;sendCommand()}
input.addEventListener("keydown",e=>{if(e.key==="Enter")sendCommand()});setupVoice();
</script>
</body>
</html>
'''



class VisshakRemoteHandler(http.server.BaseHTTPRequestHandler):

    def log_message(self, format, *args):
        print("REMOTE:", format % args)

    def send_json(self, payload, status=200):
        data = json.dumps(payload).encode("utf-8")

        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        if self.path == "/" or self.path.startswith("/index"):
            data = REMOTE_HTML.replace("__VISSHAK_REMOTE_TOKEN__", REMOTE_AUTH_TOKEN).encode("utf-8")

            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(data)
            return

        if self.path == "/health":
            self.send_json({
                "status": "online",
                "assistant": "VISSHAK"
            })
            return

        self.send_json({"error": "Not found"}, 404)

    def do_POST(self):
        if self.path != "/command":
            self.send_json({"error": "Not found"}, 404)
            return

        # Require the short-lived token embedded in the private mobile page.
        expected_auth = "Bearer " + REMOTE_AUTH_TOKEN
        supplied_auth = self.headers.get("Authorization", "")
        if not secrets.compare_digest(supplied_auth, expected_auth):
            self.send_json({"error": "Unauthorized"}, 401)
            return

        try:
            length = int(self.headers.get("Content-Length", "0"))
            if length <= 0 or length > 10000:
                self.send_json({"error": "Invalid request"}, 400)
                return

            raw = self.rfile.read(length)
            payload = json.loads(raw.decode("utf-8"))

            command = str(payload.get("command", "")).strip()

            if not command:
                self.send_json({"error": "Command is empty"}, 400)
                return

            if len(command) > 1000:
                self.send_json({"error": "Command too long"}, 400)
                return

            with remote_response_lock:
                before = remote_response_version

            command_queue.put((command, False))

            response = None
            deadline = time.time() + 15

            while time.time() < deadline:
                time.sleep(0.15)

                with remote_response_lock:
                    if remote_response_version != before:
                        response = remote_last_response
                        break

            self.send_json({
                "ok": True,
                "response": response or "Command sent to VISSHAK."
            })

        except Exception as e:
            print("Remote command error:", e)
            self.send_json({"error": "Command processing failed"}, 500)


class VisshakRemoteServer(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True


def start_remote_server():
    global remote_server

    ip = get_tailscale_ip()

    if not ip:
        print("REMOTE: Tailscale IP not found. Remote server not started.")
        return

    try:
        # Always keep the backend on localhost. Tailscale Serve securely
        # publishes this local port over HTTPS to the phone.
        bind_host = "127.0.0.1"

        remote_server = VisshakRemoteServer(
            (bind_host, REMOTE_PORT),
            VisshakRemoteHandler
        )

        threading.Thread(
            target=remote_server.serve_forever,
            daemon=True
        ).start()

        print(
            "REMOTE: VISSHAK local server running at "
            f"http://127.0.0.1:{REMOTE_PORT}"
        )

    except Exception as e:
        print("REMOTE SERVER ERROR:", e)
        ui_call(
            add_chat,
            "VISSHAK",
            "Remote phone server could not start."
        )


# =========================================================
# NEON COLORS
# =========================================================

BG = "#03030a"
PANEL = "#080817"
PANEL2 = "#10102a"
PANEL3 = "#15153a"

CYAN = "#00f6ff"
BLUE = "#248cff"
PURPLE = "#a855f7"
PINK = "#ff3cac"
GREEN = "#00ff9d"
YELLOW = "#ffd166"
RED = "#ff4d6d"

WHITE = "#f2fbff"
TEXT = "#d7f8ff"
MUTED = "#6670a8"
GRID = "#17194a"
DEEP = "#02020a"


# =========================================================
# TKINTER WINDOW
# =========================================================

root = tk.Tk()

root.title(
    "VISSHAK // NEURAL COMMAND SYSTEM"
)

root.geometry(
    "1500x900"
)

root.minsize(
    1150,
    720
)

root.configure(
    bg=BG
)


# =========================================================
# MEMORY SYSTEM
# =========================================================

def load_memory():

    if not os.path.exists(MEMORY_FILE):
        return {}

    try:

        with open(
            MEMORY_FILE,
            "r",
            encoding="utf-8"
        ) as file:

            return json.load(file)

    except Exception as e:

        print(
            "Memory load error:",
            e
        )

        return {}


def save_memory(data):

    try:

        with open(
            MEMORY_FILE,
            "w",
            encoding="utf-8"
        ) as file:

            json.dump(
                data,
                file,
                indent=4,
                ensure_ascii=False
            )

        return True

    except Exception as e:

        print(
            "Memory save error:",
            e
        )

        return False


memory = load_memory()


# =========================================================
# UI SAFE CALL
# =========================================================

def ui_call(function, *args):

    try:

        root.after(
            0,
            lambda: function(*args)
        )

    except Exception:

        pass


# =========================================================
# STATUS
# =========================================================

def set_status(status):

    global status_value

    status_value = status

    ui_call(
        update_status_ui,
        status
    )


def update_status_ui(status):

    try:

        status_label.config(
            text="● " + status
        )

        if voice_enabled:

            mode_label.config(
                text="VOICE ONLINE",
                fg=GREEN
            )

        else:

            mode_label.config(
                text="TEXT COMMAND",
                fg=CYAN
            )

        if status == "LISTENING":

            status_label.config(
                fg=GREEN
            )

        elif status == "THINKING":

            status_label.config(
                fg=PURPLE
            )

        elif status == "SPEAKING":

            status_label.config(
                fg=YELLOW
            )

        elif status == "TEXT MODE":

            status_label.config(
                fg=CYAN
            )

        elif status == "READY":

            status_label.config(
                fg=GREEN
            )

        else:

            status_label.config(
                fg=MUTED
            )

    except Exception:

        pass


# =========================================================
# CHAT SYSTEM
# =========================================================

def add_chat(sender, message):

    def update():

        try:

            chat.config(
                state="normal"
            )

            tag = (
                "user"
                if sender == "YOU"
                else "visshak"
            )

            timestamp = datetime.now().strftime(
                "%H:%M:%S"
            )

            chat.insert(
                "end",
                "[" + timestamp + "] ",
                "time"
            )

            chat.insert(
                "end",
                sender + ": ",
                tag
            )

            chat.insert(
                "end",
                str(message) + "\n\n"
            )

            chat.see("end")

            chat.config(
                state="disabled"
            )

        except Exception:

            pass

    ui_call(update)


# =========================================================
# TEXT TO SPEECH
# =========================================================

def speak(text):

    global tts_busy

    global remote_last_response
    global remote_response_version

    print(
        "VISSHAK:",
        text
    )

    with remote_response_lock:
        remote_last_response = str(text)
        remote_response_version += 1

    add_chat(
        "VISSHAK",
        text
    )

    if not sound_enabled:

        set_status(
            "LISTENING"
            if voice_enabled
            else "TEXT MODE"
        )

        return

    tts_busy = True

    set_status(
        "SPEAKING"
    )

    safe_text = str(text)

    safe_text = safe_text.replace(
        "\r",
        " "
    )

    safe_text = safe_text.replace(
        "\n",
        " "
    )

    safe_text = safe_text.replace(
        "'",
        "''"
    )

    ps_script = (
        "Add-Type -AssemblyName System.Speech; "

        "$s = New-Object "
        "System.Speech.Synthesis.SpeechSynthesizer; "

        "$selected = $false; "

        "try { "

        "$voices = $s.GetInstalledVoices(); "

        "$preferred = @("
        "'Microsoft David Desktop',"
        "'David',"
        "'George',"
        "'Mark',"
        "'Guy',"
        "'Ryan',"
        "'Daniel'"
        "); "

        "foreach($p in $preferred) { "

        "foreach($v in $voices) { "

        "$n = $v.VoiceInfo.Name; "

        "if ($n -like ('*' + $p + '*')) { "

        "$s.SelectVoice($n); "
        "$selected = $true; "
        "break; "

        "} "

        "} "

        "if ($selected) { break } "

        "} "

        "if (-not $selected) { "

        "foreach($v in $voices) { "

        "$n = $v.VoiceInfo.Name; "

        "$l = $v.VoiceInfo.GetAttribute('Language'); "

        "if (($l -match 'en-') "
        "-or ($n -match 'English')) { "

        "$s.SelectVoice($n); "
        "break; "

        "} "

        "} "

        "} "

        "} catch {} "

        "$s.Rate = -2; "

        "$s.Volume = 100; "

        f"$s.Speak('{safe_text}'); "

        "$s.Dispose();"
    )

    try:

        subprocess.run(
            [
                "powershell",
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-Command",
                ps_script
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=getattr(
                subprocess,
                "CREATE_NO_WINDOW",
                0
            )
        )

    except Exception as e:

        print(
            "TTS error:",
            e
        )

    tts_busy = False

    if running:

        set_status(
            "LISTENING"
            if voice_enabled
            else "TEXT MODE"
        )


# =========================================================
# TOGGLE SOUND
# =========================================================

def toggle_sound():

    global sound_enabled

    sound_enabled = not sound_enabled

    if sound_enabled:

        sound_button.config(
            text="🔊  VOICE SOUND  /  ON",
            fg=GREEN,
            bg="#102d23",
            activebackground="#194837",
            activeforeground=GREEN
        )

        sound_status.config(
            text="VOICE SOUND: ON",
            fg=GREEN
        )

        add_chat(
            "VISSHAK",
            "Voice sound enabled."
        )

    else:

        sound_button.config(
            text="🔇  VOICE SOUND  /  OFF",
            fg=RED,
            bg="#30121b",
            activebackground="#4a1825",
            activeforeground=RED
        )

        sound_status.config(
            text="VOICE SOUND: OFF",
            fg=RED
        )

        add_chat(
            "VISSHAK",
            "Voice sound muted. Commands will still work."
        )


# =========================================================
# OLLAMA AI
# =========================================================

def ask_ai(question):

    try:

        response = requests.post(
            OLLAMA_URL,

            json={
                "model": OLLAMA_MODEL,

                "prompt": (
                    "You are VISSHAK, a futuristic "
                    "personal AI assistant. "

                    "Answer briefly in 2 or 3 sentences. "

                    "Be calm, precise and professional. "

                    "Do not say you are ChatGPT. "

                    "Your name is VISSHAK.\n\n"

                    "User: "
                    + question
                ),

                "stream": False
            },

            timeout=60
        )

        response.raise_for_status()

        data = response.json()

        return data.get(
            "response",
            "I could not generate a response."
        ).strip()

    except Exception as e:

        print(
            "AI error:",
            e
        )

        return (
            "Sorry Boss, "
            "I could not connect to my AI brain."
        )


# =========================================================
# VOLUME CONTROL
# =========================================================

def set_volume(percent):

    try:

        devices = AudioUtilities.GetSpeakers()

        volume = devices.EndpointVolume

        percent = max(
            0,
            min(
                100,
                percent
            )
        )

        volume.SetMasterVolumeLevelScalar(
            percent / 100,
            None
        )

        return True

    except Exception as e:

        print(
            "Volume error:",
            e
        )

        return False


def volume_up():

    subprocess.Popen(
        [
            "powershell",
            "-Command",
            "(New-Object -ComObject "
            "WScript.Shell).SendKeys([char]175)"
        ]
    )


def volume_down():

    subprocess.Popen(
        [
            "powershell",
            "-Command",
            "(New-Object -ComObject "
            "WScript.Shell).SendKeys([char]174)"
        ]
    )


def mute_volume():

    subprocess.Popen(
        [
            "powershell",
            "-Command",
            "(New-Object -ComObject "
            "WScript.Shell).SendKeys([char]173)"
        ]
    )


# =========================================================
# YOUTUBE PLAYER
# =========================================================

def get_youtube_page():

    global youtube_playwright
    global youtube_context
    global youtube_page

    with youtube_lock:

        try:

            if youtube_playwright is None:

                youtube_playwright = (
                    sync_playwright().start()
                )

            if youtube_context is None:

                youtube_context = (
                    youtube_playwright
                    .chromium
                    .launch_persistent_context(

                        YOUTUBE_PROFILE,

                        channel="chrome",

                        headless=False,

                        args=[
                            "--disable-blink-features="
                            "AutomationControlled",

                            "--autoplay-policy="
                            "no-user-gesture-required"
                        ],

                        viewport=None
                    )
                )

            if youtube_page is None:

                pages = youtube_context.pages

                if pages:

                    youtube_page = pages[0]

                else:

                    youtube_page = (
                        youtube_context.new_page()
                    )

            if youtube_page.is_closed():

                youtube_page = (
                    youtube_context.new_page()
                )

            return youtube_page

        except Exception as e:

            print(
                "YouTube setup error:",
                e
            )

            youtube_page = None

            try:

                if youtube_context:

                    youtube_context.close()

            except Exception:

                pass

            try:

                if youtube_playwright:

                    youtube_playwright.stop()

            except Exception:

                pass

            youtube_context = None
            youtube_playwright = None

            return None


def close_youtube():

    global youtube_playwright
    global youtube_context
    global youtube_page

    try:

        if youtube_context:

            youtube_context.close()

    except Exception:

        pass

    try:

        if youtube_playwright:

            youtube_playwright.stop()

    except Exception:

        pass

    youtube_page = None
    youtube_context = None
    youtube_playwright = None


# =========================================================
# PLAY YOUTUBE SONG
# =========================================================

def play_youtube(song):

    global youtube_page

    try:

        page = get_youtube_page()

        if page is None:

            speak(
                "YouTube player open panna mudiyala."
            )

            return

        speak(
            song +
            " YouTube la play panren."
        )

        search_url = (
            "https://www.youtube.com/results"
            "?search_query="
            + quote_plus(song)
        )

        page.goto(
            search_url,
            wait_until="domcontentloaded",
            timeout=30000
        )

        page.wait_for_timeout(
            4000
        )

        first_video = page.locator(
            "ytd-video-renderer a#video-title"
        ).first

        first_video.wait_for(
            state="visible",
            timeout=20000
        )

        first_video.click()

        page.wait_for_timeout(
            5000
        )

        try:

            page.evaluate(
                """
                () => {
                    const video =
                        document.querySelector('video');

                    if (video) {
                        video.muted = false;
                        video.play().catch(() => {});
                    }
                }
                """
            )

        except Exception:

            pass

        speak(
            "Playing " + song + "."
        )

    except Exception as e:

        print(
            "YouTube play error:",
            e
        )

        speak(
            "YouTube la song play panna mudiyala."
        )


# =========================================================
# MEMORY EXTRACTION
# =========================================================

def extract_memory(text):

    text = text.lower().strip()

    question_words = [
        "what",
        "who",
        "where",
        "when",
        "why",
        "how",
        "do you",
        "did you",
        "can you",
        "could you",
        "enna",
        "yaaru",
        "enga",
        "eppo",
        "epadi",
        "nyabagam"
    ]

    for word in question_words:

        if text.startswith(word):

            return {
                "remember": False
            }

    # NAME

    if "my name is" in text:

        value = text.split(
            "my name is",
            1
        )[1].strip()

        if value:

            return {
                "remember": True,
                "key": "name",
                "value": value
            }

    if "en peru" in text:

        value = text.split(
            "en peru",
            1
        )[1].strip()

        value = re.sub(
            r"^is\s+",
            "",
            value
        ).strip()

        if value:

            return {
                "remember": True,
                "key": "name",
                "value": value
            }

    # CITY

    for phrase in [
        "i live in",
        "i stay in"
    ]:

        if phrase in text:

            value = text.split(
                phrase,
                1
            )[1].strip()

            if value:

                return {
                    "remember": True,
                    "key": "city",
                    "value": value
                }

    # COLLEGE

    if "my college is" in text:

        value = text.split(
            "my college is",
            1
        )[1].strip()

        if value:

            return {
                "remember": True,
                "key": "college",
                "value": value
            }

    # SCHOOL

    if "my school is" in text:

        value = text.split(
            "my school is",
            1
        )[1].strip()

        if value:

            return {
                "remember": True,
                "key": "school",
                "value": value
            }

    # HOBBY

    if "my hobby is" in text:

        value = text.split(
            "my hobby is",
            1
        )[1].strip()

        if value:

            return {
                "remember": True,
                "key": "hobby",
                "value": value
            }

    # GOAL

    if "my goal is" in text:

        value = text.split(
            "my goal is",
            1
        )[1].strip()

        if value:

            return {
                "remember": True,
                "key": "goal",
                "value": value
            }

    # LEARNING

    for phrase in [
        "i am learning",
        "i'm learning"
    ]:

        if phrase in text:

            value = text.split(
                phrase,
                1
            )[1].strip()

            if value:

                return {
                    "remember": True,
                    "key": "learning",
                    "value": value
                }

    # MARVEL

    if (
        "i love marvel" in text
        or "i like marvel" in text
    ):

        return {
            "remember": True,
            "key": "favorite_movies",
            "value": "Marvel movies"
        }

    # LIKE

    if "i like" in text:

        value = text.split(
            "i like",
            1
        )[1].strip()

        if value:

            return {
                "remember": True,
                "key": "likes",
                "value": value
            }

    # LOVE

    if "i love" in text:

        value = text.split(
            "i love",
            1
        )[1].strip()

        if value:

            return {
                "remember": True,
                "key": "likes",
                "value": value
            }

    # SKILL

    if "i know" in text:

        value = text.split(
            "i know",
            1
        )[1].strip()

        if value:

            return {
                "remember": True,
                "key": "skill",
                "value": value
            }

    return {
        "remember": False
    }


# =========================================================
# MEMORY SEARCH
# =========================================================

def search_memory(question):

    if not memory:

        return (
            "I don't have that information "
            "in my memory yet."
        )

    q = question.lower()

    # NAME

    if (
        "name" in q
        or "en peru" in q
    ):

        if "name" in memory:

            return (
                "Your name is "
                + str(memory["name"])
                + "."
            )

    # LIKE / LOVE

    if (
        "like" in q
        or "love" in q
        or "enjoy" in q
        or "pidikkum" in q
    ):

        answers = []

        if "favorite_movies" in memory:

            answers.append(
                "You like "
                + str(
                    memory["favorite_movies"]
                )
            )

        if "likes" in memory:

            answers.append(
                "You like "
                + str(
                    memory["likes"]
                )
            )

        if answers:

            return (
                ". ".join(answers)
                + "."
            )

    # LEARNING

    if (
        "learning" in q
        or "learn" in q
    ):

        if "learning" in memory:

            return (
                "You are learning "
                + str(
                    memory["learning"]
                )
                + "."
            )

    # HOBBY

    if "hobby" in q:

        if "hobby" in memory:

            return (
                "Your hobby is "
                + str(
                    memory["hobby"]
                )
                + "."
            )

    # GOAL

    if "goal" in q:

        if "goal" in memory:

            return (
                "Your goal is "
                + str(
                    memory["goal"]
                )
                + "."
            )

    # SKILL

    if "skill" in q:

        if "skill" in memory:

            return (
                "Your skill is "
                + str(
                    memory["skill"]
                )
                + "."
            )

    # COLLEGE

    if "college" in q:

        if "college" in memory:

            return (
                "Your college is "
                + str(
                    memory["college"]
                )
                + "."
            )

    # CITY

    if (
        "live" in q
        or "stay" in q
        or "city" in q
    ):

        if "city" in memory:

            return (
                "You live in "
                + str(
                    memory["city"]
                )
                + "."
            )

    # SCHOOL

    if "school" in q:

        if "school" in memory:

            return (
                "Your school is "
                + str(
                    memory["school"]
                )
                + "."
            )

    # FAVORITES

    if (
        "favorite" in q
        or "favorites" in q
    ):

        results = []

        for key, value in memory.items():

            if (
                key.startswith("favorite")
                or key == "likes"
            ):

                results.append(
                    str(value)
                )

        if results:

            return (
                "Your favorites are "
                + ", ".join(results)
                + "."
            )

    return (
        "I don't have that information "
        "in my memory yet."
    )


# =========================================================
# WAKE WORD FUNCTIONS
# =========================================================

def has_wake_word(text):

    lower = text.lower().strip()

    return any(
        lower.startswith(word)
        for word in WAKE_WORDS
    )


def remove_wake_word(text):

    lower = text.lower().strip()

    for word in WAKE_WORDS:

        if lower.startswith(word):

            return text[
                len(word):
            ].strip()

    return text.strip()


# =========================================================
# WEBSITE MAP
# =========================================================

website_map = {

    "youtube":
        "https://www.youtube.com",

    "instagram":
        "https://www.instagram.com",

    "gmail":
        "https://mail.google.com",

    "google":
        "https://www.google.com",

    "spotify":
        "https://open.spotify.com",

    "netflix":
        "https://www.netflix.com",

    "linkedin":
        "https://www.linkedin.com",

    "facebook":
        "https://www.facebook.com",

    "twitter":
        "https://twitter.com",

    "x":
        "https://x.com",

    "github":
        "https://github.com",

    "chatgpt":
        "https://chatgpt.com",

    "reddit":
        "https://www.reddit.com",

    "amazon":
        "https://www.amazon.in",

    "flipkart":
        "https://www.flipkart.com"
}


# =========================================================
# WINDOWS SYSTEM CONTROLS
# =========================================================

def close_chrome():
    try:
        close_youtube()
        subprocess.run(["taskkill.exe","/F","/T","/IM","chrome.exe"],capture_output=True,text=True,timeout=15)
        time.sleep(0.8)
        return True
    except Exception as e:
        print("Chrome close error:",e); return False


def lock_pc():
    try:
        subprocess.Popen(["rundll32.exe","user32.dll,LockWorkStation"]); return True
    except Exception as e:
        print("PC lock error:",e); return False


def request_shutdown():
    global shutdown_confirmation_pending,restart_confirmation_pending
    restart_confirmation_pending=False; shutdown_confirmation_pending=True
    speak("Shutdown confirmation required. Say confirm shutdown or cancel.")


def request_restart():
    global shutdown_confirmation_pending,restart_confirmation_pending
    shutdown_confirmation_pending=False; restart_confirmation_pending=True
    speak("Restart confirmation required. Say confirm restart or cancel.")


def cancel_power_action():
    global shutdown_confirmation_pending,restart_confirmation_pending
    shutdown_confirmation_pending=False; restart_confirmation_pending=False
    try: subprocess.run(["shutdown.exe","/a"],capture_output=True,text=True,timeout=5)
    except Exception: pass
    speak("Power action cancelled.")


def shutdown_pc():
    global shutdown_confirmation_pending
    shutdown_confirmation_pending=False
    try:
        result=subprocess.run(["shutdown.exe","/s","/f","/t","10"],capture_output=True,text=True,timeout=5)
        speak("Shutdown scheduled. PC will turn off in ten seconds." if result.returncode==0 else "Windows shutdown command failed.")
    except Exception as e:
        print("Shutdown error:",e); speak("Shutdown command failed.")


def restart_pc():
    global restart_confirmation_pending
    restart_confirmation_pending=False
    try:
        result=subprocess.run(["shutdown.exe","/r","/f","/t","10"],capture_output=True,text=True,timeout=5)
        speak("Restart scheduled. PC will restart in ten seconds." if result.returncode==0 else "Windows restart command failed.")
    except Exception as e:
        print("Restart error:",e); speak("Restart command failed.")


def show_interface():
    try:
        root.deiconify(); root.lift(); root.focus_force(); speak("Interface visible.")
    except Exception as e: print("Show interface error:",e)


def hide_interface():
    try:
        root.withdraw(); speak("Interface hidden. VISSHAK continues in background.")
    except Exception as e: print("Hide interface error:",e)


# =========================================================
# COMMAND ENGINE
# =========================================================

def process_command(
    original_text,
    from_voice=False
):

    global running

    text = original_text.strip()

    if not text:

        return

    # -----------------------------------------------------
    # VOICE WAKE WORD
    # -----------------------------------------------------

    if from_voice:

        if not has_wake_word(text):

            set_status(
                "LISTENING"
            )

            return

        text = remove_wake_word(
            text
        )

        if not text:

            speak(
                "Yes Boss?"
            )

            return

    # -----------------------------------------------------
    # CHAT
    # -----------------------------------------------------

    add_chat(
        "YOU",
        original_text
    )

    lower_text = text.lower().strip()

    set_status(
        "THINKING"
    )

    # =====================================================
    # POWER CONFIRMATION
    # =====================================================

    global shutdown_confirmation_pending, restart_confirmation_pending

    if shutdown_confirmation_pending:
        if "confirm shutdown" in lower_text or lower_text in ("confirm", "yes shutdown", "shutdown confirm"):
            shutdown_pc()
        elif "cancel" in lower_text or "stop shutdown" in lower_text:
            cancel_power_action()
        else:
            speak("Say confirm shutdown or cancel.")
        return

    if restart_confirmation_pending:
        if "confirm restart" in lower_text or lower_text in ("confirm", "yes restart", "restart confirm"):
            restart_pc()
        elif "cancel" in lower_text or "stop restart" in lower_text:
            cancel_power_action()
        else:
            speak("Say confirm restart or cancel.")
        return

    # =====================================================
    # STOP
    # =====================================================

    if (
        "stop visshak" in lower_text
        or "close visshak" in lower_text
        or lower_text == "stop"
        or lower_text == "bye"
        or lower_text == "exit"
    ):

        speak(
            "Mission complete. "
            "See you later Boss."
        )

        running = False

        close_youtube()

        root.after(
            800,
            root.destroy
        )

        return

    # =====================================================
    # INTERFACE SHOW / HIDE
    # =====================================================

    if lower_text in ("open interface", "show interface", "interface open", "visshak open interface"):
        show_interface()
        return

    if lower_text in ("hide interface", "close interface", "interface hide", "visshak hide interface"):
        hide_interface()
        return

    # =====================================================
    # CHROME CLOSE
    # =====================================================

    if "close chrome" in lower_text or lower_text in ("chrome close", "close chrome pannu", "chrome ah close pannu"):
        speak("Chrome closed." if close_chrome() else "Chrome close panna mudiyala.")
        return

    # =====================================================
    # YOUTUBE CLOSE
    # =====================================================

    if "close youtube" in lower_text or "youtube close" in lower_text:
        close_youtube()
        speak("YouTube closed.")
        return

    # =====================================================
    # LOCK PC
    # =====================================================

    if lower_text in ("lock", "lock pc", "lock computer", "pc lock", "computer lock", "lock pannu", "pc ah lock pannu") or lower_text.startswith("lock pc"):
        speak("PC locked." if lock_pc() else "PC lock panna mudiyala.")
        return

    # =====================================================
    # SHUTDOWN / RESTART
    # =====================================================

    if "shutdown pc" in lower_text or "shutdown computer" in lower_text or lower_text in ("shutdown", "pc shutdown", "shutdown pannu"):
        request_shutdown()
        return

    if "restart pc" in lower_text or "restart computer" in lower_text or lower_text in ("restart", "pc restart", "restart pannu"):
        request_restart()
        return

    if lower_text in ("cancel", "cancel power", "cancel shutdown", "cancel restart"):
        cancel_power_action()
        return

    # =====================================================
    # NOTEPAD
    # =====================================================

    if (
        "open notepad" in lower_text
        or "notepad open" in lower_text
        or "notepad ah open" in lower_text
    ):

        subprocess.Popen(
            "notepad.exe"
        )

        speak(
            "Opening Notepad."
        )

        return

    # =====================================================
    # CHROME
    # =====================================================

    if (
        "open chrome" in lower_text
        or "chrome open" in lower_text
        or "chrome ah open" in lower_text
    ):

        subprocess.Popen(
            "start chrome",
            shell=True
        )

        speak(
            "Opening Chrome."
        )

        return

    # =====================================================
    # CALCULATOR
    # =====================================================

    if (
        "open calculator" in lower_text
        or "calculator open" in lower_text
        or "calculator ah open" in lower_text
    ):

        subprocess.Popen(
            "calc.exe"
        )

        speak(
            "Opening Calculator."
        )

        return

    # =====================================================
    # TIME
    # =====================================================

    if (
        "what time" in lower_text
        or "what is the time" in lower_text
        or "time enna" in lower_text
        or "time sollu" in lower_text
        or "neram enna" in lower_text
    ):

        current_time = datetime.now().strftime(
            "%I:%M %p"
        )

        speak(
            "The time is "
            + current_time
        )

        return

    # =====================================================
    # EXACT VOLUME
    # =====================================================

    if (
        "volume" in lower_text
        and (
            "percent" in lower_text
            or "%" in lower_text
        )
    ):

        match = re.search(
            r"(\d+)\s*(?:percent|%)?",
            lower_text
        )

        if match:

            percent = int(
                match.group(1)
            )

            if set_volume(percent):

                speak(
                    "Volume "
                    + str(percent)
                    + " percent set panren."
                )

            else:

                speak(
                    "Volume set panna mudiyala."
                )

        return

    # =====================================================
    # VOLUME UP
    # =====================================================

    if (
        "volume up" in lower_text
        or "volume increase" in lower_text
        or "sound up" in lower_text
        or "sound increase" in lower_text
    ):

        volume_up()

        speak(
            "Volume increase panren."
        )

        return

    # =====================================================
    # VOLUME DOWN
    # =====================================================

    if (
        "volume down" in lower_text
        or "volume decrease" in lower_text
        or "sound down" in lower_text
        or "sound decrease" in lower_text
    ):

        volume_down()

        speak(
            "Volume decrease panren."
        )

        return

    # =====================================================
    # MUTE
    # =====================================================

    if (
        "mute" in lower_text
        or "sound mute" in lower_text
    ):

        mute_volume()

        speak(
            "Sound mute panren."
        )

        return

    # =====================================================
    # YOUTUBE PLAY
    # =====================================================

    play_command = (
        lower_text.startswith("play ")
        or lower_text == "play"
        or lower_text.startswith("play music")
        or lower_text.startswith("play song")
    )

    if play_command:

        song = lower_text

        song = re.sub(
            r"^play\s*",
            "",
            song
        )

        if song.startswith("music"):

            song = song[
                len("music"):
            ].strip()

        if song.startswith("song"):

            song = song[
                len("song"):
            ].strip()

        song = song.strip()

        if not song:

            page = get_youtube_page()

            if page:

                try:

                    page.goto(
                        "https://www.youtube.com",
                        wait_until="domcontentloaded",
                        timeout=30000
                    )

                    speak(
                        "YouTube open panren."
                    )

                except Exception:

                    speak(
                        "YouTube open panna mudiyala."
                    )

            return

        play_youtube(
            song
        )

        return

    # =====================================================
    # PAUSE
    # =====================================================

    if (
        "pause music" in lower_text
        or "pause song" in lower_text
        or lower_text == "pause"
        or "music pause" in lower_text
    ):

        try:

            if (
                youtube_page
                and not youtube_page.is_closed()
            ):

                youtube_page.evaluate(
                    """
                    () => {
                        const video =
                            document.querySelector('video');

                        if (video) {
                            video.pause();
                        }
                    }
                    """
                )

                speak(
                    "Music pause panren."
                )

            else:

                speak(
                    "No music playing."
                )

        except Exception as e:

            print(
                "Pause error:",
                e
            )

            speak(
                "Music pause panna mudiyala."
            )

        return

    # =====================================================
    # RESUME
    # =====================================================

    if (
        "resume music" in lower_text
        or "resume song" in lower_text
        or lower_text == "resume"
        or "music resume" in lower_text
    ):

        try:

            if (
                youtube_page
                and not youtube_page.is_closed()
            ):

                youtube_page.evaluate(
                    """
                    () => {
                        const video =
                            document.querySelector('video');

                        if (video) {
                            video.muted = false;
                            video.play().catch(() => {});
                        }
                    }
                    """
                )

                speak(
                    "Music resume panren."
                )

            else:

                speak(
                    "No music player open."
                )

        except Exception as e:

            print(
                "Resume error:",
                e
            )

            speak(
                "Music resume panna mudiyala."
            )

        return

    # =====================================================
    # NEXT
    # =====================================================

    if (
        "next song" in lower_text
        or "next music" in lower_text
        or "next song pannu" in lower_text
    ):

        try:

            if (
                youtube_page
                and not youtube_page.is_closed()
            ):

                youtube_page.bring_to_front()

                clicked = youtube_page.locator("button.ytp-next-button, a.ytp-next-button").first
                if clicked.count():
                    clicked.click()
                else:
                    youtube_page.keyboard.press("Shift+N")

                speak(
                    "Next song."
                )

            else:

                speak(
                    "No music player open."
                )

        except Exception as e:

            print(
                "Next error:",
                e
            )

            speak(
                "Next song panna mudiyala."
            )

        return

    # =====================================================
    # PREVIOUS
    # =====================================================

    if (
        "previous song" in lower_text
        or "previous music" in lower_text
        or "previous song pannu" in lower_text
    ):

        try:

            if (
                youtube_page
                and not youtube_page.is_closed()
            ):

                youtube_page.bring_to_front()

                clicked = youtube_page.locator("button.ytp-prev-button, a.ytp-prev-button").first
                if clicked.count():
                    clicked.click()
                else:
                    youtube_page.keyboard.press("Shift+P")

                speak(
                    "Previous song."
                )

            else:

                speak(
                    "No music player open."
                )

        except Exception as e:

            print(
                "Previous error:",
                e
            )

            speak(
                "Previous song panna mudiyala."
            )

        return

    # =====================================================
    # WEBSITE OPEN
    # =====================================================

    if "open" in lower_text:

        selected_site = None

        for site in website_map:

            if site == "x":

                if (
                    lower_text == "open x"
                    or "open x " in lower_text
                ):

                    selected_site = site

                    break

            elif site in lower_text:

                selected_site = site

                break

        if selected_site:

            subprocess.Popen(
                f'start chrome '
                f'"{website_map[selected_site]}"',
                shell=True
            )

            speak(
                selected_site
                + " open panren."
            )

            return

    # =====================================================
    # GOOGLE SEARCH
    # =====================================================

    if (
        "search" in lower_text
        or "google la" in lower_text
        or "google search" in lower_text
    ):

        query = lower_text

        for word in [
            "google la",
            "google search",
            "search for",
            "search pannu",
            "search panna",
            "search pan",
            "search pannunga",
            "search"
        ]:

            query = query.replace(
                word,
                ""
            )

        query = query.strip()

        if query:

            url = (
                "https://www.google.com/search?q="
                + quote_plus(query)
            )

            subprocess.Popen(
                f'start chrome "{url}"',
                shell=True
            )

            speak(
                "Google la "
                + query
                + " search panren."
            )

        return

    # =====================================================
    # SHOW MEMORY
    # =====================================================

    if (
        "what do you remember" in lower_text
        or "what do you know about me" in lower_text
        or "enna nyabagam irukku" in lower_text
        or "enna pathi enna nyabagam" in lower_text
        or "enna pathi enna theriyum" in lower_text
    ):

        if memory:

            memory_text = ", ".join(
                f"{key}: {value}"
                for key, value
                in memory.items()
            )

            speak(
                "Here is what I remember. "
                + memory_text
            )

        else:

            speak(
                "I don't remember anything yet."
            )

        return

    # =====================================================
    # NAME RECALL
    # =====================================================

    if (
        "what is my name" in lower_text
        or "en peru enna" in lower_text
        or "en peru enna da" in lower_text
    ):

        if "name" in memory:

            speak(
                "Your name is "
                + str(
                    memory["name"]
                )
            )

        else:

            speak(
                "I don't know your name yet."
            )

        return

    # =====================================================
    # COLLEGE RECALL
    # =====================================================

    if (
        "what is my college" in lower_text
        or "en college enna" in lower_text
        or "en college peru enna" in lower_text
    ):

        if "college" in memory:

            speak(
                "Your college is "
                + str(
                    memory["college"]
                )
            )

        else:

            speak(
                "I don't know your college yet."
            )

        return

    # =====================================================
    # LOCATION RECALL
    # =====================================================

    if (
        "where do i live" in lower_text
        or "where do i stay" in lower_text
        or "enga stay panren" in lower_text
        or "naan enga stay panren" in lower_text
        or "naan enga live panren" in lower_text
    ):

        if "city" in memory:

            speak(
                "You live in "
                + str(
                    memory["city"]
                )
            )

        else:

            speak(
                "I don't know where you live yet."
            )

        return

    # =====================================================
    # MEMORY QUESTIONS
    # =====================================================

    memory_words = [

        "do you remember",

        "what do i like",

        "what do i love",

        "what am i learning",

        "what i am learning",

        "what is my hobby",

        "what are my hobbies",

        "what is my goal",

        "what are my goals",

        "what are my interests",

        "what are my skills",

        "what do i enjoy",

        "what is my favorite",

        "what are my favorites",

        "enna like panren",

        "enna love panren",

        "enna pidikkum",

        "naan enna learn panren",

        "naan enna learning panren",

        "enna learn panren",

        "en hobby enna",

        "en goal enna",

        "en interests enna",

        "en skills enna",

        "en favorite enna"
    ]

    if any(
        word in lower_text
        for word in memory_words
    ):

        speak(
            search_memory(text)
        )

        return

    # =====================================================
    # AUTOMATIC MEMORY
    # =====================================================

    memory_result = extract_memory(
        text
    )

    if memory_result.get(
        "remember"
    ):

        key = memory_result.get(
            "key"
        )

        value = memory_result.get(
            "value"
        )

        if key and value:

            memory[key] = value

            save_memory(
                memory
            )

            print(
                "Memory saved:",
                key,
                "=",
                value
            )

            speak(
                "Got it. "
                "I will remember that."
            )

            return

    # =====================================================
    # AI ANSWER
    # =====================================================

    answer = ask_ai(
        text
    )

    speak(
        answer
    )


# =========================================================
# VOICE ENGINE
# =========================================================

def voice_loop():

    global running

    while running:

        if (
            not voice_enabled
            or tts_busy
        ):

            time.sleep(
                0.15
            )

            continue

        try:

            set_status(
                "LISTENING"
            )

            audio = sd.rec(
                int(
                    RECORD_DURATION
                    * SAMPLE_RATE
                ),

                samplerate=SAMPLE_RATE,

                channels=1,

                dtype="int16"
            )

            sd.wait()

            if not running:

                break

            if (
                not voice_enabled
                or tts_busy
            ):

                continue

            audio_data = sr.AudioData(
                audio.tobytes(),
                SAMPLE_RATE,
                2
            )

            try:

                # Google speech recognition requires an internet connection.
                text = (
                    recognizer.recognize_google(
                        audio_data
                    )
                )

                if text.strip():

                    command_queue.put(
                        (
                            text,
                            True
                        )
                    )

            except sr.UnknownValueError:

                set_status(
                    "LISTENING"
                )

            except sr.RequestError as e:

                print(
                    "Speech recognition error:",
                    e
                )

                set_status(
                    "LISTENING"
                )

        except Exception as e:

            print(
                "Voice error:",
                e
            )

            time.sleep(
                0.5
            )


# =========================================================
# COMMAND WORKER
# =========================================================

def command_worker():

    global running

    while running:

        try:

            original_text, from_voice = (
                command_queue.get(
                    timeout=0.5
                )
            )

            process_command(
                original_text,
                from_voice
            )

            command_queue.task_done()

        except queue.Empty:

            continue

        except Exception as e:

            print(
                "Command worker error:",
                e
            )


# =========================================================
# TEXT COMMAND
# =========================================================

def send_text_command():

    text = command_entry.get().strip()

    if (
        not text
        or text == "Type command here..."
    ):

        return

    command_entry.delete(
        0,
        "end"
    )

    command_queue.put(
        (
            text,
            False
        )
    )


# =========================================================
# VOICE TOGGLE
# =========================================================

def toggle_voice():

    global voice_enabled

    voice_enabled = not voice_enabled

    if voice_enabled:

        voice_button.config(
            text="◉  VOICE MODE  /  ON",
            fg=GREEN,
            bg="#102d23"
        )

        mode_label.config(
            text="VOICE ONLINE",
            fg=GREEN
        )

        text_hint.config(
            text="Voice active  //  Say BOSS + command",
            fg=MUTED
        )

        set_status(
            "LISTENING"
        )

    else:

        voice_button.config(
            text="▣  TEXT MODE  /  ON",
            fg=CYAN,
            bg="#101b3d"
        )

        mode_label.config(
            text="TEXT COMMAND",
            fg=CYAN
        )

        text_hint.config(
            text="TEXT COMMAND MODE  //  Type below and press ENTER",
            fg=CYAN
        )

        set_status(
            "TEXT MODE"
        )

        focus_text_box()


# =========================================================
# FOCUS TEXT BOX
# =========================================================

def focus_text_box():

    try:

        command_entry.focus_set()

    except Exception:

        pass


# =========================================================
# FULLSCREEN
# =========================================================

def fullscreen_toggle(event=None):

    current = bool(
        root.attributes(
            "-fullscreen"
        )
    )

    root.attributes(
        "-fullscreen",
        not current
    )


def exit_fullscreen(event=None):

    root.attributes(
        "-fullscreen",
        False
    )


# =========================================================
# STARTUP FORMATION // ORIGINAL FUTURISTIC SFX
# =========================================================

SFX_DIR = os.path.abspath("visshak_sfx")


def _write_wav(path, samples, sample_rate=44100):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with wave.open(path, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        frames = bytearray()
        for value in samples:
            value = max(-1.0, min(1.0, value))
            frames.extend(struct.pack("<h", int(value * 32767)))
        wf.writeframes(frames)


def _make_sfx_files():
    os.makedirs(SFX_DIR, exist_ok=True)
    names = ["hum.wav", "whoosh.wav", "charge.wav", "lock.wav", "power.wav"]
    paths = [os.path.join(SFX_DIR, n) for n in names]
    if all(os.path.exists(x) for x in paths):
        return paths
    sr = 44100
    n = int(sr * 2.2)
    hum=[]
    for i in range(n):
        t=i/sr; env=min(1.0,t*4.0)*min(1.0,(2.2-t)*4.0)
        hum.append((0.16*math.sin(2*math.pi*55*t)+0.06*math.sin(2*math.pi*110*t))*env)
    _write_wav(paths[0],hum,sr)
    n=int(sr*1.0); whoosh=[]
    for i in range(n):
        t=i/sr; f=180+1450*t*t; env=math.sin(math.pi*t)
        whoosh.append(0.22*math.sin(2*math.pi*f*t)*env)
    _write_wav(paths[1],whoosh,sr)
    n=int(sr*1.8); charge=[]
    for i in range(n):
        t=i/sr; f=260+1100*t; env=(t/1.8)**0.7*min(1.0,(1.8-t)*5)
        charge.append((0.20*math.sin(2*math.pi*f*t)+0.07*math.sin(2*math.pi*2*f*t))*env)
    _write_wav(paths[2],charge,sr)
    n=int(sr*0.16); lock=[]
    for i in range(n):
        t=i/sr; env=max(0.0,1.0-t/0.16)**2; freq=900 if t<0.055 else 1450
        lock.append(0.32*math.sin(2*math.pi*freq*t)*env)
    _write_wav(paths[3],lock,sr)
    n=int(sr*1.4); power=[]
    for i in range(n):
        t=i/sr; f=160+900*(t/1.4); env=min(1.0,t*7)*min(1.0,(1.4-t)*5)
        power.append((0.24*math.sin(2*math.pi*f*t)+0.10*math.sin(2*math.pi*2*f*t))*env)
    _write_wav(paths[4],power,sr)
    return paths


def play_startup_sfx(name, wait=False):
    if not sound_enabled:
        return
    try:
        paths=_make_sfx_files()
        path={"hum":paths[0],"whoosh":paths[1],"charge":paths[2],"lock":paths[3],"power":paths[4]}.get(name)
        if path:
            winsound.PlaySound(path, winsound.SND_FILENAME | (winsound.SND_SYNC if wait else winsound.SND_ASYNC))
    except Exception as e:
        print("Startup SFX error:",e)


def stop_startup_sfx():
    try:
        winsound.PlaySound(None,winsound.SND_PURGE)
    except Exception:
        pass


def start_formation_sequence():
    global formation_overlay, formation_canvas
    try:
        root.withdraw()
        formation_overlay=tk.Toplevel(root)
        formation_overlay.overrideredirect(True)
        formation_overlay.configure(bg="#010208")
        formation_overlay.attributes("-topmost",True)
        try:
            formation_overlay.attributes("-fullscreen",True)
        except Exception:
            formation_overlay.geometry(f"{root.winfo_screenwidth()}x{root.winfo_screenheight()}+0+0")
        formation_canvas=tk.Canvas(formation_overlay,bg="#010208",highlightthickness=0)
        formation_canvas.pack(fill="both",expand=True)
        started=time.time()
        particles=[]
        for _ in range(260):
            particles.append({"a":random.uniform(0,math.tau),"r":random.uniform(250,1050),"s":random.uniform(0.7,1.5),"size":random.choice([1,1,2,2,3])})
        sound_schedule=[(0.0,"hum"),(1.4,"whoosh"),(3.0,"whoosh"),(4.2,"charge"),(6.7,"lock"),(7.1,"lock"),(7.5,"lock"),(8.4,"power")]
        played=set()
        def draw():
            if not running or formation_overlay is None: return
            try:
                now=time.time()-started; w=max(formation_canvas.winfo_width(),900); h=max(formation_canvas.winfo_height(),600); cx,cy=w/2,h/2
                formation_canvas.delete("all")
                for x in range(0,w,48): formation_canvas.create_line(x,0,x,h,fill="#071026")
                for y in range(0,h,48): formation_canvas.create_line(0,y,w,y,fill="#071026")
                c,pad=70,28
                for x,y,sx,sy in [(pad,pad,1,1),(w-pad,pad,-1,1),(pad,h-pad,1,-1),(w-pad,h-pad,-1,-1)]:
                    formation_canvas.create_line(x,y,x+sx*c,y,fill="#00eaff",width=3); formation_canvas.create_line(x,y,x,y+sy*c,fill="#00eaff",width=3)
                particle_p=min(now/2.0,1.0)
                for item in particles:
                    rr=item["r"]*(1-particle_p); a=item["a"]+now*item["s"]; x=cx+math.cos(a)*rr; y=cy+math.sin(a)*rr; z=item["size"]
                    formation_canvas.create_oval(x-z,y-z,x+z,y+z,fill="#63efff",outline="")
                ring_p=max(0.0,min((now-1.2)/3.0,1.0))
                for idx,base in enumerate([180,270,370,470]):
                    radius=base*ring_p
                    if radius<2: continue
                    rot=now*(70 if idx%2==0 else -52)+idx*35
                    formation_canvas.create_oval(cx-radius,cy-radius,cx+radius,cy+radius,outline="#123b69",width=1)
                    for j in range(4):
                        st=rot+j*90
                        formation_canvas.create_arc(cx-radius,cy-radius,cx+radius,cy+radius,start=st,extent=32,outline=["#00eaff","#438cff","#a66cff","#ff55c8"][idx],width=4)
                core_p=max(0.0,min((now-4.0)/2.0,1.0))
                if core_p>0:
                    pulse=1+0.08*math.sin(now*12)
                    for r in [110,90,70,52]:
                        rr=r*core_p*pulse; formation_canvas.create_oval(cx-rr,cy-rr,cx+rr,cy+rr,outline="#145d8c",width=2)
                    rr=30+42*core_p; formation_canvas.create_oval(cx-rr,cy-rr,cx+rr,cy+rr,fill="#59edff",outline="#eaffff",width=3)
                v_p=max(0.0,min((now-5.7)/2.2,1.0))
                if v_p>0:
                    scale=0.25+0.75*v_p
                    pts=[(-150*scale,-90*scale),(-75*scale,110*scale),(0,175*scale),(75*scale,110*scale),(150*scale,-90*scale)]
                    pts=[(cx+x,cy+y) for x,y in pts]
                    for k in range(len(pts)-1): formation_canvas.create_line(pts[k],pts[k+1],fill="#00f6ff",width=max(3,int(8*scale)),capstyle="round")
                    formation_canvas.create_text(cx,cy+245*scale,text="VISSHAK",fill="#dfffff",font=("Consolas",max(18,int(40*scale)),"bold"))
                if now>=8.0:
                    formation_canvas.create_text(cx,cy-300,text="VISSHAK // CORE ASSEMBLY",fill="#00f6ff",font=("Consolas",13,"bold"))
                    formation_canvas.create_text(cx,cy+315,text="SYSTEM ONLINE  •  BOSS LINK ACTIVE",fill="#8c7cff",font=("Consolas",11,"bold"))
                sy=(now*420)%h; formation_canvas.create_line(0,sy,w,sy,fill="#0e5272",width=2)
                for t,sound in sound_schedule:
                    if now>=t and (t,sound) not in played:
                        played.add((t,sound)); threading.Thread(target=play_startup_sfx,args=(sound,),daemon=True).start()
                if now<STARTUP_FORMATION_SECONDS:
                    formation_overlay.after(16,draw)
                else:
                    stop_startup_sfx(); formation_overlay.destroy(); formation_overlay=None; root.deiconify(); root.lift()
                    try: root.attributes("-topmost",True); root.after(300,lambda:root.attributes("-topmost",False))
                    except Exception: pass
                    if os.environ.get("VISSHAK_BACKGROUND")=="1": root.after(int(STARTUP_INTERFACE_SECONDS*1000),lambda:root.withdraw())
            except Exception as e:
                print("Formation animation error:",e)
                try: formation_overlay.destroy()
                except Exception: pass
                formation_overlay=None; root.deiconify()
        formation_overlay.after(100,draw)
    except Exception as e:
        print("Formation startup error:",e)
        try: root.deiconify()
        except Exception: pass


# =========================================================
# ANIMATED NEURAL CORE
# =========================================================

def animate_core():

    global animation_angle
    global pulse_value
    global scan_offset
    global particle_angle

    try:

        canvas.delete(
            "all"
        )

        width = max(
            canvas.winfo_width(),
            500
        )

        height = max(
            canvas.winfo_height(),
            500
        )

        cx = width / 2
        cy = height / 2

        animation_angle += 1.8
        pulse_value += 0.09
        scan_offset += 4
        particle_angle += 1.2

        # GRID

        for x in range(
            0,
            width,
            32
        ):

            canvas.create_line(
                x,
                0,
                x,
                height,
                fill=GRID
            )

        for y in range(
            0,
            height,
            32
        ):

            canvas.create_line(
                0,
                y,
                width,
                y,
                fill=GRID
            )

        # SCAN LINE

        scan_y = (
            scan_offset
            % height
        )

        canvas.create_line(
            0,
            scan_y,
            width,
            scan_y,
            fill="#25255e",
            width=2
        )

        # CORNER BRACKETS

        corner = 48
        pad = 20

        brackets = [

            (
                pad,
                pad,
                pad + corner,
                pad
            ),

            (
                pad,
                pad,
                pad,
                pad + corner
            ),

            (
                width - pad,
                pad,
                width - pad - corner,
                pad
            ),

            (
                width - pad,
                pad,
                width - pad,
                pad + corner
            ),

            (
                pad,
                height - pad,
                pad + corner,
                height - pad
            ),

            (
                pad,
                height - pad,
                pad,
                height - pad - corner
            ),

            (
                width - pad,
                height - pad,
                width - pad - corner,
                height - pad
            ),

            (
                width - pad,
                height - pad,
                width - pad,
                height - pad - corner
            )
        ]

        for x1, y1, x2, y2 in brackets:

            canvas.create_line(
                x1,
                y1,
                x2,
                y2,

                fill=(
                    PURPLE
                    if int(
                        animation_angle / 10
                    ) % 2
                    else CYAN
                ),

                width=3
            )

        outer = (
            min(width, height)
            * 0.39
        )

        # OUTER RING

        canvas.create_oval(
            cx - outer,
            cy - outer,
            cx + outer,
            cy + outer,

            outline="#20205c",
            width=1
        )

        # ROTATING ARCS

        arc_colors = [
            CYAN,
            BLUE,
            PURPLE,
            PINK,
            CYAN
        ]

        for i in range(6):

            start = (
                animation_angle
                * (
                    1
                    if i % 2 == 0
                    else -1
                )
                + i * 60
            )

            canvas.create_arc(

                cx - outer,
                cy - outer,
                cx + outer,
                cy + outer,

                start=start,

                extent=38 + i * 2,

                outline=arc_colors[
                    i % len(arc_colors)
                ],

                width=(
                    4
                    if i == 2
                    else 2
                ),

                style="arc"
            )

        # TECHNICAL TICKS

        for i in range(36):

            angle = math.radians(
                animation_angle * 1.1
                + i * 10
            )

            r1 = outer - 5

            r2 = (
                outer - 20
                if i % 3 == 0
                else outer - 11
            )

            x1 = (
                cx
                + math.cos(angle)
                * r1
            )

            y1 = (
                cy
                + math.sin(angle)
                * r1
            )

            x2 = (
                cx
                + math.cos(angle)
                * r2
            )

            y2 = (
                cy
                + math.sin(angle)
                * r2
            )

            canvas.create_line(
                x1,
                y1,
                x2,
                y2,

                fill=[
                    CYAN,
                    BLUE,
                    PURPLE
                ][i % 3],

                width=2
            )

        # MIDDLE RINGS

        middle_colors = [
            CYAN,
            PURPLE,
            PINK,
            BLUE
        ]

        for i, radius in enumerate(
            [190, 164, 138, 112]
        ):

            wobble = (
                math.sin(
                    pulse_value + i
                )
                * 3
            )

            canvas.create_oval(

                cx - radius - wobble,
                cy - radius + wobble,
                cx + radius + wobble,
                cy + radius - wobble,

                outline=middle_colors[i],

                width=2
            )

        # PARTICLES

        particle_colors = [
            CYAN,
            BLUE,
            PURPLE,
            PINK,
            GREEN
        ]

        for i in range(48):

            angle = math.radians(
                particle_angle
                + i * 7.5
            )

            radius = (
                105
                + math.sin(
                    pulse_value * 2 + i
                ) * 65
            )

            x = (
                cx
                + math.cos(angle)
                * radius
            )

            y = (
                cy
                + math.sin(angle)
                * radius
            )

            size = (
                1.5
                + (
                    math.sin(
                        pulse_value * 3 + i
                    ) + 1
                )
            )

            canvas.create_oval(

                x - size,
                y - size,
                x + size,
                y + size,

                fill=particle_colors[
                    i % len(particle_colors)
                ],

                outline=""
            )

        # INNER ARCS

        for i in range(5):

            start = (
                -animation_angle
                * (i + 1)
                + i * 72
            )

            canvas.create_arc(

                cx - 122,
                cy - 122,
                cx + 122,
                cy + 122,

                start=start,

                extent=58,

                outline=[
                    CYAN,
                    PURPLE,
                    PINK,
                    BLUE,
                    CYAN
                ][i],

                width=3,

                style="arc"
            )

        # CORE GLOW

        glow_sizes = [
            100,
            88,
            76,
            64,
            52
        ]

        glow_colors = [
            "#101044",
            "#17215f",
            "#163c83",
            "#4b249b",
            CYAN
        ]

        for radius, color in zip(
            glow_sizes,
            glow_colors
        ):

            canvas.create_oval(

                cx - radius,
                cy - radius,
                cx + radius,
                cy + radius,

                fill=DEEP,

                outline=color,

                width=2
            )

        # ENERGY CORE

        core_radius = (
            31
            + math.sin(
                pulse_value * 2
            ) * 3
        )

        canvas.create_oval(

            cx - core_radius,
            cy - core_radius,
            cx + core_radius,
            cy + core_radius,

            fill=CYAN,

            outline=WHITE,

            width=2
        )

        canvas.create_text(

            cx,
            cy,

            text="V",

            font=(
                "Segoe UI",
                32,
                "bold"
            ),

            fill="#001014"
        )

        canvas.create_text(

            cx,
            cy - outer - 18,

            text="NEURAL CORE // ONLINE",

            font=(
                "Consolas",
                9,
                "bold"
            ),

            fill=CYAN
        )

        canvas.create_text(

            cx,
            cy + outer + 18,

            text="VISSHAK // BOSS LINK ACTIVE",

            font=(
                "Consolas",
                9,
                "bold"
            ),

            fill=PURPLE
        )

        status_color = (

            GREEN
            if status_value
            in (
                "LISTENING",
                "READY"
            )

            else YELLOW
            if status_value == "SPEAKING"

            else PURPLE
            if status_value == "THINKING"

            else CYAN
        )

        canvas.create_text(

            cx,
            cy + outer + 38,

            text=status_value,

            font=(
                "Consolas",
                10,
                "bold"
            ),

            fill=status_color
        )

        if running:

            root.after(
                30,
                animate_core
            )

    except Exception as e:

        print(
            "Animation error:",
            e
        )


# =========================================================
# HEADER
# =========================================================

header = tk.Frame(
    root,
    bg=BG
)

header.pack(
    fill="x",
    padx=24,
    pady=(14, 6)
)


title = tk.Label(

    header,

    text="VISSHAK",

    font=(
        "Segoe UI",
        31,
        "bold"
    ),

    fg=CYAN,

    bg=BG
)

title.pack(
    side="left"
)


subtitle = tk.Label(

    header,

    text=(
        "NEURAL COMMAND SYSTEM  //  "
        "JARVIS × ULTRON × VISSHAK"
    ),

    font=(
        "Consolas",
        9
    ),

    fg=MUTED,

    bg=BG
)

subtitle.pack(
    side="left",
    padx=16,
    pady=12
)


mode_label = tk.Label(

    header,

    text="VOICE ONLINE",

    font=(
        "Consolas",
        9,
        "bold"
    ),

    fg=GREEN,

    bg=BG
)

mode_label.pack(
    side="right",
    padx=18
)


status_label = tk.Label(

    header,

    text="● INITIALIZING",

    font=(
        "Consolas",
        10,
        "bold"
    ),

    fg=GREEN,

    bg=BG
)

status_label.pack(
    side="right"
)


# =========================================================
# MAIN AREA
# =========================================================

main = tk.Frame(
    root,
    bg=BG
)

main.pack(
    fill="both",
    expand=True,
    padx=24,
    pady=8
)


# =========================================================
# LEFT PANEL
# =========================================================

left = tk.Frame(

    main,

    bg=PANEL,

    width=600,

    highlightbackground="#24245f",

    highlightthickness=1
)

left.pack(
    side="left",
    fill="both",
    padx=(0, 10)
)

left.pack_propagate(
    False
)


core_title = tk.Label(

    left,

    text="◈  VISSHAK NEURAL CORE",

    font=(
        "Consolas",
        10,
        "bold"
    ),

    fg=PURPLE,

    bg=PANEL
)

core_title.pack(
    pady=(13, 0)
)


canvas = tk.Canvas(

    left,

    bg=PANEL,

    highlightthickness=0
)

canvas.pack(
    fill="both",
    expand=True,
    padx=8,
    pady=4
)


# =========================================================
# VOICE BUTTON
# =========================================================

voice_button = tk.Button(

    left,

    text="◉  VOICE MODE  /  ON",

    command=toggle_voice,

    font=(
        "Segoe UI",
        10,
        "bold"
    ),

    fg=GREEN,

    bg="#102d23",

    activebackground="#194837",

    activeforeground=GREEN,

    relief="flat",

    bd=0,

    cursor="hand2"
)

voice_button.pack(
    fill="x",
    padx=42,
    pady=(0, 7),
    ipady=10
)


# =========================================================
# SOUND BUTTON
# =========================================================

sound_button = tk.Button(

    left,

    text="🔊  VOICE SOUND  /  ON",

    command=toggle_sound,

    font=(
        "Segoe UI",
        10,
        "bold"
    ),

    fg=GREEN,

    bg="#102d23",

    activebackground="#194837",

    activeforeground=GREEN,

    relief="flat",

    bd=0,

    cursor="hand2"
)

sound_button.pack(
    fill="x",
    padx=42,
    pady=(0, 7),
    ipady=10
)


sound_status = tk.Label(

    left,

    text="VOICE SOUND: ON",

    font=(
        "Consolas",
        8,
        "bold"
    ),

    fg=GREEN,

    bg=PANEL
)

sound_status.pack(
    pady=(0, 2)
)


voice_hint = tk.Label(

    left,

    text=(
        "BOSS is the wake word  //  "
        "Voice recognition and sound are separate"
    ),

    font=(
        "Consolas",
        8
    ),

    fg=MUTED,

    bg=PANEL
)

voice_hint.pack(
    pady=(0, 15)
)


# =========================================================
# RIGHT PANEL
# =========================================================

right = tk.Frame(

    main,

    bg=PANEL,

    highlightbackground="#24245f",

    highlightthickness=1
)

right.pack(
    side="right",
    fill="both",
    expand=True
)


terminal_title = tk.Label(

    right,

    text="◈  VISSHAK COMMAND TERMINAL",

    font=(
        "Consolas",
        10,
        "bold"
    ),

    fg=PURPLE,

    bg=PANEL
)

terminal_title.pack(
    anchor="w",
    padx=20,
    pady=(13, 7)
)


# =========================================================
# CHAT TERMINAL
# =========================================================

chat = scrolledtext.ScrolledText(

    right,

    bg="#02030b",

    fg=TEXT,

    font=(
        "Consolas",
        10
    ),

    insertbackground=CYAN,

    relief="flat",

    bd=0,

    wrap="word"
)

chat.pack(
    fill="both",
    expand=True,
    padx=16,
    pady=(0, 8)
)


chat.tag_config(
    "user",
    foreground=GREEN
)

chat.tag_config(
    "visshak",
    foreground=CYAN
)

chat.tag_config(
    "time",
    foreground="#4e5686"
)

chat.config(
    state="disabled"
)


# =========================================================
# TEXT COMMAND PANEL
# =========================================================

text_command_panel = tk.Frame(

    right,

    bg=PANEL2,

    highlightbackground="#34347c",

    highlightthickness=1
)

text_command_panel.pack(
    fill="x",
    padx=16,
    pady=(0, 15)
)


text_mode_title = tk.Label(

    text_command_panel,

    text="▣  TEXT COMMAND INTERFACE",

    font=(
        "Consolas",
        9,
        "bold"
    ),

    fg=CYAN,

    bg=PANEL2
)

text_mode_title.pack(
    anchor="w",
    padx=12,
    pady=(8, 3)
)


text_hint = tk.Label(

    text_command_panel,

    text=(
        "Text box is always available  //  "
        "Toggle TEXT MODE to type without BOSS"
    ),

    font=(
        "Consolas",
        8
    ),

    fg=MUTED,

    bg=PANEL2
)

text_hint.pack(
    anchor="w",
    padx=12,
    pady=(0, 6)
)


input_frame = tk.Frame(

    text_command_panel,

    bg=PANEL2
)

input_frame.pack(
    fill="x",
    padx=10,
    pady=(0, 10)
)


command_entry = tk.Entry(

    input_frame,

    bg="#02030b",

    fg=WHITE,

    insertbackground=CYAN,

    font=(
        "Segoe UI",
        13,
        "bold"
    ),

    relief="flat",

    bd=0
)

command_entry.pack(
    side="left",
    fill="x",
    expand=True,
    ipady=14,
    padx=(0, 10)
)


command_entry.insert(
    0,
    "Type command here..."
)

command_entry.config(
    fg="#59618c"
)


# =========================================================
# TEXT PLACEHOLDER
# =========================================================

def clear_placeholder(event=None):

    if (
        command_entry.get()
        == "Type command here..."
    ):

        command_entry.delete(
            0,
            "end"
        )

        command_entry.config(
            fg=WHITE
        )


def restore_placeholder(event=None):

    if not command_entry.get().strip():

        command_entry.insert(
            0,
            "Type command here..."
        )

        command_entry.config(
            fg="#59618c"
        )


command_entry.bind(
    "<FocusIn>",
    clear_placeholder
)

command_entry.bind(
    "<FocusOut>",
    restore_placeholder
)


# =========================================================
# SEND BUTTON
# =========================================================

send_button = tk.Button(

    input_frame,

    text="SEND  ➤",

    command=send_text_command,

    font=(
        "Segoe UI",
        10,
        "bold"
    ),

    fg="#001014",

    bg=CYAN,

    activebackground="#9cffff",

    activeforeground="#001014",

    relief="flat",

    bd=0,

    cursor="hand2",

    padx=26
)

send_button.pack(
    side="right",
    ipady=10
)


command_entry.bind(
    "<Return>",
    lambda event: send_text_command()
)


# =========================================================
# FOOTER
# =========================================================

footer = tk.Frame(
    root,
    bg=BG
)

footer.pack(
    fill="x",
    padx=24,
    pady=(0, 12)
)


footer_left = tk.Label(

    footer,

    text=(
        "SYSTEM: ONLINE   |   "
        "LOCAL AI: OLLAMA   |   "
        "TTS: WINDOWS SAPI   |   "
        "NEON HUD: ACTIVE"
    ),

    font=(
        "Consolas",
        8
    ),

    fg=MUTED,

    bg=BG
)

footer_left.pack(
    side="left"
)


footer_right = tk.Label(

    footer,

    text="F11 FULLSCREEN   |   ESC EXIT",

    font=(
        "Consolas",
        8
    ),

    fg=MUTED,

    bg=BG
)

footer_right.pack(
    side="right"
)


# =========================================================
# CLOSE APPLICATION
# =========================================================

def on_close():

    global running
    global voice_enabled

    running = False
    voice_enabled = False

    try:

        sd.stop()

    except Exception:

        pass

    close_youtube()

    try:

        root.destroy()

    except Exception:

        pass


root.protocol(
    "WM_DELETE_WINDOW",
    on_close
)


# =========================================================
# KEYBOARD SHORTCUTS
# =========================================================

root.bind(
    "<F11>",
    fullscreen_toggle
)

root.bind(
    "<Escape>",
    exit_fullscreen
)


# =========================================================
# STARTUP MESSAGES
# =========================================================

add_chat(
    "VISSHAK",
    "Neural command system initialized."
)

add_chat(
    "VISSHAK",
    "Voice recognition and text systems ready."
)

add_chat(
    "VISSHAK",
    "Voice sound can be turned ON/OFF independently."
)

add_chat(
    "VISSHAK",
    "Say BOSS followed by a command, or use the text box."
)


# =========================================================
# STARTUP VOICE
# =========================================================

def startup():

    # Wait until the formation + short interface reveal has completed.
    time.sleep(
        STARTUP_FORMATION_SECONDS + STARTUP_INTERFACE_SECONDS + 0.5
    )

    if not running:

        return

    speak(
        "Visshak activated. "
        "All systems are online. "
        "How can I assist you, Boss?"
    )

    set_status(
        "LISTENING"
        if voice_enabled
        else "TEXT MODE"
    )


# =========================================================
# WINDOWS AUTO START
# =========================================================

def install_autostart():
    try:
        startup_dir = os.path.join(os.environ.get("APPDATA", ""), "Microsoft", "Windows", "Start Menu", "Programs", "Startup")
        if not startup_dir or not os.path.isdir(startup_dir):
            return
        script_path = os.path.abspath(__file__)
        python_exe = sys.executable
        pythonw_exe = os.path.join(os.path.dirname(python_exe), "pythonw.exe")
        if not os.path.exists(pythonw_exe):
            pythonw_exe = python_exe
        bat_path = os.path.join(startup_dir, "VISSHAK_AutoStart.bat")
        bat = ("@echo off\n" f'cd /d "{os.path.dirname(script_path)}"\n' "set VISSHAK_BACKGROUND=1\n" f'start "" /min "{pythonw_exe}" "{script_path}"\n')
        with open(bat_path, "w", encoding="utf-8") as file:
            file.write(bat)
        print("AUTO START: VISSHAK background startup enabled.")
    except Exception as e:
        print("AUTO START ERROR:", e)


def setup_tailscale_https():
    try:
        tailscale_exe = r"C:\Program Files\Tailscale\tailscale.exe"
        if not os.path.exists(tailscale_exe):
            print("TAILSCALE: tailscale.exe not found.")
            return

        # Tailscale Serve gives the phone a valid HTTPS URL while keeping
        # the Python server private on localhost.
        subprocess.run(
            [tailscale_exe, "serve", "--bg", str(REMOTE_PORT)],
            capture_output=True,
            text=True,
            timeout=20
        )

        status = subprocess.run(
            [tailscale_exe, "serve", "status"],
            capture_output=True,
            text=True,
            timeout=10
        )

        output = (status.stdout or status.stderr).strip()
        print("TAILSCALE SERVE STATUS:")
        print(output)

        # Also retrieve the MagicDNS name so the exact phone URL is obvious.
        info = subprocess.run(
            [tailscale_exe, "status", "--json"],
            capture_output=True,
            text=True,
            timeout=10
        )

        data = json.loads(info.stdout)
        dns_name = str(data.get("Self", {}).get("DNSName", "")).rstrip(".")

        if dns_name:
            url = "https://" + dns_name
            print("PHONE URL:", url)
            ui_call(add_chat, "VISSHAK", "Phone HTTPS access ready: " + url)

    except Exception as e:
        print("TAILSCALE HTTPS setup error:", e)


# =========================================================
# START ENGINES
# =========================================================

def start_engines():

    if ENABLE_AUTOSTART:
        install_autostart()

    time.sleep(
        2
    )

    if not running:

        return

    # Remote phone server
    start_remote_server()

    # Publish the local server through Tailscale HTTPS.
    setup_tailscale_https()

    # Command worker

    threading.Thread(
        target=command_worker,
        daemon=True
    ).start()

    # Voice recognition

    threading.Thread(
        target=voice_loop,
        daemon=True
    ).start()


# =========================================================
# STARTUP FORMATION + MAIN HUD
# =========================================================

try:
    root.withdraw()
except Exception:
    pass

start_formation_sequence()
animate_core()


# =========================================================
# STARTUP THREADS
# =========================================================

threading.Thread(
    target=startup,
    daemon=True
).start()

threading.Thread(
    target=start_engines,
    daemon=True
).start()


# =========================================================
# RUN VISSHAK
# =========================================================

root.mainloop()
