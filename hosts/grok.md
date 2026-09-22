# Grok

Native child: `spawn_subagent` with `subagent_type` `tometo-agent` when the role's runner is `grok` and the role does not pin `model` or `effort`. `spawn_subagent` has no model argument, so a pin is invisible there.

Pinned model, pinned effort, or a runner other than `grok`: `bin/tometo spawn`.

Code that writes files goes out with `isolation: worktree` natively, or `--worktree` on the CLI.

Several children start in one message. The parent reads their results.
