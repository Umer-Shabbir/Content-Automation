# worker.py  v6.0
"""
AccountWorker for Google Flow Studio Batch Pro.
Handles job execution with character consistency tagging, model/aspect-ratio parameter routing, and recovery.
"""

import asyncio
import threading
import time
import queue
from pathlib import Path
from typing import Optional, Dict

from models import Account, Job, JobStatus, AccountStatus, Settings, Workspace, Character
from automator import (
    GoogleFlowAutomator,
    QuotaLimitError, PolicyError,
    LoginExpiredError, SkippedError
)
from queue_manager import QueueManager
from utils import build_final_prompt, generate_filename


class AccountWorker:

    def __init__(
        self,
        account: Account,
        queue_mgr: QueueManager,
        settings: Settings,
        evt_q: queue.Queue,
        characters: Optional[Dict[str, Character]] = None,
    ):
        self.account    = account
        self.queue      = queue_mgr
        self.settings   = settings
        self.evt_q      = evt_q
        self.characters = characters or {}

        self._stop_evt      = threading.Event()
        self._pause_evt     = threading.Event()
        self._skip_evt      = threading.Event()
        self._thread        = None
        self._auto: Optional[GoogleFlowAutomator] = None
        self._topic         = None
        self._profile       = str(Path("profiles") / account.id)
        self._loop          = None

        self._start_time:        float = 0.0
        self._last_success_time: float = 0.0
        self._recovery_count:    int   = 0
        self._force_new_chat:    bool  = False

    # â”€â”€ Control â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

    def start(self):
        self._stop_evt.clear()
        self._start_time = time.time()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def request_stop(self):
        self._stop_evt.set()
        if self._auto:
            self._auto.running = False
        if self._loop and self._loop.is_running():
            try:
                self._loop.call_soon_threadsafe(self._cancel_all_tasks)
            except Exception:
                pass

    def _cancel_all_tasks(self):
        try:
            for task in asyncio.all_tasks(self._loop):
                task.cancel()
        except Exception:
            pass

    def request_pause(self):
        self._pause_evt.set()
        self._emit("status", AccountStatus.PAUSED)

    def request_resume(self):
        self._pause_evt.clear()
        self._emit("status", AccountStatus.RUNNING)

    def request_skip(self):
        self._skip_evt.set()
        if self._auto:
            self._auto.running = False

    def request_recovery(self):
        self._force_new_chat = True
        if self._auto:
            self._auto.running = True

    def reset_recovery_count(self):
        self._recovery_count = 0

    def get_last_success_time(self) -> float:
        return self._last_success_time

    def get_start_time(self) -> float:
        return self._start_time

    def is_running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def join(self, timeout: float = 5.0):
        if self._thread:
            self._thread.join(timeout)

    # â”€â”€ Test helpers â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

    def test_login(self):
        if self._loop and self._auto and self._loop.is_running():
            asyncio.run_coroutine_threadsafe(self._auto.test_login(), self._loop)

    def test_screenshot(self, path: Path):
        if self._loop and self._auto and self._loop.is_running():
            asyncio.run_coroutine_threadsafe(self._auto.test_screenshot(path), self._loop)

    # â”€â”€ Internal â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

    def _emit(self, *args):
        self.evt_q.put((args[0], self.account.id) + args[1:])

    def _log(self, msg: str, level: str = "info"):
        self._emit("log", msg, level)

    def _s(self, attr: str, default=None):
        return getattr(self.settings, attr, default)

    # â”€â”€ Thread entry â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

    def _run(self):
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        try:
            self._loop.run_until_complete(self._main())
        except asyncio.CancelledError:
            self._log("Worker loop cancelled", "info")
        except Exception as e:
            self._log(f"Worker crash: {e}", "error")
            self._emit("status", AccountStatus.ERROR)
        finally:
            try:
                pending = asyncio.all_tasks(self._loop)
                for task in pending:
                    task.cancel()
                if pending:
                    self._loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
                self._loop.run_until_complete(self._loop.shutdown_asyncgens())
            except Exception:
                pass
            self._loop.close()
            self._loop = None
            self._emit("finished")

    # â”€â”€ Workspace helpers â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

    def _current_ws(self) -> Workspace:
        if 0 <= self.account.current_workspace_idx < len(self.account.workspaces):
            return self.account.workspaces[self.account.current_workspace_idx]
        return self.account.workspaces[0]

    def _mark_ws_limited(self):
        ws = self._current_ws()
        ws.exhausted = True
        ws.image_limit_until = time.time() + 86400
        self._emit("ws_exhausted", ws.name)

    def _check_and_update_project_folder(self, folder_path: str):
        if not folder_path:
            return
            
        import json
        from pathlib import Path
        
        folder_jobs = [j for j in self.queue.all_jobs() if getattr(j, 'project_folder', '') == folder_path]
        if not folder_jobs:
            return
            
        all_finished = True
        for j in folder_jobs:
            if j.status not in ("done", "skipped"):
                all_finished = False
                break
                
        if all_finished:
            pjson_path = Path(folder_path) / "project.json"
            if pjson_path.exists():
                try:
                    with open(pjson_path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    
                    is_video = any(getattr(j, 'mode', 'image') == 'video' for j in folder_jobs)
                    stage_name = "VIDEOS_READY" if is_video else "IMAGES_READY"
                    if data.get("stage") != stage_name:
                        data["stage"] = stage_name
                        data["status"] = "COMPLETED"
                        with open(pjson_path, "w", encoding="utf-8") as f:
                            json.dump(data, f, indent=2)
                        self._log(f"Project state advanced to {stage_name} for {Path(folder_path).name}", "info")
                except Exception as e:
                    self._log(f"Error updating project.json for {Path(folder_path).name}: {e}", "warning")

    def _requeue_job(self, job: Job, reason: str):
        job.status              = JobStatus.PENDING
        job.error               = reason
        job.retry_count         = 0
        job.assigned_account_id = ""
        self.queue.update_job(job)
        self._emit("job_requeued", job.id, reason)
        self._log(f"Re-queued #{job.global_index} ({reason})", "warning")

    # â”€â”€ Main loop â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

    async def _main(self):
        color = self.account.color or "#4285F4"

        self._auto = GoogleFlowAutomator(
            profile_dir    = self._profile,
            settings       = self.settings,
            log_callback   = self._log,
            account_color  = color,
            account_name   = self.account.name,
        )
        try:
            await self._auto.start()

            # Google Login wait
            login_timeout = self._s("login_wait_timeout", 150.0)
            if not await self._auto.check_login():
                self._emit("login_req")
                self._emit("status", AccountStatus.LOGIN_REQUIRED)
                self._log(f"Google login required â€” waiting up to {int(login_timeout)}s", "warning")
                waited = 0.0
                poll   = 3.0
                while waited < login_timeout:
                    if self._stop_evt.is_set():
                        return
                    await asyncio.sleep(poll)
                    waited += poll
                    await self._auto.goto_flow()
                    if await self._auto.check_login():
                        self._log("Google login verified âœ…", "success")
                        break
                else:
                    self._log("Google login timeout â€” releasing worker slot", "error")
                    return

            self._emit("status", AccountStatus.RUNNING)
            self._log(f"Running on Google Flow [{self.account.name}]", "info")

            while not self._stop_evt.is_set():
                while self._pause_evt.is_set() and not self._stop_evt.is_set():
                    await asyncio.sleep(self._s("input_poll_interval", 0.30))
                if self._stop_evt.is_set():
                    break

                job = self.queue.get_next_job()
                if not job:
                    self._emit("status", AccountStatus.IDLE)
                    break

                try:
                    await self._process_job(job)
                except asyncio.CancelledError:
                    self._requeue_job(job, "worker_cancelled")
                    raise
                except Exception as e:
                    self._log(f"Unhandled job error: {e}", "error")
                    self._requeue_job(job, f"unhandled_error_{e}")

                if not self._stop_evt.is_set():
                    delay = self._s("delay_between_prompts", 3.0)
                    await asyncio.sleep(delay)

        except asyncio.CancelledError:
            pass
        except Exception as e:
            self._log(f"Fatal worker exception: {e}", "error")
            self._emit("status", AccountStatus.ERROR)
        finally:
            if self._auto:
                try:
                    await self._auto.stop()
                except Exception:
                    pass

    # â”€â”€ Job processing â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

    async def _process_job(self, job: Job):
        self._skip_evt.clear()
        if self._auto:
            self._auto.running = True

        do_new_chat = False
        mode = self._s("new_chat_mode", "per_topic")
        if mode == "per_prompt":
            do_new_chat = True
        elif mode == "per_topic" and job.topic_name != self._topic:
            do_new_chat = True
            self._topic = job.topic_name

        # 1. Resolve character for consistency
        char_name = job.character_name or self._s("active_character_name", "")
        character_obj = self.characters.get(char_name)
        
        # Load preset if specified
        preset_name = self._s("style_preset", "")
        preset_visual_style = ""
        preset_aspect_ratio = ""

        if job.project_folder:
            import json
            pjson_path = Path(job.project_folder) / "project.json"
            if not pjson_path.exists():
                pjson_path = Path(job.project_folder) / "metadata.json"
            
            if pjson_path.exists():
                try:
                    pdata = json.loads(pjson_path.read_text(encoding="utf-8"))
                    preset_name = pdata.get("preset_name", preset_name)
                except Exception:
                    pass
                    
        if preset_name:
            try:
                import json
                registry_path = Path("H:/Automation/Presets/master_presets_registry.json")
                if registry_path.exists():
                    registry = json.loads(registry_path.read_text(encoding="utf-8"))
                    if preset_name in registry:
                        ia = registry[preset_name].get("image_automation", {})
                        preset_visual_style = ia.get("visual_style", "")
                        preset_aspect_ratio = ia.get("aspect_ratio", "")
            except Exception as e:
                self._log(f"Failed to load preset {preset_name}: {e}", "warning")

        # 2. Build final prompt with @Character tag
        final_prompt = build_final_prompt(
            base           = job.prompt_text,
            character_name = char_name,
            prefix         = self._s("prompt_prefix", ""),
            suffix         = self._s("prompt_suffix", ""),
            style          = preset_visual_style or self._s("style_preset", ""),
            aspect_ratio   = preset_aspect_ratio or job.aspect_ratio or self._s("aspect_ratio", "16:9"),
        )

        target_mode = getattr(job, 'mode', None) or self._s("generation_mode", "image")

        if job.project_folder:
            if getattr(job, 'prompt_index', 0) == -1 or "thumbnail" in str(getattr(job, 'prompt_slug', '')).lower() or getattr(job, 'topic_slug', '') == 'thumbnail':
                # Generate thumbnail.jpg in project root
                img_dir = Path(job.project_folder)
                img_dir.mkdir(parents=True, exist_ok=True)
                filename = "thumbnail.jpg"
                save_path = img_dir / filename
            else:
                if target_mode.lower() == "video":
                    media_dir = Path(job.project_folder) / "videos"
                    media_dir.mkdir(parents=True, exist_ok=True)
                    filename = f"{job.prompt_index:02d}.mp4"
                else:
                    media_dir = Path(job.project_folder) / "images"
                    media_dir.mkdir(parents=True, exist_ok=True)
                    filename = f"{job.prompt_index:02d}.png"
                save_path = media_dir / filename
        else:
            max_slug = self._s("max_slug_chars", 60)
            filename = generate_filename(
                self._s("filename_template", "{topicSlug}/{topicSlug}_{promptIndex}_{promptSlug}.png"),
                job,
                max_slug = max_slug,
                mode     = job.mode or self._s("generation_mode", "image")
            )
            save_path = Path(self._s("output_dir", "output")) / filename

        # Dedup check
        min_bytes = self._s("min_image_bytes", 30_000)
        if self._s("dedup_check", True) and save_path.exists() and save_path.stat().st_size >= min_bytes:
            job.status       = JobStatus.DONE
            job.file_path    = str(save_path)
            job.completed_at = time.time()
            self.queue.update_job(job)
            self._log(f"â­ #{job.global_index} skipped â€” file exists: {save_path.name}", "info")
            self._emit("job_done", job.id, str(save_path))
            # NEW: Custom update to project.json if this job finishes the project folder
            if job.project_folder:
                import json
                folder_jobs = [j for j in self.queue.all_jobs() if j.project_folder == job.project_folder]
                all_finished = True
                for j in folder_jobs:
                    # Look at current state PLUS this job's updated state
                    current_status = JobStatus.DONE if j.id == job.id else j.status
                    if current_status not in (JobStatus.DONE, JobStatus.SKIPPED):
                        all_finished = False
                        break
                
                if all_finished:
                    pjson_path = Path(job.project_folder) / "project.json"
                    if pjson_path.exists():
                        try:
                            with open(pjson_path, "r", encoding="utf-8") as pf:
                                pdata = json.load(pf)
                            pdata["stage"] = "IMAGES_READY"
                            pdata["status"] = "COMPLETED"
                            with open(pjson_path, "w", encoding="utf-8") as pf:
                                json.dump(pdata, pf, indent=2)
                        except Exception as e:
                            self._log(f"Error updating project.json: {e}", "error")
            return

        job.status              = JobStatus.RUNNING
        job.started_at          = time.time()
        job.assigned_account_id = self.account.id
        self.queue.update_job(job)

        self._emit("job_start", job.id, job.prompt_text)
        self._log(f"â–¶ #{job.global_index} [{job.topic_name}] {char_name or 'generic'} â†’ {Path(filename).name}", "info")

        max_retries     = self._s("max_retries", 3)
        retry_delay     = self._s("retry_delay", 5.0)
        rate_limit_wait = self._s("rate_limit_wait", 300.0)
        retry           = 0

        target_model = job.model_name or self._s("default_model", "Nano Banana")
        target_ratio = job.aspect_ratio or self._s("aspect_ratio", "16:9")

        while retry <= max_retries:
            if self._stop_evt.is_set():
                self._requeue_job(job, "worker_stopped")
                return

            try:
                paths = await self._auto.run_prompt(
                    prompt_text  = final_prompt,
                    save_path    = save_path,
                    model_name   = target_model,
                    mode         = target_mode,
                    aspect_ratio = target_ratio,
                    image_count  = getattr(self.settings, 'image_count', 'x1'),
                    character    = character_obj,
                    do_new_session = do_new_chat,
                )

                primary_path = paths[0] if paths else str(save_path)
                job.status            = JobStatus.DONE
                job.file_path         = ", ".join(paths) if paths else str(save_path)
                job.completed_at      = time.time()
                self.queue.update_job(job)
                self._check_and_update_project_folder(getattr(job, 'project_folder', ''))

                num_saved = len(paths)
                self.account.images_session += num_saved
                self.account.images_total   += num_saved
                self._current_ws().images_generated += num_saved
                now = time.time()
                self._last_success_time      = now
                self.account.last_image_time = now
                self._recovery_count         = 0

                # JSON metadata sidecar for all saved files
                if self._s("save_metadata_json", False):
                    import json as _json, datetime as _dt
                    for p in paths:
                        sidecar = Path(p).with_suffix(".json")
                        try:
                            sidecar.write_text(_json.dumps({
                                "prompt": job.prompt_text,
                                "final_prompt": final_prompt,
                                "character": char_name,
                                "model": target_model,
                                "aspect_ratio": target_ratio,
                                "mode": job.mode,
                                "topic": job.topic_name,
                                "timestamp": _dt.datetime.now().isoformat(),
                                "account": self.account.name,
                            }, indent=2), encoding="utf-8")
                        except Exception:
                            pass

                self._emit("job_done", job.id, primary_path)
                # NEW: Custom update to project.json if this job finishes the project folder
                if job.project_folder:
                    import json
                    folder_jobs = [j for j in self.queue.all_jobs() if j.project_folder == job.project_folder]
                    all_finished = True
                    for j in folder_jobs:
                        current_status = JobStatus.DONE if j.id == job.id else j.status
                        if current_status not in (JobStatus.DONE, JobStatus.SKIPPED):
                            all_finished = False
                            break
                    
                    if all_finished:
                        pjson_path = Path(job.project_folder) / "project.json"
                        if pjson_path.exists():
                            try:
                                with open(pjson_path, "r", encoding="utf-8") as pf:
                                    pdata = json.load(pf)
                                pdata["stage"] = "IMAGES_READY"
                                pdata["status"] = "COMPLETED"
                                with open(pjson_path, "w", encoding="utf-8") as pf:
                                    json.dump(pdata, pf, indent=2)
                            except Exception as e:
                                self._log(f"Error updating project.json: {e}", "error")
                self._emit("img_count", self.account.images_session, self.account.images_total)
                self._log(f"✅ #{job.global_index} → {Path(primary_path).name} ({num_saved} images)", "success")
                return

            except QuotaLimitError:
                ws = self._current_ws().name
                self._log(f"Google Flow quota reached on '{ws}'", "warning")
                self._emit("image_limit", ws)
                self._emit("status", AccountStatus.IMAGE_LIMITED)
                self._mark_ws_limited()
                await asyncio.sleep(rate_limit_wait)
                retry += 1
                do_new_chat = True
                continue

            except PolicyError as e:
                self._log(f"Google Safety Policy: {e}", "warning")
                job.status       = JobStatus.SKIPPED
                job.error        = f"policy: {e}"
                job.completed_at = time.time()
                self.queue.update_job(job)
                self._check_and_update_project_folder(getattr(job, 'project_folder', ''))
                self._emit("job_skip", job.id, "policy_violation")
                return

            except LoginExpiredError:
                self._log("Google session expired", "warning")
                self._emit("login_expired")
                self._emit("status", AccountStatus.LOGIN_EXPIRED)
                self._requeue_job(job, "session_expired")
                self._stop_evt.set()
                return

            except SkippedError:
                job.status       = JobStatus.SKIPPED
                job.error        = "user_skipped"
                job.completed_at = time.time()
                self.queue.update_job(job)
                self._check_and_update_project_folder(getattr(job, 'project_folder', ''))
                self._emit("job_skip", job.id, "user_skipped")
                return

            except Exception as e:
                self._log(f"Generation issue: {e} (attempt {retry+1}/{max_retries+1})", "warning")
                retry += 1
                do_new_chat = True
                if retry <= max_retries:
                    await asyncio.sleep(retry_delay)
                    continue

        self._log(f"âŒ #{job.global_index} â€” {max_retries+1} attempts exhausted, marking failed", "error")
        job.status       = JobStatus.FAILED
        job.error        = f"failed_{max_retries+1}_attempts"
        job.completed_at = time.time()
        self.queue.update_job(job)
        self._emit("job_fail", job.id, f"Failed after {max_retries+1} attempts")
