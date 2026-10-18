# Runtime

Skills, host files, and `bin/tometo` share this contract. Change it here first.

## Config

`tometo setup` writes `~/.tometo/config.json`.

```json
{
  "version": 1,
  "lane": "local",
  "host": "grok",
  "approve": "edits",
  "roles": {
    "code": {"runner": "grok", "effort": "high"},
    "judgment": {"runner": "claude", "effort": "high"},
    "panel": [
      {"runner": "grok", "effort": "xhigh"},
      {"runner": "claude", "effort": "high"}
    ],
    "swarm": {"runner": "grok", "effort": "high"}
  }
}
```

`lane` is `local` or `cloud`. Setup writes `cloud` when any role it assigns is a cloud runner, and `local` otherwise.

`tometo spawn` starts nothing that sends the prompt off this machine until the command includes `--allow-cloud`. That covers a cloud lane and any cloud call on a local lane:

- `grok`, `claude`, `opencode`, `codex`: always cloud. The binary is local, the model is not.
- `ollama`: cloud when the model tag ends in `cloud`, for example `gpt-oss:120b-cloud`.
- `openai`: cloud unless `base_url` is `localhost` or a loopback address.
- `llama-cli`, `mlx`: local. A Hugging Face repo is downloaded, the prompt is not sent.

The refusal exits 3. `--dry-run` never refuses, and each call it prints carries `"cloud": true` or `false`.

`host` is the session that is driving: `grok`, `claude-code`, `cursor`, `codex`, `opencode`, `pi`, or `local`. Spawn does not care. The session reads `hosts/<host>.md` to decide how to start a child.

`approve` is how a child is allowed to act:

| value | meaning |
| --- | --- |
| `edits` | file edits proceed, shell still follows that CLI's normal rules |
| `auto` | that CLI's automatic approval mode |
| `all` | the CLI's full bypass flag |

A missing `model` on `grok`, `claude`, `opencode`, or `codex` means that CLI's own default. Set `model` to pin one.

A local model is a runner too. `setup` puts each model from `ollama list` on the panel. `llama-cli`, `mlx`, and `openai` are used when a role names them.

| runner | `model` | what spawn runs |
| --- | --- | --- |
| `ollama` | a name from `ollama list` | `ollama run`. `code` and `swarm` get its tool loop. `judgment` and `panel` are one reply. |
| `llama-cli` | a GGUF path, or `user/repo` | one turn of `llama-cli` |
| `mlx` | a local directory or a Hugging Face repo | `mlx_lm.generate` |
| `openai` | the id that server expects | `POST {base_url}/chat/completions` |

`base_url` is the OpenAI-compatible root, for example `http://127.0.0.1:11434/v1` or `http://127.0.0.1:8080/v1`.

```json
{"runner": "ollama", "model": "qwen3.5:9b", "effort": "high"}
{"runner": "llama-cli", "model": "user/model"}
{"runner": "mlx", "model": "mlx-community/Llama-3.2-3B-Instruct-4bit"}
{"runner": "openai", "model": "local", "base_url": "http://127.0.0.1:8080/v1"}
```

`judgment` and any single role may use `{"runner": "inherit"}`. That work stays in the parent session. A panel is a list of role objects, one child each.

## Roles

| role | who |
| --- | --- |
| `code` | implementation, refactors, mechanical edits |
| `judgment` | design calls, prose, the hardest change |
| `panel` | one fresh context per entry, same question |
| `swarm` | one worker per slice of a coverage job |

## How a child starts

Read `hosts/<host>.md`.

Use the host's native subagent when the role's runner is this same host. Spawn that child as `tometo-agent`.

Use `bin/tometo spawn` when the runner is another CLI, when the role pins a model or an effort the native tool cannot set, or when the host is `local`. The command prepends `agents/tometo-agent.md` to the prompt.

```bash
bin/tometo spawn --role code --prompt-file /tmp/task.md --cwd "$PWD" --worktree
```

`--worktree` adds a git worktree under `~/.tometo/worktrees/` and runs the child there, on a branch `tometo/<role>-<runner>-<time>-<id>`. Pass it when the child writes code.

Each call gets `~/.tometo/runs/<role>-<runner>-<time>-<id>/` with `prompt.md`, `stdout.txt`, and `stderr.txt`. stdout streams to the terminal as it arrives. The path is printed on stderr when the child exits. `--timeout SECONDS` kills a child that runs longer.

`claude`, `opencode`, `codex`, `ollama`, and `mlx` read the prompt on stdin. `grok` and `llama-cli` read `prompt.md`.

A panel is one spawn of `--role panel`, which runs every panel entry and prints a section per runner. `--index N` runs a single entry.

## Leaves

The parent owns fan-out. A child does the task in its prompt and stops. That rule is the body of `agents/tometo-agent.md`.

## Proof

A green build is not proof of a user-facing change. The playbook names the surface. Run it there, and write down the command and what it printed.

Claims in the reply are measured, inferred, or a guess, in the same sentence.
