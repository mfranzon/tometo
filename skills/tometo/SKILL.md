---
name: tometo
description: Rigorous engineering loop on whatever agent is already running, local by default. Use when the user says tometo, /tometo, or asks for poteto-style work on a local CLI, Claude Code, Codex, Pi, OpenCode, Cursor, or Grok.
disable-model-invocation: true
user-invocable: true
---

# Tometo

The contract is `docs/runtime.md` in this checkout. The checkout is the directory that contains this skill's `skills/` parent. The runner is `bin/tometo` there.

## Start

1. If `~/.tometo/config.json` is missing, run the setup-tometo skill, then come back.
2. Read the config. Read `hosts/<host>.md` for that config's `host`.
3. Match one playbook below. Open a todo list whose first items are that file's steps, copied verbatim. A step you skip stays on the list with `skip:` and the reason.
4. Do the steps. Start children the way the host file says. Review their diffs yourself.

## Playbooks

| task | file |
| --- | --- |
| how something works, why it is shaped this way, are we sure | `playbooks/investigation.md` |
| a defect to reproduce and fix | `playbooks/bug-fix.md` |
| new or changed behavior | `playbooks/feature.md` |
| open a PR for work that is already proven | `playbooks/opening-a-pr.md` |

Anything else still follows the contract: name the data, do the smallest change, prove it on the real surface, label claims. Say that no bundled playbook fit.

## Reply

Short sentences. Name who the change is for and what they can do after it. Then what the next engineer inherits.

Every claim is measured, inferred, or a guess, in the same sentence. A prediction is a guess. A command you ran is measured, and the sentence includes the command's result.
