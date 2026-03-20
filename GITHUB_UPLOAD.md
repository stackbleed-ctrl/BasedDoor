# 🍁 BasedDoor — GitHub Upload & Extraction Instructions

Complete walkthrough: from the ZIP file you downloaded to a live, HACS-installable
public GitHub repository in under 15 minutes.

---

## Part 1 — Prerequisites

Install these on your local machine before starting:

```bash
# macOS (Homebrew)
brew install git gh unzip

# Ubuntu / Debian
sudo apt install git gh unzip -y

# Windows (PowerShell — run as Administrator)
winget install Git.Git GitHub.cli
```

Verify:
```bash
git --version    # should be 2.x
gh --version     # should be 2.x
```

---

## Part 2 — Extract the ZIP

### macOS / Linux

```bash
# Move the ZIP to your projects folder
mv ~/Downloads/BasedDoor.zip ~/projects/

# Extract
cd ~/projects
unzip BasedDoor.zip

# Verify structure
ls -la BasedDoor/
```

You should see:
```
BasedDoor/
├── custom_components/baseddoor/
├── docs/
├── prompts/
├── mobile/
├── automations/
├── scripts/
├── tests/
├── hacs.json
├── README.md
├── LICENSE
├── pytest.ini
├── requirements-dev.txt
└── .github/workflows/
```

### Windows (PowerShell)

```powershell
# Extract
Expand-Archive -Path "$HOME\Downloads\BasedDoor.zip" -DestinationPath "$HOME\projects\"

# Verify
Get-ChildItem "$HOME\projects\BasedDoor\"
```

---

## Part 3 — Initialise the Local Git Repository

```bash
cd ~/projects/BasedDoor

# Initialise git
git init

# Set your identity (skip if already configured globally)
git config user.name  "StackBleed"
git config user.email "you@example.com"

# Stage everything
git add .

# Verify what's staged (should show all files, .enc files excluded by .gitignore)
git status

# First commit
git commit -m "feat: initial BasedDoor release v0.1.0

Local AI door sentinel for Home Assistant.
Charter s.7/s.8 rights-based auto-response.
Warrant document scanner (OCR + LLM sanity check).
Piper TTS + Ollama LLM + LLaVA vision.
Zero cloud. Zero telemetry."
```

---

## Part 4 — Create the GitHub Repository

### Option A — GitHub CLI (Fastest)

```bash
# Authenticate (one-time)
gh auth login
# → Choose: GitHub.com → HTTPS → Login with a web browser → follow prompts

# Create repo and push in one command
gh repo create BasedDoor \
  --public \
  --description "🍁 Local AI door sentinel. Charter s.7/s.8 rights-based auto-response. Zero cloud." \
  --homepage "https://github.com/StackBleed/BasedDoor" \
  --push \
  --source=.

# Add topics for discoverability
gh repo edit StackBleed/BasedDoor \
  --add-topic "home-assistant" \
  --add-topic "hacs" \
  --add-topic "privacy" \
  --add-topic "charter-rights" \
  --add-topic "ollama" \
  --add-topic "local-ai" \
  --add-topic "canada"
```

Done. Your repo is live at `https://github.com/StackBleed/BasedDoor`.

---

### Option B — GitHub Web UI

1. Go to **https://github.com/new**
2. Fill in:
   - **Repository name:** `BasedDoor`
   - **Description:** `🍁 Local AI door sentinel. Charter s.7/s.8 rights-based auto-response. Zero cloud.`
   - **Visibility:** ✅ Public
   - **DO NOT** check "Add README", "Add .gitignore", or "Choose a license" — you already have these
3. Click **Create repository**
4. Copy the SSH or HTTPS remote URL shown on the next page

Then back in your terminal:

```bash
cd ~/projects/BasedDoor

# Add the remote (replace URL with yours)
git remote add origin https://github.com/StackBleed/BasedDoor.git

# Push
git branch -M main
git push -u origin main
```

---

## Part 5 — Verify the Repository

```bash
# Open in browser
gh browse
# or
open https://github.com/StackBleed/BasedDoor
```

Check:
- [ ] README.md renders with badges and feature table
- [ ] `custom_components/baseddoor/` directory visible
- [ ] `hacs.json` present at repo root
- [ ] `LICENSE` file visible
- [ ] `.github/workflows/hacs_validate.yml` present
- [ ] CI badge shows (may take a minute for first run)

---

## Part 6 — Add BasedDoor to HACS (Test Your Install)

Before announcing, verify the HACS install flow works end-to-end on your own HA instance.

1. In Home Assistant: **HACS → Custom Repositories**
2. Add: `https://github.com/StackBleed/BasedDoor`
3. Category: **Integration**
4. Click **Add**
5. Go to **HACS → Integrations → Explore & Download Repositories**
6. Search **BasedDoor**
7. Click **Download**
8. Restart Home Assistant
9. **Settings → Devices & Services → Add Integration → BasedDoor**

