# Project Architecture & Module Specifications

## 1. System Overview
This application is a production-quality desktop application (PySide6 + SQLite + Asyncio + Anthropic-compatible API) for generating complete, coherent YouTube content packages (Title, Clean Voice-over Script, Detailed Image Prompts with Visual Continuity).

All backend layers are complete and fully tested with 100% test pass rate across 37 cases. Next up is UI Implementation in PySide6.

## 2. Directory Structure
```
H:\Automation\Content Automation\
├── requirements.txt
├── venv/
├── src/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── config/              # Configuration & Settings Management
│   │   │   ├── __init__.py
│   │   │   ├── settings.py
│   │   │   └── models.py
│   │   ├── db/                  # SQLite Persistence & Migrations
│   │   │   ├── __init__.py
│   │   │   ├── database.py
│   │   │   └── schema.sql
│   │   ├── ai/                  # AI Client, Rate Limiter & Profiles
│   │   │   ├── __init__.py
│   │   │   ├── client.py
│   │   │   ├── rate_limiter.py
│   │   │   ├── retry.py
│   │   │   └── usage.py
│   │   ├── models/              # System Models & Schemas
│   │   │   ├── __init__.py
│   │   │   ├── preset.py
│   │   │   ├── enums.py
│   │   │   ├── api_profile.py
│   │   │   ├── generation.py
│   │   │   └── job.py
│   │   ├── prompts/             # Modular Prompt Composition System
│   │   │   ├── __init__.py
│   │   │   ├── builder.py
│   │   │   ├── parser.py
│   │   │   └── templates.py
│   │   ├── pipeline/            # Multi-stage Generation & Critics
│   │   │   ├── __init__.py
│   │   │   ├── pipeline.py
│   │   │   ├── duplicate_checker.py
│   │   │   └── stages/
│   │   │       ├── title_stage.py
│   │   │       ├── script_stage.py
│   │   │       ├── scene_stage.py
│   │   │       ├── image_prompt_stage.py
│   │   │       └── final_review_stage.py
│   │   ├── orchestrator/        # Batch, Queue, State Machine & Resumability
│   │   │   ├── __init__.py
│   │   │   ├── engine.py
│   │   │   ├── event_bus.py
│   │   │   └── queue.py
│   │   ├── storage/             # Safe Disk Storage, Path Sanitization & Validation
│   │   │   ├── __init__.py
│   │   │   ├── exporter.py
│   │   │   └── sanitizer.py
│   │   ├── ui/                  # PySide6 Modern Dark/Light Desktop Interface
│   │   │   ├── __init__.py
│   │   │   ├── app.py
│   │   │   ├── main_window.py
│   │   │   ├── components/
│   │   │   ├── styles/
│   │   │   └── views/
│   │   └── utils/               # Logging, Threading & Helpers
│   │       ├── __init__.py
│   │       └── logging.py
│   └── tests/
│       ├── __init__.py
│       ├── test_db.py
│       ├── test_ai_client.py
│       ├── test_rate_limiter.py
│       ├── test_pipeline.py
│       ├── test_models.py
│       ├── test_prompts.py
│       ├── test_storage.py
│       └── test_orchestrator.py
```
