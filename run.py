"""Sayt va Telegram botni bir buyruq bilan boshqarish."""
import logging
import os
from pathlib import Path
import re
import subprocess
import sys
import threading
import time

import requests

BASE_DIR = Path(__file__).resolve().parent
logger = logging.getLogger("bmi-run")


class ProjectLock:
    """OS lock: ikkinchi launcher yangi bot sessiyasini ochmaydi."""

    def __init__(self, path):
        self.path = Path(path)
        self.file = None

    def acquire(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        stream = self.path.open("a+b")
        if stream.seek(0, os.SEEK_END) == 0:
            stream.write(b"0")
            stream.flush()
        stream.seek(0)
        try:
            if os.name == "nt":
                import msvcrt
                msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            stream.close()
            return False
        self.file = stream
        return True

    def release(self):
        if self.file is not None:
            self.file.close()
            self.file = None


def stream_output(process, name):
    for line in process.stdout:
        # Telegram URL va exception matnlaridagi tokenlarni logdan yashirish.
        safe = re.sub(r"(?:bot)?[0-9]{6,}:[A-Za-z0-9_-]{20,}", "[TOKEN REDACTED]", line.rstrip())
        if safe:
            logger.info("[%s] %s", name, safe)


def start_worker(filename, environment):
    process = subprocess.Popen(
        [sys.executable, "-u", "-X", "utf8", "-B", str(BASE_DIR / filename)],
        cwd=BASE_DIR, env=environment, stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="replace",
    )
    threading.Thread(target=stream_output, args=(process, filename), daemon=True).start()
    logger.info("%s ishga tushirildi (PID=%s)", filename, process.pid)
    return process


def stop_workers(processes):
    for process in reversed(processes):
        if process.poll() is None:
            process.terminate()
    for process in processes:
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)


def wait_for_web(process, port, timeout=60):
    deadline = time.monotonic() + timeout
    with requests.Session() as session:
        session.trust_env = False  # localhost tekshiruvi tashqi proxy orqali ketmasin
        while time.monotonic() < deadline:
            if process.poll() is not None:
                raise RuntimeError("Sayt ishga tushmadi.")
            try:
                response = session.get(f"http://127.0.0.1:{port}/healthz", timeout=2)
                if response.status_code == 200 and response.json().get("status") == "ok":
                    return
            except (requests.RequestException, ValueError):
                pass
            time.sleep(.5)
    raise RuntimeError("Sayt 60 soniyada tayyor bo'lmadi.")


def worker_environment(port):
    environment = os.environ.copy()
    environment.update({"BMI_RUN_WORKER": "1", "PYTHONIOENCODING": "utf-8"})
    environment.setdefault("SITE_BASE", f"http://127.0.0.1:{port}")
    return environment


def main():
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    lock = ProjectLock(BASE_DIR / "logs" / "combined-run.lock")
    if not lock.acquire():
        logger.info("Sayt va bot allaqachon ishga tushirilgan.")
        return 0
    processes = []
    try:
        # Ilovalardagi odatiy sozlamalarni yuklash; qiymatlar logga chiqarilmaydi.
        from dotenv import load_dotenv
        load_dotenv(BASE_DIR / ".env")
        from config import Config
        port = int(os.environ.get("PORT", Config.PORT))
        environment = worker_environment(port)
        web = start_worker("app.py", environment)
        processes.append(web)
        wait_for_web(web, port)
        bot = start_worker("telegram_bot.py", environment)
        processes.append(bot)
        logger.info("Sayt: http://localhost:%s · Bot ulangan · To'xtatish: Ctrl+C", port)
        while True:
            for process in processes:
                code = process.poll()
                if code is not None:
                    logger.error("Jarayon to'xtadi (kod=%s); sayt va bot yopiladi.", code)
                    return code or 1
            time.sleep(.5)
    except KeyboardInterrupt:
        logger.info("Sayt va bot to'xtatilmoqda.")
        return 0
    except (OSError, RuntimeError, ValueError) as error:
        logger.error("Ishga tushirish xatosi: %s", type(error).__name__)
        return 1
    finally:
        stop_workers(processes)
        lock.release()


if __name__ == "__main__":
    raise SystemExit(main())
