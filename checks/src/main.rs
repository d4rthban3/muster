//! muster-checks: Muster's coded checks as one ready-built program per system.
//!   muster-checks rules|guard|talk|board-stop   the hooks (a hook's JSON on standard input; same output as the Python copies)
//!   muster-checks renew|precompact   the SessionStart (compact) and PreCompact hooks; usage   the Usage line (scripts/usage.py)
//!   muster-checks worker-queue   the worker queue Stop hook (scripts/worker-queue-check.py), also --list [--worker name]
//!   muster-checks idle-check   the idle-crew Stop hook (scripts/idle-check.py), also --project DIR and --list
//!   muster-checks record        reads one worker-to-worker record on standard input; exit 0 if valid, 1 and the reason if not.
mod boardstop;
mod common;
mod idle;
mod record;
mod rules;
mod small;
mod talk;
mod wq;

use std::io::Read;

fn main() {
    let args: Vec<String> = std::env::args().skip(1).collect();
    match args.first().map(String::as_str) {
        Some("record") => {
            let mut text = String::new();
            if std::io::stdin().read_to_string(&mut text).is_err() { eprintln!("could not read the record"); std::process::exit(2); }
            match record::validate(&text, &common::project_things("", "")) {
                Ok(()) => println!("OK"),
                Err(why) => { println!("BAD: {why}"); std::process::exit(1); }
            }
        }
        Some("rules") => std::process::exit(rules::run()),
        Some("guard") => std::process::exit(rules::run_guard()),
        Some("talk") => std::process::exit(talk::run()),
        Some("board-stop") => std::process::exit(boardstop::run()),
        Some("renew") => std::process::exit(small::renew()),
        Some("precompact") => std::process::exit(small::precompact()),
        Some("worker-queue") => std::process::exit(wq::run(&args[1..])),
        Some("idle-check") => std::process::exit(idle::run(&args[1..])),
        Some("usage") => std::process::exit(small::usage(&args[1..])),
        _ => { eprintln!("usage: muster-checks record|rules|guard|talk|board-stop|renew|precompact|worker-queue|idle-check < input.json, or usage [--session id] [--limit-percent n]"); std::process::exit(2); }
    }
}
