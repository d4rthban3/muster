# Muster, step by step

You do not need to know anything about terminals or code to follow this.

## 1. Install (once)
**In the Claude desktop app:**
1. Open the Claude app and click Code.
2. Start a chat and send: `Please run these two commands: claude plugin marketplace add d4rthban3/muster, then claude plugin install muster@muster-kit --scope user`
3. Click Allow when it asks to run them. It says Muster is installed for every folder ("scope: user").

**In a terminal:** run `claude plugin marketplace add d4rthban3/muster`, then
`claude plugin install muster@muster-kit --scope user`.

## 2. Set up your crew (once per project)
You do not need a project folder: Muster makes one for you, in a folder called Muster in your home folder.
1. Start a chat in Claude Code (any folder, or none).
2. Type `/muster:setup` and press Enter.
3. A setup page opens: in the side browser of the desktop app, or in your own web browser.
4. Type a short name for your project in "Project name". Your project's folder and its group in the sidebar get
   this name.
5. In the next box, write what you are building and your vision, in your own words.
6. Your crew shows as cards: Manager_<your project>_001, Builder A_<your project>_001, Designer_<your project>_001 and Inspector_<your project>_001 are always there.
7. Add any add-ons you want: extra builders, Sketchpad_<your project>_001, AI Socket_<your project>_001, Agent Teacher_<your project>_001. When three or more
   workers build, Design Inspector_<your project>_001 appears on its own.
8. "What the crew asks you first": spending money, keys or passwords, and deleting anything are always on. Type
   anything else you want to be asked about first, and press Add.
9. Press Start, then go back to Claude.
10. The app asks you to trust your new project folder twice: press "Trust workspace", then "Trust repository".
11. Muster starts your crew.
If you already have a project folder and open the chat in it, setup asks whether to use that folder or make a new one.

## 3. Working with your crew
- Talk only to **Manager_<your project>_001**. In the desktop app it is in the sidebar, in a group named after your project. In a
  terminal, the manager is the chat you open in your project's folder with the one line the setup gives you; to look
  in on another worker, type `claude agents --cwd .` there, pick it, and press the left arrow key to go back.
- Say what you want in your own words. The manager sorts it: an **order** goes straight to a worker; a **question**
  ("why does this look off?") gets looked into and answered with choices; an **idea** is parked on your list without
  starting work.
- Your list is `muster/OWNERS-LIST.md`: what you asked for, word for word, and where each thing stands.
- The manager asks one question at a time; the question names the choices, each is a button, and its pick is marked. It messages you on its own only for
  that question, a one-line "Closed" note, something that failed for good, something it needs your yes for, or to
  say the crew is idle, with what's next toward your goal as buttons. When a worker finishes, the manager gives it
  the next open item from your list that fits its job.
- To bring a finished item back: "reopen" and its number.
- To speed things up: tell the manager. The manager and the inspectors then think harder (more usage).

## 4. What happens on its own
- Every worker is its own chat with its own copy of your project folder, so no two workers edit the same file.
- When a chat gets long, it hands over to a fresh one with the next number (Builder A_<your project>_002, and so on). Old chats are
  kept, never deleted.
- Nobody checks their own work: builders hand finished work to an inspector, who passes it or sends it back.
