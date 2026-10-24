# VISSHAK – AI Personal Assistant

VISSHAK is a Python-based, JARVIS-inspired Windows desktop assistant that combines voice commands, local AI responses, persistent memory, PC automation, YouTube controls, and optional mobile access through Tailscale.

## Features

- Futuristic Tkinter graphical interface
- Wake-word voice commands
- Local AI responses using Ollama and Llama 3.2
- Persistent memory stored locally in `memory.json`
- Windows app launching and system controls
- Volume controls
- YouTube playback automation using Playwright
- Optional phone interface through Tailscale Serve
- Keyboard shortcuts and startup animation

## Technology

- Python
- Tkinter
- Ollama (`llama3.2`)
- SpeechRecognition and SoundDevice
- Playwright
- Pycaw
- Tailscale (optional remote access)

## Requirements

- Windows 10/11
- Python 3.10+ recommended (test with your installed version)
- Ollama installed with the `llama3.2` model available
- Microphone and speakers for voice interaction
- Internet access for `SpeechRecognition`'s Google speech-recognition service
- Chrome/Playwright browser support for YouTube automation
- Tailscale configured only if you want phone access

## Setup

1. Install Python and make sure `python` works in PowerShell.
2. Install Ollama from its official website and download the model:

   ```powershell
   ollama pull llama3.2
   ```

3. Open PowerShell inside this project folder and create a virtual environment:

   ```powershell
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```

4. Install dependencies:

   ```powershell
   python -m pip install --upgrade pip
   pip install -r requirements.txt
   ```

5. Install the Playwright Chromium browser if required:

   ```powershell
   python -m playwright install chromium
   ```

6. Start Ollama, then launch VISSHAK:

   ```powershell
   python main.py
   ```

## Privacy and Safety

- `memory.json` may contain personal details. It is excluded from Git by `.gitignore`; do not upload it.
- Browser profiles and logs are also excluded.
- Windows auto-start is disabled by default. If you intentionally want it, change `ENABLE_AUTOSTART = False` to `True` in `main.py`.
- Voice recognition uses Google's speech-recognition service and therefore needs internet; this project is not fully offline.
- Remote phone access is optional and depends on Tailscale configuration. Keep your tailnet access restricted to trusted devices/users. A per-run authorization token is used for the mobile command endpoint.
- Commands that affect the PC should be tested carefully on your own Windows system.

## Project Status

Personal/student development project. Hardware, Windows, microphone, browser, Ollama, and Tailscale behavior must be tested on the target computer; syntax validation alone does not guarantee every feature will work.

## License

No license has been selected yet. Add a license only after choosing how others may use, modify, and redistribute the project.
