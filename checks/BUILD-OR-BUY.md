# Build or buy: the local date and time in the ready-built program (the chrono crate)

Made for rust-first-4-worker-queue, 2026-11-18, under the build-or-buy skill (skills/build-or-buy). Recommends; the manager decides.
Re-check by 2027-05-18, or sooner if a build fails on a new chrono release or a security advisory names it.

## The need
The ready-built program (checks/) must print the same local clock text as the Python copies: the date and time on the board entry written before
a compaction (precompact), and the "resets Mon 24 Nov" and "read at 14:05" parts of the Usage line. Python's `time.localtime` gives this for free;
Rust's standard library only knows UTC. Good enough for now: free, working on all five systems, traceable to its source.

## What was checked (each labelled)
| Candidate | Check | Notes |
|---|---|---|
| **chrono 0.4.45** with only the `clock` feature (MIT OR Apache-2.0, MSRV 1.61) | official docs read (docs.rs, 2026-11-18); lock file and `cargo tree` read here | Reads the local zone from `TZ` or the system, formats with strftime codes. Since 0.4.20 it no longer calls `localtime_r` (the advisory RUSTSEC-2020-0159 was about that call; the docs say it is gone). Default features are off, so no `time` 0.1 and no serde. |
| `time` 0.3 with `local-offset` | not checked here (from prior knowledge: a lead, not a fact) | Its local offset refuses to answer when other threads may run (soundness guard), so the program would often print UTC or fail. Unfit for this need. |
| Own code over `libc` (`localtime_r`) plus Windows calls | search summary only, a lead not a fact | Three systems' time-zone code to write and keep, and `libc` is itself a dependency. More risk than the dependency it avoids. |
| Run `date` | reasoned, not tried | No `date` on Windows; a process start per call; format codes differ between systems. |
| UTC only | reasoned | The board entry and the usage line would show a different hour than the Python copy: the two copies would no longer answer alike, which is the point of the whole piece. |

## Recommendation: use chrono (`default-features = false, features = ["clock"]`)
One reason: it is the long-established, widely used answer, already reviewed by many eyes, and it keeps the program the same on all five systems with
no time-zone code of our own.

## The price, in plain numbers
- Cargo.lock grew from 18 to 50 entries. Most of the new ones belong to other systems (Android, Haiku, web, Windows helpers) and are not compiled
  into a given system's program; each of the five builds compiles only the ones its own system needs.
- Every build uses `cargo build --locked` / `cargo test --locked`, so a crate cannot change between builds without a commit that shows it.
- The programs are rebuilt by the automatic run and checked against bin/SOURCE-STAMP, so what ships is what was built from the committed lock file.

## What stays our own code
The two formats and their rounding (checks/src/small.rs: `local_time`, `py_round`, the board heading's date and time) and the test that runs the
Python and the program side by side (scripts/small-hooks-selftest.py). chrono only supplies "the local time for this moment".

## If this is turned down
Fallback is already in place: the Python copy runs wherever no program is found. The smallest build would drop the dates from the board entry
(no time of day) and read the usage line's day names from a fixed UTC offset, at the cost of differing from Python; not recommended.
