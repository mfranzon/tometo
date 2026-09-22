# Bug fix

1. Reproduce the failure on the surface the user hits. Record the command and the output.
2. Name the root cause as the code path that produced that output.
3. Add the smallest check that fails for that cause, then the smallest fix.
4. Re-run the reproduction and the check. Both must show the new behavior.
5. When the user asked to ship, continue with `opening-a-pr.md`.
