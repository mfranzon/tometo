---
name: setup-tometo
description: Detect local coding CLIs and write ~/.tometo/config.json for tometo. Use when the user says setup tometo, /setup-tometo, or a tometo run has no config.
disable-model-invocation: true
user-invocable: true
---

# Setup tometo

The contract is `docs/runtime.md` in this checkout. The runner is `bin/tometo`.

1. Run `bin/tometo setup --yes` from the checkout.
2. Run `bin/tometo doctor`.
3. Show the config path, the host, the lane, and each role's runner. A cloud CLI with no `model` uses that CLI's default. An `ollama`, `llama-cli`, `mlx`, or `openai` role names its model, as `docs/runtime.md` describes. Offer to pin a model only when the user has already named one.
4. Run `bin/tometo link`. It adds missing symlinks and leaves any skill folder that is already there.
