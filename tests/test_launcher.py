"""Combined launcher lifecycle tests without loading app secrets or data."""
import ast
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

import run as launcher

ROOT = Path(__file__).resolve().parents[1]


class LauncherTests(unittest.TestCase):
    def test_lock_blocks_duplicate_and_releases_on_close(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "combined.lock"
            first = launcher.ProjectLock(path)
            second = launcher.ProjectLock(path)
            try:
                self.assertTrue(first.acquire())
                self.assertFalse(second.acquire())
                first.release()
                self.assertTrue(second.acquire())
            finally:
                first.release()
                second.release()

    def test_workers_use_same_interpreter_and_do_not_launch_recursively(self):
        process = Mock()
        with patch.object(launcher.subprocess, "Popen", return_value=process) as popen, \
             patch.object(launcher.threading, "Thread") as thread, \
             patch.dict(launcher.os.environ, {}, clear=True):
            environment = launcher.worker_environment(5001)
            self.assertEqual(environment["SITE_BASE"], "http://127.0.0.1:5001")
            self.assertEqual(environment["BMI_RUN_WORKER"], "1")
            self.assertIs(launcher.start_worker("telegram_bot.py", environment), process)
            args, kwargs = popen.call_args
            self.assertEqual(args[0][0], launcher.sys.executable)
            self.assertEqual(Path(args[0][-1]).name, "telegram_bot.py")
            self.assertEqual(kwargs["cwd"], launcher.BASE_DIR)
            thread.return_value.start.assert_called_once()

    def test_explicit_site_url_is_preserved(self):
        with patch.dict(launcher.os.environ, {"SITE_BASE": "https://monitor.example"}, clear=True):
            self.assertEqual(launcher.worker_environment(5000)["SITE_BASE"], "https://monitor.example")

    def test_worker_shutdown_terminates_both_and_kills_stuck_child(self):
        web, bot = Mock(), Mock()
        web.poll.return_value = bot.poll.return_value = None
        bot.wait.side_effect = [launcher.subprocess.TimeoutExpired("bot", 5), 0]
        launcher.stop_workers([web, bot])
        web.terminate.assert_called_once()
        bot.terminate.assert_called_once()
        bot.kill.assert_called_once()
        self.assertEqual(bot.wait.call_count, 2)

    def test_web_failure_is_detected_before_bot_starts(self):
        web = Mock()
        web.poll.return_value = 1
        with self.assertRaisesRegex(RuntimeError, "Sayt ishga tushmadi"):
            launcher.wait_for_web(web, 5000)

    def test_output_redacts_token(self):
        process = Mock()
        token = "123456:" + "a" * 35
        process.stdout = iter([f"https://api.telegram.org/bot{token}/getUpdates\n"])
        with patch.object(launcher.logger, "info") as log:
            launcher.stream_output(process, "bot")
            self.assertNotIn(token, log.call_args.args[-1])
            self.assertIn("[TOKEN REDACTED]", log.call_args.args[-1])

    def test_each_entrypoint_selects_supervisor_or_worker(self):
        for filename, worker in (("app.py", "run_web_server"), ("telegram_bot.py", "main")):
            source = ROOT.joinpath(filename).read_text(encoding="utf-8")
            tree = ast.parse(source)
            entrypoints = [node for node in tree.body if isinstance(node, ast.If) and "__main__" in ast.unparse(node.test)]
            calls = []

            def supervise():
                calls.append("supervisor")
                return 0

            fake_run = Mock(main=supervise)
            for child, expected in ((False, "supervisor"), (True, "worker")):
                calls.clear()
                namespace = {"__name__": "__main__", "os": launcher.os,
                             worker: lambda: calls.append("worker")}
                environment = {"BMI_RUN_WORKER": "1"} if child else {}
                with patch.dict(launcher.os.environ, environment, clear=True), \
                     patch.dict("sys.modules", {"run": fake_run}):
                    try:
                        exec(compile(ast.Module(body=entrypoints, type_ignores=[]), filename, "exec"), namespace)
                    except SystemExit as exit:
                        self.assertEqual(exit.code, 0)
                self.assertEqual(calls, [expected])

    def test_supervisor_starts_both_and_cleans_up_on_ctrl_c(self):
        lock = Mock()
        lock.acquire.return_value = True
        web, bot = Mock(), Mock()
        web.poll.return_value = bot.poll.return_value = None
        config = Mock()
        config.Config.PORT = 5000
        dotenv = Mock()
        with patch.object(launcher, "ProjectLock", return_value=lock), \
             patch.object(launcher, "start_worker", side_effect=[web, bot]) as start, \
             patch.object(launcher, "wait_for_web") as ready, \
             patch.object(launcher, "stop_workers") as stop, \
             patch.object(launcher.time, "sleep", side_effect=KeyboardInterrupt), \
             patch.dict("sys.modules", {"dotenv": dotenv, "config": config}), \
             patch.dict(launcher.os.environ, {}, clear=True):
            self.assertEqual(launcher.main(), 0)
            self.assertEqual([call.args[0] for call in start.call_args_list], ["app.py", "telegram_bot.py"])
            self.assertEqual(start.call_args_list[0].args[1], start.call_args_list[1].args[1])
            ready.assert_called_once_with(web, 5000)
            stop.assert_called_once_with([web, bot])
            lock.release.assert_called_once()

    def test_duplicate_launcher_does_not_start_workers(self):
        lock = Mock()
        lock.acquire.return_value = False
        with patch.object(launcher, "ProjectLock", return_value=lock), \
             patch.object(launcher, "start_worker") as start:
            self.assertEqual(launcher.main(), 0)
            start.assert_not_called()

    def test_failed_web_startup_cleans_up_and_does_not_start_bot(self):
        lock, web = Mock(), Mock()
        lock.acquire.return_value = True
        config = Mock()
        config.Config.PORT = 5000
        with patch.object(launcher, "ProjectLock", return_value=lock), \
             patch.object(launcher, "start_worker", return_value=web) as start, \
             patch.object(launcher, "wait_for_web", side_effect=RuntimeError("failed")), \
             patch.object(launcher, "stop_workers") as stop, \
             patch.dict("sys.modules", {"dotenv": Mock(), "config": config}), \
             patch.dict(launcher.os.environ, {}, clear=True):
            self.assertEqual(launcher.main(), 1)
            start.assert_called_once()
            stop.assert_called_once_with([web])
            lock.release.assert_called_once()



if __name__ == "__main__":
    unittest.main()
