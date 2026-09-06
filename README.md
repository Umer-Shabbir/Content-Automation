# Content Automation

A desktop application (built with PySide6, SQLite, Asyncio, and Anthropic-compatible API) for generating YouTube content packages—including high-retention titles, clean voiceover narration scripts, and image prompts with visual continuity.

---

## Prerequisites

- **Python:** `3.10` or higher (`3.11` / `3.12` recommended)
- **Operating System:** Windows 10/11, macOS (12+), or Linux (Ubuntu 20.04+, Debian 11+, Fedora 36+)
  - *Linux note:* A desktop environment (X11 / Wayland) or offscreen framebuffer (`libegl1`, `libgl1`, `libxkbcommon0`) is required for Qt UI rendering.
- **Git** (for cloning)
- **AI API Access:** An Anthropic API key (or an Anthropic-compatible local/remote proxy)

---

## Quick Start (Fresh Clone)

### 1. Clone the Repository
```bash
git clone <repository-url>
cd "Content Automation"
```

### 2. Configure Environment Variables
Copy the example environment file and add your credentials:
```bash
# Windows (PowerShell / CMD)
copy .env.example .env

# macOS / Linux
cp .env.example .env
```
Edit `.env` and set your `ANTHROPIC_API_KEY` (and optional base URL or output directory).

### 3. Create Virtual Environment & Install Dependencies

**Windows (PowerShell):**
```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install --upgrade pip
pip install -r requirements.txt
```

**macOS / Linux:**
```bash
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

### 4. Launch the Application

**Using launcher scripts:**
```bash
# Windows
run.bat

# macOS / Linux
chmod +x run.sh
./run.sh
```

**Direct Python command:**
```bash
# With virtual environment activated:
python main.py
```

### 5. Run the Test Suite
```bash
# With virtual environment activated:
pytest
```
*All tests run in headless offscreen mode by default without requiring an open display.*

---

## Environment Variables

All variables are optional with safe defaults, except for `ANTHROPIC_API_KEY` which is required when executing live AI generations.

| Variable | Description | Default | Required? |
| :--- | :--- | :--- | :---: |
| `ANTHROPIC_API_KEY` | Anthropic / Messages API key. | `""` | **Yes** (for live generation) |
| `ANTHROPIC_BASE_URL` | API base URL (official Anthropic or local proxy). | `https://api.anthropic.com` | No |
| `ANTHROPIC_MODEL` | Target Claude model name. | `claude-sonnet-4-6` | No |
| `MAX_CONCURRENT_REQUESTS` | Maximum simultaneous API requests allowed. | `3` | No |
| `OUTPUT_DIR` | Output directory for generated project files. | `./output` | No |
| `DATABASE_PATH` | Path to persistent SQLite database. | `./ideas.db` | No |
| `MASTER_PRESETS_PATH` | Path to master presets registry JSON. | `./presets/master_presets_registry.json` | No |
| `IDEA_SCAN_DIRS` | Semicolon/comma-separated dirs to scan for existing projects. | *(Auto-detected)* | No |
| `AUTOMATION_ROOT` | Parent directory of sibling automation projects. | *(Workspace parent)* | No |

---

## Project Structure

```
Content Automation/
├── .env.example            # Template for environment configuration
├── .gitignore              # Ignores local databases, .env, venv, and outputs
├── README.md               # Quick start, requirements, and environment reference
├── requirements.txt        # Pinned/tested application dependencies
├── main.py                 # Application entry point with self-healing directories
├── run.bat                 # Windows quick launcher
├── run.sh                  # Linux/macOS quick launcher
├── presets/
│   └── master_presets_registry.json  # Bundled 23 style presets
├── src/
│   ├── app/
│   │   ├── ai/             # Anthropic client, rate limiter, token usage tracking
│   │   ├── core/           # Configuration, env loading, runtime self-healing
│   │   ├── db/             # SQLite database coordinator, schema, and idea manager
│   │   ├── models/         # Pydantic models for presets, jobs, and generations
│   │   ├── orchestrator/   # Job queue, batch engine, event bus, workers
│   │   ├── pipeline/       # Multi-stage generation pipeline & duplicate checking
│   │   ├── prompts/        # Prompt templates and builders
│   │   ├── storage/        # Atomic file exporter & filename sanitizer
│   │   └── ui/             # PySide6 desktop UI (views, styles, components)
│   └── tests/              # 109 automated unit, integration, and UI tests
```
