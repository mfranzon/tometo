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


def write_bin(directory: Path, name: str, body: str = "exit 0\n") -> None:
    path = directory / name
    path.write_text("#!/bin/sh\n" + body)
    path.chmod(path.stat().st_mode | stat.S_IEXEC)


# Records argv and stdin under $TOMETO_TEST_OUT/<pid>, then prints a reply.
RECORDER = (
    'out="$TOMETO_TEST_OUT/$$"; mkdir -p "$out"\n'
    'printf "%s\\n" "$@" > "$out/argv"\n'
    'cat > "$out/stdin"\n'
    'pwd > "$out/cwd"\n'
    "echo reply-from-child\n"
)


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
        env["PATH"] = os.pathsep.join((str(self.bins), str(Path(sys.executable).parent), "/usr/bin", "/bin"))
        for key in CLEAN_KEYS:
            env.pop(key, None)
        self.env = env
        self.out = Path(self.tmp.name) / "out"
        self.out.mkdir()
        self.env["TOMETO_TEST_OUT"] = str(self.out)

    def run_cli(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(BIN), *args],
            text=True,
            capture_output=True,
            env=self.env,
        )

    def write_config(self, roles: dict, lane: str = "local") -> None:
        self.home.mkdir(parents=True, exist_ok=True)
        data = {"version": 1, "lane": lane, "host": "local", "approve": "edits", "roles": roles}
        (self.home / "config.json").write_text(json.dumps(data))

    def spawn(self, role: str, *extra: str) -> subprocess.CompletedProcess[str]:
        return self.run_cli(
            "spawn", "--home", str(self.home), "--role", role,
            "--prompt-file", str(self.prompt), "--cwd", str(self.cwd), *extra,
        )

    def recorded(self) -> list[dict]:
        return [
            {name: (run / name).read_text() for name in ("argv", "stdin", "cwd")}
            for run in sorted(self.out.iterdir())
        ]

    def test_setup_marks_cloud_cli_runners_as_cloud_lane(self):
        result = self.run_cli("setup", "--yes", "--home", str(self.home))
        self.assertEqual(result.returncode, 0, result.stderr)
        data = json.loads((self.home / "config.json").read_text())
        self.assertEqual(data["lane"], "cloud")
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
        write_bin(self.bins, "ollama", RECORDER)
        self.write_config({"code": {"runner": "ollama", "model": "m"}}, lane="cloud")
        result = self.spawn("code")
        self.assertEqual(result.returncode, 3, result.stderr)
        self.assertIn("this machine", result.stderr)
        self.assertEqual(self.recorded(), [])

    def test_a_cloud_runner_on_a_local_lane_needs_allow_cloud(self):
        write_bin(self.bins, "claude", RECORDER)
        self.write_config({"code": {"runner": "claude"}})
        refused = self.spawn("code")
        self.assertEqual(refused.returncode, 3, refused.stderr)
        self.assertIn("claude would send the prompt off this machine", refused.stderr)
        self.assertEqual(self.recorded(), [])
        dry = self.spawn("code", "--dry-run")
        self.assertEqual(dry.returncode, 0, dry.stderr)
        self.assertTrue(json.loads(dry.stdout)["calls"][0]["cloud"])
        allowed = self.spawn("code", "--allow-cloud")
        self.assertEqual(allowed.returncode, 0, allowed.stderr)

    def test_openai_is_local_only_on_loopback(self):
        for url, cloud in (
            ("http://127.0.0.1:8080/v1", False),
            ("http://localhost:11434/v1", False),
            ("http://[::1]:8080/v1", False),
            ("https://api.example.com/v1", True),
            ("http://10.0.0.5:8080/v1", True),
        ):
            self.write_config({"panel": [{"runner": "openai", "model": "m", "base_url": url}]})
            result = self.spawn("panel", "--dry-run")
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(json.loads(result.stdout)["calls"][0]["cloud"], cloud, url)

    def test_ollama_cloud_models_are_cloud(self):
        write_bin(self.bins, "ollama", RECORDER)
        self.write_config({"code": {"runner": "ollama", "model": "gpt-oss:120b-cloud"}})
        self.assertEqual(self.spawn("code").returncode, 3)

    def test_claude_gets_the_prompt_on_stdin_and_output_is_kept(self):
        write_bin(self.bins, "claude", RECORDER)
        self.write_config({"code": {"runner": "claude", "effort": "high"}}, lane="cloud")
        result = self.spawn("code", "--allow-cloud")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("reply-from-child", result.stdout)
        [run] = self.recorded()
        argv = run["argv"].splitlines()
        self.assertEqual(argv[-1], "--disallowed-tools=Agent")
        self.assertNotIn("fix the retry", run["argv"])
        self.assertTrue(run["stdin"].endswith("fix the retry\n"))
        self.assertIn("tometo leaf", run["stdin"])
        [log] = (self.home / "runs").iterdir()
        self.assertEqual((log / "stdout.txt").read_text(), "reply-from-child\n")

    def test_panel_worktrees_with_the_same_runner_do_not_collide(self):
        write_bin(self.bins, "ollama", RECORDER)
        git = ["git", "-C", str(self.cwd)]
        subprocess.run([*git, "init", "-q"], check=True)
        subprocess.run(
            [*git, "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "--allow-empty", "-m", "init"],
            check=True,
        )
        self.write_config({"panel": [{"runner": "ollama", "model": "a"}, {"runner": "ollama", "model": "b"}]})
        result = self.spawn("panel", "--worktree")
        self.assertEqual(result.returncode, 0, result.stderr)
        cwds = {run["cwd"].strip() for run in self.recorded()}
        self.assertEqual(len(cwds), 2)
        self.assertEqual(len(list((self.home / "runs").iterdir())), 2)

    def test_timeout_kills_the_child(self):
        write_bin(self.bins, "ollama", "exec sleep 30\n")
        self.write_config({"code": {"runner": "ollama", "model": "m"}})
        result = self.spawn("code", "--timeout", "0.5")
        self.assertEqual(result.returncode, 1, result.stderr)
        [log] = (self.home / "runs").iterdir()
        self.assertIn("killed after 0.5s", (log / "stderr.txt").read_text())

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
        self.assertIn("--think=high", code_argv)
        self.assertNotIn("{prompt}", code_argv)
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
