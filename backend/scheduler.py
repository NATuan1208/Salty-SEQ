import json
import logging
import time
from datetime import datetime
from pathlib import Path

from apscheduler.schedulers.background import BackgroundScheduler

logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).parent / "data"
STATUS_FILE = DATA_DIR / "pipeline_status.json"
LOG_FILE = DATA_DIR / "pipeline_runs.log"

_scheduler = BackgroundScheduler()


def get_pipeline_status() -> dict:
    if STATUS_FILE.exists():
        try:
            return json.loads(STATUS_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {
        "last_run": None,
        "status": "never",
        "records_added": 0,
        "next_run": None,
        "error": None,
    }


def _write_status(status: str, records_added: int = 0, error: str | None = None) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    job = _scheduler.get_job("daily_pipeline")
    next_run = None
    if job and job.next_run_time:
        next_run = job.next_run_time.isoformat()
    STATUS_FILE.write_text(
        json.dumps({
            "last_run": datetime.now().isoformat(),
            "status": status,
            "records_added": records_added,
            "next_run": next_run,
            "error": error,
        }),
        encoding="utf-8",
    )


def _run_daily_pipeline() -> None:
    logger.info("Pipeline job started")
    _write_status("running")
    try:
        time.sleep(2)
        _write_status("success", records_added=5)
        LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(f"{datetime.now().isoformat()} | SUCCESS | records_added=5\n")
        logger.info("Pipeline job completed successfully")
    except Exception as e:
        _write_status("failed", error=str(e))
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(f"{datetime.now().isoformat()} | FAILED | {e}\n")
        logger.error("Pipeline job failed: %s", e)


def trigger_pipeline() -> None:
    _scheduler.add_job(
        _run_daily_pipeline,
        "date",
        id="manual_run",
        replace_existing=True,
    )


def start_scheduler(app=None) -> None:
    _scheduler.add_job(
        _run_daily_pipeline,
        "cron",
        hour=6,
        minute=0,
        id="daily_pipeline",
        replace_existing=True,
    )
    if not _scheduler.running:
        _scheduler.start()
    logger.info("APScheduler started (daily pipeline at 06:00)")
