//! muster-checks: Muster's coded checks as one ready-built program per system.
//!   muster-checks record        reads one worker-to-worker record on standard input; exit 0 if valid, 1 and the reason if not.
mod record;

use std::io::Read;

fn main() {
    let args: Vec<String> = std::env::args().skip(1).collect();
    match args.first().map(String::as_str) {
        Some("record") => {
            let mut text = String::new();
            if std::io::stdin().read_to_string(&mut text).is_err() { eprintln!("could not read the record"); std::process::exit(2); }
            match record::validate(&text) {
                Ok(()) => println!("OK"),
                Err(why) => { println!("BAD: {why}"); std::process::exit(1); }
            }
        }
        _ => { eprintln!("usage: muster-checks record < record.json"); std::process::exit(2); }
    }
}
