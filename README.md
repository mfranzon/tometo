# tometo

tometo is a companion to [Lauren Tan](https://github.com/poteto)'s poteto method. pstack carries that method on Cursor and Grok Bot. tometo carries it on the agent you already run, including a CLI on this machine.

The loop is the same shape. Name the data. Reproduce before you fix. Prove the change on the surface a person uses. Put a stronger model on the judgment, and a fast one on the edit. Fan out from the parent. Children stop when their task is done.

Workers run on this machine. A cloud or bot lane is a switch you turn on, and `tometo spawn` refuses it until you do.

This is not pstack, and it is not her text. See [NOTICE.md](NOTICE.md).

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

`setup` records a CLI it can see on `PATH`: `grok`, `claude`, `opencode`, `codex`. It also puts each Ollama model on the panel. A `llama-cli`, `mlx`, or `openai` role is used once you name its model in the config. The fields are in [docs/runtime.md](docs/runtime.md). `spawn --dry-run` prints the argv. Pi has a host file. This runner does not call Pi's subagent tool yet.

## Tests

```bash
python3 tests/test_cli.py
```
