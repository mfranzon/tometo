#!/usr/bin/env python3
"""Hermetic checks for bin/tometo. No model calls."""

import json
import os
import stat
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BIN = ROOT / "bin" / "tometo"

CLEAN_KEYS = (
    "GROK_SESSION_ID",
    "GROK_AGENT",
    "CLAUDECODE",
    "CLAUDE_CODE_ENTRYPOINT",
    "CURSOR_AGENT",
    "CURSOR_TRACE_ID",
    "CODEX_SANDBOX",
    "CODEX_THREAD_ID",
    "OPENCODE",
    "OPENCODE_CLIENT",
    "PI_CODING_AGENT_DIR",
)


def write_bin(directory: Path, name: str) -> None:
    path = directory / name
    path.write_text("#!/bin/sh\nexit 0\n")
    path.chmod(path.stat().st_mode | stat.S_IEXEC)


class TometoCliTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.home = Path(self.tmp.name) / "home"
        self.bins = Path(self.tmp.name) / "bins"
        self.bins.mkdir()
        self.cwd = Path(self.tmp.name) / "repo"
        self.cwd.mkdir()
        self.prompt = Path(self.tmp.name) / "task.md"
        self.prompt.write_text("fix the retry\n")
        write_bin(self.bins, "grok")
        write_bin(self.bins, "claude")
        env = os.environ.copy()
        env["PATH"] = os.pathsep.join((str(self.bins), str(Path(sys.executable).parent)))
        for key in CLEAN_KEYS:
            env.pop(key, None)
        self.env = env

    def run_cli(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(BIN), *args],
            text=True,
            capture_output=True,
            env=self.env,
        )

    def test_setup_writes_local_lane_and_detected_runners(self):
        result = self.run_cli("setup", "--yes", "--home", str(self.home))
        self.assertEqual(result.returncode, 0, result.stderr)
        data = json.loads((self.home / "config.json").read_text())
        self.assertEqual(data["lane"], "local")
        self.assertEqual(data["host"], "local")
        self.assertEqual(data["approve"], "edits")
        self.assertEqual(data["roles"]["code"], {"runner": "grok", "effort": "high"})
        self.assertEqual(data["roles"]["judgment"]["runner"], "claude")
        self.assertEqual([item["runner"] for item in data["roles"]["panel"]], ["grok", "claude"])

    def test_spawn_dry_run_uses_local_grok_argv(self):
        self.run_cli("setup", "--yes", "--home", str(self.home))
        result = self.run_cli(
            "spawn",
            "--dry-run",
            "--home",
            str(self.home),
            "--role",
            "code",
            "--prompt-file",
            str(self.prompt),
            "--cwd",
            str(self.cwd),
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(
            payload["calls"][0]["argv"],
            [
                "grok",
                "--prompt-file",
                "{prompt}",
                "--cwd",
                str(self.cwd.resolve()),
                "--output-format",
                "plain",
                "--no-subagents",
                "--permission-mode",
                "acceptEdits",
                "--effort",
                "high",
            ],
        )

    def test_worktree_dry_run_does_not_need_a_git_repo(self):
        self.run_cli("setup", "--yes", "--home", str(self.home))
        result = self.run_cli(
            "spawn",
            "--dry-run",
            "--worktree",
            "--home",
            str(self.home),
            "--role",
            "code",
            "--prompt-file",
            str(self.prompt),
            "--cwd",
            str(self.cwd),
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        call = json.loads(result.stdout)["calls"][0]
        self.assertIn(str(self.home / "worktrees"), call["worktree"])
        self.assertFalse((self.home / "worktrees").exists())

    def test_cloud_lane_is_refused(self):
        self.run_cli("setup", "--yes", "--home", str(self.home))
        path = self.home / "config.json"
        data = json.loads(path.read_text())
        data["lane"] = "cloud"
        path.write_text(json.dumps(data))
        result = self.run_cli(
            "spawn",
            "--dry-run",
            "--home",
            str(self.home),
            "--role",
            "code",
            "--prompt-file",
            str(self.prompt),
            "--cwd",
            str(self.cwd),
        )
        self.assertEqual(result.returncode, 3, result.stderr)
        self.assertIn("this machine", result.stderr)

    def test_inherit_stays_in_the_parent(self):
        self.run_cli("setup", "--yes", "--home", str(self.home))
        path = self.home / "config.json"
        data = json.loads(path.read_text())
        data["roles"]["judgment"] = {"runner": "inherit"}
        path.write_text(json.dumps(data))
        result = self.run_cli(
            "spawn",
            "--dry-run",
            "--home",
            str(self.home),
            "--role",
            "judgment",
            "--prompt-file",
            str(self.prompt),
        )
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertEqual(json.loads(result.stdout)["calls"], [{"runner": "inherit"}])

    def test_doctor_fails_when_the_runner_is_missing(self):
        self.run_cli("setup", "--yes", "--home", str(self.home))
        empty = Path(self.tmp.name) / "empty"
        empty.mkdir()
        self.env["PATH"] = os.pathsep.join((str(empty), str(Path(sys.executable).parent)))
        result = self.run_cli("doctor", "--home", str(self.home))
        self.assertEqual(result.returncode, 1, result.stdout)
        self.assertIn("bin=missing", result.stdout)

    def test_link_dry_run_writes_nothing_and_real_link_points_at_the_checkout(self):
        dest = Path(self.tmp.name) / "dest"
        (dest / ".grok").mkdir(parents=True)
        dry = self.run_cli("link", "--dry-run", "--dest-root", str(dest))
        self.assertEqual(dry.returncode, 0, dry.stderr)
        self.assertIn(str(dest / ".grok" / "skills" / "tometo"), dry.stdout)
        self.assertIn(str(dest / ".agents" / "skills" / "setup-tometo"), dry.stdout)
        self.assertFalse((dest / ".grok" / "skills").exists())
        linked = self.run_cli("link", "--dest-root", str(dest))
        self.assertEqual(linked.returncode, 0, linked.stderr)
        skill = dest / ".grok" / "skills" / "tometo"
        self.assertTrue(skill.is_symlink())
        self.assertEqual(skill.resolve(), (ROOT / "skills" / "tometo").resolve())

    def test_setup_adds_each_ollama_model_once(self):
        write_bin(self.bins, "ollama")
        (self.bins / "ollama").write_text(
            "#!/bin/sh\n"
            "if [ \"$1\" = list ]; then\n"
            "  printf '%s\\n' 'NAME ID SIZE MODIFIED' 'qwen3.5:9b abc 1 today' 'qwen3.5:latest abc 1 today'\n"
            "fi\n"
            "exit 0\n"
        )
        result = self.run_cli("setup", "--yes", "--home", str(self.home))
        self.assertEqual(result.returncode, 0, result.stderr)
        panel = json.loads((self.home / "config.json").read_text())["roles"]["panel"]
        ollama = [item for item in panel if item["runner"] == "ollama"]
        self.assertEqual(ollama, [{"runner": "ollama", "model": "qwen3.5:9b", "effort": "high"}])

    def test_ollama_code_uses_the_tool_loop_and_panel_is_one_reply(self):
        write_bin(self.bins, "ollama")
        self.run_cli("setup", "--yes", "--home", str(self.home))
        path = self.home / "config.json"
        data = json.loads(path.read_text())
        data["roles"]["code"] = {"runner": "ollama", "model": "qwen3.5:9b", "effort": "high"}
        data["roles"]["panel"] = [{"runner": "ollama", "model": "qwen3.5:9b", "effort": "high"}]
        path.write_text(json.dumps(data))
        code = self.run_cli(
            "spawn",
            "--dry-run",
            "--home",
            str(self.home),
            "--role",
            "code",
            "--prompt-file",
            str(self.prompt),
            "--cwd",
            str(self.cwd),
        )
        self.assertEqual(code.returncode, 0, code.stderr)
        code_argv = json.loads(code.stdout)["calls"][0]["argv"]
        self.assertEqual(
            code_argv[:6],
            ["ollama", "run", "qwen3.5:9b", "--nowordwrap", "--experimental", "--experimental-yolo"],
        )
        self.assertIn("--think", code_argv)
        panel = self.run_cli(
            "spawn",
            "--dry-run",
            "--home",
            str(self.home),
            "--role",
            "panel",
            "--prompt-file",
            str(self.prompt),
            "--cwd",
            str(self.cwd),
        )
        self.assertEqual(panel.returncode, 0, panel.stderr)
        panel_argv = json.loads(panel.stdout)["calls"][0]["argv"]
        self.assertNotIn("--experimental", panel_argv)
        self.assertEqual(panel_argv[0:3], ["ollama", "run", "qwen3.5:9b"])

    def test_llama_cli_and_openai_are_accepted_when_named(self):
        write_bin(self.bins, "llama-cli")
        self.run_cli("setup", "--yes", "--home", str(self.home))
        path = self.home / "config.json"
        data = json.loads(path.read_text())
        data["roles"]["judgment"] = {"runner": "llama-cli", "model": "org/repo", "effort": "high"}
        data["roles"]["panel"] = [
            {"runner": "openai", "model": "local", "base_url": "http://127.0.0.1:8080/v1"}
        ]
        path.write_text(json.dumps(data))
        llama = self.run_cli(
            "spawn",
            "--dry-run",
            "--home",
            str(self.home),
            "--role",
            "judgment",
            "--prompt-file",
            str(self.prompt),
        )
        self.assertEqual(llama.returncode, 0, llama.stderr)
        self.assertEqual(
            json.loads(llama.stdout)["calls"][0]["argv"][:4],
            ["llama-cli", "--single-turn", "--simple-io", "--no-display-prompt"],
        )
        self.assertIn("--hf-repo", json.loads(llama.stdout)["calls"][0]["argv"])
        remote = self.run_cli(
            "spawn",
            "--dry-run",
            "--home",
            str(self.home),
            "--role",
            "panel",
            "--prompt-file",
            str(self.prompt),
        )
        self.assertEqual(remote.returncode, 0, remote.stderr)
        self.assertEqual(
            json.loads(remote.stdout)["calls"][0]["argv"][:3],
            ["POST", "http://127.0.0.1:8080/v1/chat/completions", "local"],
        )

    def test_a_local_runner_without_a_model_is_rejected(self):
        write_bin(self.bins, "ollama")
        self.run_cli("setup", "--yes", "--home", str(self.home))
        path = self.home / "config.json"
        data = json.loads(path.read_text())
        data["roles"]["code"] = {"runner": "ollama"}
        path.write_text(json.dumps(data))
        result = self.run_cli(
            "spawn",
            "--dry-run",
            "--home",
            str(self.home),
            "--role",
            "code",
            "--prompt-file",
            str(self.prompt),
        )
        self.assertEqual(result.returncode, 2, result.stdout)
        self.assertIn("needs a model", result.stderr)


if __name__ == "__main__":
    unittest.main()
