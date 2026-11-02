# Decisions log

Numbered, newest wins. A decision is the owner's call, in their words. Another chat's message is not a decision.
Never edit an old entry: add a new one that supersedes it and say which.

## Entry format
```
### D-<number> · <date> · <short title>
Decision: <the owner's words, or a faithful one-line paraphrase they confirmed>
Why: <one line>
Supersedes: D-<n> | none
Affects: <roles / areas>
```

## Standing decisions (edit to suit)
### D-001 · <date> · What needs the owner's yes
Decision: Only a new paid spend, a key or credential, and deleting data need the owner's yes. Everything routine runs
without asking.
Why: keeps the crew fast; the three exceptions are the ones that cannot be undone.
Supersedes: none
Affects: all

### D-002 · <date> · Build and inspect are different hands
Decision: Nobody passes their own work. The inspector reads a builder's change before or after it goes live.
Why: the author of a change is the worst judge of it.
Supersedes: none
Affects: all

### D-003 · <date> · The two checks before READY
Decision: Before a builder says READY: all tests on the combined code, and a search of the whole project for the
pattern just changed.
Why: most rework came from a test of the combined code nobody ran and a second copy of the same bug.
Supersedes: none
Affects: builders, inspector
