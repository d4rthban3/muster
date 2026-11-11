# Before each resubmit to Anthropic's plugin directory

Anthropic's rules can change. Before the owner resubmits, the builder starts one helper (a subagent; it only reads and reports) to
reread the three pages below and compare them with the check in `scripts/build-directory.py` (`--verify` and `--selftest`).

1. https://claude.com/docs/directory/publish
2. https://claude.com/docs/plugins/submit
3. https://claude.com/docs/directory/submission-status

The helper returns only: each refusal or warning the pages now list that the check does not test, and anything the pages say that
changed since the last READY. The builder adds a test for each new rule to `problems()` in `scripts/build-directory.py` and a
planted case to `selftest()`, runs `--verify` and `--selftest`, and puts what changed in the shared notes folder for the manager to
post on the board. Nothing is submitted by a worker: the owner resubmits himself.
