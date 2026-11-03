# Muster, step by step

You do not need to know anything about terminals or code to follow this.

## 1. Install (once)
**In the Claude desktop app:**
1. Open the Claude app and click Code.
2. Start a chat and send: `Please run these two commands: claude plugin marketplace add d4trhban3/muster, then claude plugin install muster@muster-kit --scope user`
3. Click Allow when it asks to run them. It says Muster is installed for every folder ("scope: user").

**In a terminal:** run `claude plugin marketplace add d4trhban3/muster`, then
`claude plugin install muster@muster-kit --scope user`.

## 2. Set up your crew (once per project)
1. Start a new chat in your project's folder (in the desktop app, pick the folder when you start the chat). When
   Claude asks whether you trust the folder, say yes: the crew's chats cannot start without it.
2. Type `/muster:setup` and press Enter.
3. A setup page opens: in the side browser of the desktop app, or in your own web browser.
4. In the first box, write what you are building and your vision, in your own words.
5. Your crew shows as cards: Manager_001, Builder_A_001, Designer_001 and Inspector_001 are always there.
6. Add any add-ons you want: extra builders, Sketchpad_001, AI_Socket_001, Agent_Teacher_001. When three or more
   workers build, Design_Inspector_001 appears on its own.
7. "What the crew asks you first": spending money, keys or passwords, and deleting anything are always on. Type
   anything else you want to be asked about first, and press Add.
8. Press Start, then go back to Claude. It starts your crew.

## 3. Working with your crew
- Talk only to **Manager_001**. In the desktop app it is in the sidebar, in a group named after your project. In a
  terminal, the manager is the chat you open in your project's folder with the one line the setup gives you; to look
  in on another worker, type `claude agents --cwd .` there, pick it, and press the left arrow key to go back.
- Say what you want in your own words. The manager sorts it: an **order** goes straight to a worker; a **question**
  ("why does this look off?") gets looked into and answered with choices; an **idea** is parked on your list without
  starting work.
- Your list is `muster/OWNERS-LIST.md`: what you asked for, word for word, and where each thing stands.
- The manager asks one question at a time; the question names the choices, each is a button, and its pick is marked. It messages you on its own only for
  that question, a one-line "Closed" note, something that failed for good, or something it needs your yes for.
- To bring a finished item back: "reopen" and its number.
- To speed things up: tell the manager. The manager and the inspectors then think harder (more usage).

## 4. What happens on its own
- Every worker is its own chat with its own copy of your project folder, so no two workers edit the same file.
- When a chat gets long, it hands over to a fresh one with the next number (Builder_A_002, and so on). Old chats are
  kept, never deleted.
- Nobody checks their own work: builders hand finished work to an inspector, who passes it or sends it back.
