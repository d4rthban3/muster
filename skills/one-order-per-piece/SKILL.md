---
name: one-order-per-piece
description: How the manager writes orders: one per finished piece, a job name each report repeats.
---

# one-order-per-piece

## Rules
1. **One order per finished piece**, never one per step or per worker. The inspector's part comes with the READY.
2. **The job name** is short and plain. Every report about the job repeats it word for word.
3. **Only what the owner chose.** The order carries the owner's words for what it should look like, what counts as
   done, and what is in or out. If the owner has not said, that is a question to the owner first, not a guess in the
   order.
4. **Say where the work lives** (which worker's folder copy, which line of work) and what is out of the job, so the
   worker lists unrelated problems instead of fixing them.
5. **Two builders at once only when their files do not overlap.** Say which files each owns.
6. **No keys or passwords in an order.**
7. **Every order record carries `action`:** `start` (do the work, send READY), `hold` (after PASS wait for his go) or `ship` (after PASS ship it). Take it from his words; if he has not said, ask him.

8. **Every order carries an `Accept:` line** (one line per thing) **and a `Serves:` line** naming the part of the vision page the work is for. What counts as done is the owner's call (rule 3), so each Accept line quotes their words; a plain coding check (tests green, the free test run) you may add yourself. The inspector reads PASS or FAIL against the Accept lines one by one and says which line failed; then it looks at the real result against the `Serves:` line and reports any gap as a finding, even on a PASS. An order with no filled `Accept:` line is refused by the end-of-turn check.
9. **A `Contract:` line when one worker hands another a field or piece:** what is handed over and its shape (name, kind, where it lives), so two orders cannot cross. Both orders carry the same line. It is only for a hand-off; when nothing is handed over, leave the line out (a Contract line that is there must be filled).
10. **Open risks live in one page, `muster/RISKS.md`** (owner of the risk, what would go wrong, what closes it), not as loose lines on the board. An order that closes a risk names it in its Accept line.

## Order shape
Made-up example:
```
To:      Builder A_MyProject
Job:     filter button move
Owner's words: "filter button right of the pills" (owner's list, item 7)
Owns:    the home page files in your folder copy, line of work "builder/filter-move"
Out:     the pills themselves, any other page
Accept:  "filter button right of the pills" (his words); the page test passes; one light and one dark picture
Contract: (only for a hand-off) the new button posts {filter: "name"}; the list page reads that field
Done:    the owner's words above; the two checks; READY to Inspector_MyProject
```
A worker starting fresh gets the five-line note instead (`muster/START-NOTE.md`), with this job under Open.
