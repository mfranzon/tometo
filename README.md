# tometo

tometo runs the poteto loop locally. Code, judgment, panel, and swarm can all be local models: Ollama, llama.cpp, MLX, or an OpenAI-compatible server at 127.0.0.1.

Name the data. Reproduce before you fix. Prove the change on the surface a person uses. Put a stronger model on the judgment, and a fast one on the edit. The parent fans out. Children stop when their task is done.

`tometo spawn` stays on this machine until you pass `--allow-cloud`.

pstack carries that method on Cursor and Grok Bot. See [NOTICE.md](NOTICE.md).

## A full local stack

`~/.tometo/config.json` can name a model on every role. This example uses Qwen3.8, the current open 27B weights. [`qwen3.8:27b`](https://ollama.com/library/qwen3.8) is the default 18GB Ollama tag. [`qwen3.8:27b-q8_0`](https://ollama.com/library/qwen3.8:27b-q8_0) is the 30GB quant. [`unsloth/Qwen3.8-27B-GGUF`](https://huggingface.co/unsloth/Qwen3.8-27B-GGUF) is the llama.cpp repo.

`setup` writes Ollama into code, judgment, and swarm when no `grok`, `claude`, `opencode`, or `codex` binary is on `PATH`. When one of those CLIs is installed, `setup` leaves code and judgment on it and adds each model from `ollama list` to the panel. Paste the file below to pin every role to a local model.

```json
{
  "version": 1,
  "lane": "local",
  "host": "local",
  "approve": "edits",
  "roles": {
    "code": {"runner": "ollama", "model": "qwen3.8:27b", "effort": "high"},
    "judgment": {"runner": "ollama", "model": "qwen3.8:27b-q8_0", "effort": "high"},
    "panel": [
      {"runner": "ollama", "model": "qwen3.8:27b", "effort": "high"},
      {"runner": "llama-cli", "model": "unsloth/Qwen3.8-27B-GGUF", "effort": "high"}
    ],
    "swarm": {"runner": "ollama", "model": "qwen3.8:27b", "effort": "high"}
  }
}
```

`ollama` on code and swarm gets the tool loop. Judgment, panel, llama.cpp, MLX, and `openai` are one reply. `bin/tometo doctor` checks that each runner's binary is on `PATH`. `bin/tometo spawn --dry-run` prints the argv and starts nothing.

An `mlx` seat uses the same shape, `{"runner": "mlx", "model": "<repo>"}`, with a repo `mlx_lm.generate` can load. The Apple Silicon upload `mlx-community/Qwen3.8-27B-4bit` is an mlx-vlm build.

## Install

From this checkout:

```bash
bin/tometo link
bin/tometo setup --yes
bin/tometo doctor
```

`link` symlinks the skills into the skill folders of the hosts installed on this machine (`~/.grok`, `~/.claude`, `~/.cursor`, `~/.codex`) and into `~/.agents/skills`.

Grok can also load the checkout as a plugin:

```bash
grok plugin install /absolute/path/to/tometo --trust
```

Then start a session and run `/setup-tometo`, then `/tometo`.

## Use

`/tometo` reads `~/.tometo/config.json`, then `hosts/<host>.md`, then one playbook:

| playbook | for |
| --- | --- |
| investigation | how something works, or whether a claim is true |
| bug-fix | reproduce, cause, smallest fix, run it again |
| feature | a new behavior, driven the way a user drives it |
| opening-a-pr | a proven diff, small commits, a PR body with what you ran |

The contract those files share is [docs/runtime.md](docs/runtime.md).

A role whose runner is another product starts with:

```bash
bin/tometo spawn --role code --prompt-file /tmp/task.md --cwd "$PWD" --worktree
```

`--dry-run` prints the argv and does not start a model. `setup` leaves `model` unset, so each CLI uses the default you already signed in with. Pin one by editing the JSON.

## Runners

`setup` records a CLI it can see on `PATH`: `grok`, `claude`, `opencode`, `codex`. It also puts each Ollama model on the panel. A `llama-cli`, `mlx`, or `openai` role is used once you name its model in the config. A full local assignment is in [A full local stack](#a-full-local-stack). The fields are in [docs/runtime.md](docs/runtime.md). `spawn --dry-run` prints the argv. Pi has a host file. This runner does not call Pi's subagent tool yet.

## Tests

```bash
python3 tests/test_cli.py
```