If the config flow appears: ✅ HACS install confirmed working.

---

## Part 7 — Submit to HACS Default Repository (Optional but Recommended)

Getting into the HACS default repo means one-click discovery for all HACS users.

Requirements:
- Repo is public
- `hacs.json` is valid
- `manifest.json` passes `hassfest`
- CI is green
- At least 1 release/tag published

```bash
# Create v0.1.0 release tag
git tag -a v0.1.0 -m "BasedDoor v0.1.0 — initial release"
git push origin v0.1.0

# Create GitHub release
gh release create v0.1.0 \
  --title "BasedDoor v0.1.0" \
  --notes "Initial release. Local AI door sentinel for Home Assistant.
- Charter s.7/s.8 auto-response via Piper TTS + Ollama
- LLaVA vision for uniform/badge detection
- Warrant document scanner (OCR + LLM sanity check)
- Four response modes: Polite / Based / Maximum Refusal / User Clip
- Encrypted local logging
- Ring doorbell support (with caveats) + local RTSP recommended
- Android mobile app (beta)"
```

Then open a PR against:
`https://github.com/hacs/default`

File: `integrations` — add one line:
```
StackBleed/BasedDoor
```

---

## Part 8 — Future Updates

When you make changes and want to push:

```bash
cd ~/projects/BasedDoor

# Stage changed files
git add .

# Commit with a descriptive message
git commit -m "feat: add French language support"

# Push to GitHub
git push

# Bump version when ready for a new HACS release
# 1. Update version in custom_components/baseddoor/manifest.json
# 2. Tag and release:
git tag -a v0.2.0 -m "BasedDoor v0.2.0"
git push origin v0.2.0
gh release create v0.2.0 --title "v0.2.0" --generate-notes
```

HACS picks up the new version automatically within a few hours via GitHub release tags.

---

## Part 9 — Running the Tests Locally

```bash
cd ~/projects/BasedDoor

# Install test dependencies
pip install -r requirements-dev.txt

# Run full test suite
pytest tests/ -v

# Run with coverage report
pytest tests/ --cov=custom_components/baseddoor --cov-report=term-missing

# Run a specific test file
pytest tests/test_encryption.py -v
pytest tests/test_warrant_scanner.py -v
pytest tests/test_input_sanitisation.py -v
```

Expected output on a clean run:
```
tests/test_encryption.py          ........  PASSED
tests/test_llm_engine.py          ..........PASSED
tests/test_vision.py              ..........PASSED
tests/test_warrant_scanner.py     ..........PASSED
tests/test_modes.py               ..........PASSED
tests/test_config_flow.py         ........  PASSED
tests/test_input_sanitisation.py  ..........PASSED
```

Note: tests that call Ollama/Piper/Whisper (marked `asyncio`) will pass even
when those services are offline — they test the fallback and error-handling paths,
not live AI output.

---

## Part 10 — Launch Checklist

Before posting the X thread:

- [ ] Repo is public at `github.com/StackBleed/BasedDoor`
- [ ] CI is green (HACS validate + hassfest + ruff lint)
- [ ] HACS custom repo install tested and confirmed working on your HA
- [ ] v0.1.0 release tag published
- [ ] Record a 30-60 second demo video: mock knock → TTS response → HA notification
- [ ] Post X thread (draft below)

---

## X Launch Thread (Copy-Paste Ready)

```
After a police knock-and-chat over a tweet (no warrant, no emergency),
I built BasedDoor:

A local AI that answers my door with Charter s.7/s.8 max refusal.
No cloud. No OpenAI. HACS-ready.

🚪 github.com/StackBleed/BasedDoor

🧵 1/5

---

What it does:
🗣️ Speaks Charter rights to whoever knocked (Piper TTS)
👁️ Detects uniforms via local vision AI (LLaVA)
📄 Scans warrant docs held to the camera — OCR + sanity check
📼 Logs everything locally, encrypted
📵 Zero cloud. Zero Amazon. Zero cooperation.

2/5

---

Stack:
→ Home Assistant custom integration (HACS one-click)
→ Ollama (llama3.2:3b) for responses
→ LLaVA 7b for vision
→ Piper TTS for voice
→ Whisper STT for transcription
→ Fernet AES encryption for logs

All local. All offline. All yours.

3/5

---

Four response modes:
🍁 Polite Canadian — firm but warm
⚡ Grok-Based — no warrant, no consent, bye
🔴 Maximum Refusal — full s.7/s.8 recitation
🎙️ User Clip — your own recorded voice

Auto-escalates at night or if uniform detected.

4/5

---

Install in 60 seconds:
HACS → Custom Repositories →
github.com/StackBleed/BasedDoor

Docs, Charter cheat sheet, hardware guide included.
Ditch Ring. Use a local RTSP cam.

Who's testing? 🚪🤖🇨🇦

#HomeAssistant #Privacy #CharterRights #HACS

5/5
```

---

*Ship it. Sydney's about to get loud. 🍁*
