import { parse } from './parse'
// The look is kept per group. A group is a project: its git repository's main
// folder (so a project's worktrees share one look), or else the folder the
// session started in. Each group's choices are one entry in this plugin's own
// store file under the Claude Code configuration folder; a group with no entry
// uses the defaults.
const HEX = /^#[0-9a-fA-F]{6}$/
export const KEYS = ['chipFont', 'questionHeadingColor', 'cardHeadingColor', 'choiceChipColor', 'lineTopColor', 'lineBottomColor', 'questionBorderColor', 'questionFieldColor', 'cardBorderColor', 'cardFieldColor', 'choiceBorderColor', 'choiceFieldColor']

// A host with no store keeps the choices for the session only (and the test kit has none).
const memory = new Map<string, unknown>()
export async function kvGet($: any, k: string): Promise<unknown> { try { return await $.store.get(k) } catch { return memory.get(k) } }
export async function kvSet($: any, k: string, v: unknown): Promise<void> { try { await $.store.set(k, v) } catch { memory.set(k, JSON.parse(JSON.stringify(v))) } }
export async function kvDel($: any, k: string): Promise<void> { try { await $.store.delete(k) } catch { memory.delete(k) } }

// A project is one group however many folders hold it: a crew's workers each work in their own
// copy (a worktree or a clone), all with the same origin remote, so the remote names the group
// (host/owner/name, lowercase, no ".git"). A project with no remote falls back to its repository
// folder, else the folder the session started in.
export function groupKey(remote: string | null | undefined, root: string): string {
  if (typeof remote === 'string' && remote.trim() !== '') {
    const r = remote.trim().replace(/^[a-z+]+:\/\//i, '').replace(/^[^@/]+@/, '').replace(':', '/').replace(/\.git$/i, '').replace(/\/+$/, '').toLowerCase()
    if (r !== '') return 'remote:' + r
  }
  return root
}
// The key this plugin used before groups followed the remote: the repository's own folder.
async function ids($: any): Promise<{ id: string; legacy: string }> {
  let root = ''
  let remote: string | null = null
  try {
    const repo = await $.session.repo()
    if (repo && typeof repo.root === 'string' && repo.root !== '') { root = repo.root; remote = typeof repo.remote === 'string' ? repo.remote : null }
  } catch { /* not a repository */ }
  if (root === '') {
    try { root = String(await $.session.root()) } catch {
      try { root = String(await $.session.cwd()) } catch { root = 'unknown' }
    }
  }
  return { id: groupKey(remote, root), legacy: root }
}
// The project's name for the owner's words is the name typed at setup, which every crew chat carries as the
// suffix of its name (Manager_Muster, Builder A_PINR). The project's muster/CREW.md lists those chats.
export function nameFromCrew(text: string): string {
  const m = /^\|\s*(?:Manager|Builder|Designer|Inspector|Design Inspector)(?: [A-Z])?_([^|_]+?)(?:_\d{3})?\s*\|/m.exec(text)
  return m === null ? '' : m[1]!.trim()
}
// With no crew file: the git origin remote's last part as written, else the repository's folder name.
export function nameFromRemote(remote: string | null | undefined): string {
  if (typeof remote !== 'string') return ''
  const r = remote.trim().replace(/\.git$/i, '').replace(/\/+$/, '')
  return r.split(/[/:]/).pop() ?? ''
}
export async function pickName($: any): Promise<string> {
  let repo: any = null
  try { repo = await $.session.repo() } catch { /* not a repository */ }
  const roots: string[] = []
  if (repo && typeof repo.root === 'string' && repo.root !== '') roots.push(repo.root)
  try { roots.push(String(await $.session.root())) } catch { /* none */ }
  try { roots.push(String(await $.session.cwd())) } catch { /* none */ }
  for (const r of roots) {
    try {
      const n = nameFromCrew(String(await $.fs.read(r.replace(/\/+$/, '') + '/muster/CREW.md')))
      if (n !== '') return n
    } catch { /* no crew file here */ }
  }
  const n = nameFromRemote(repo && typeof repo.remote === 'string' ? repo.remote : null)
  if (n !== '') return n
  if (repo && typeof repo.root === 'string' && repo.root !== '') return projectName(repo.root)
  return roots[0] !== undefined ? projectName(roots[0]) : ''
}
export async function groupId($: any): Promise<string> { return (await ids($)).id }
// What was kept for this group: under its own key, else (only when the group is this session's) under
// the folder key it was kept under before, so nothing already set is lost.
export async function keptFor($: any, prefix: string, id?: string): Promise<Record<string, unknown> | undefined> {
  let key = id
  let legacy = ''
  if (key === undefined) { const i = await ids($); key = i.id; legacy = i.legacy }
  let raw = await kvGet($, prefix + key)
  if ((raw === undefined || raw === null) && legacy !== '' && legacy !== key) raw = await kvGet($, prefix + legacy)
  return raw && typeof raw === 'object' ? (raw as Record<string, unknown>) : undefined
}

export const groupName = (id: string) => id.split('/').filter(Boolean).pop() ?? id

export async function loadGroup($: any, id?: string): Promise<Record<string, string>> {
  const out: Record<string, string> = {}
  try {
    const raw = await keptFor($, 'group:', id)
    if (raw && typeof raw === 'object') {
      for (const k of KEYS) {
        const v = raw[k]
        if (typeof v === 'string' && (k === 'chipFont' ? v !== '' : HEX.test(v))) out[k] = v
      }
    }
  } catch { /* no store: defaults */ }
  return out
}

export async function saveGroup($: any, key: string, value: string | null, id?: string): Promise<void> {
  if (!KEYS.includes(key)) return
  try {
    const gid = id ?? (await groupId($))
    const now = await loadGroup($, id)
    if (value === null) delete now[key]; else now[key] = value
    await kvSet($, 'group:' + gid, now)
  } catch { /* a store that refuses leaves the look as it was */ }
}

export async function clearGroup($: any, id?: string): Promise<void> {
  try {
    if (id !== undefined) { await kvDel($, 'group:' + id); return }
    const i = await ids($)
    await kvDel($, 'group:' + i.id)
    if (i.legacy !== i.id) await kvDel($, 'group:' + i.legacy)
  } catch { /* nothing kept */ }
}

// True when the plugin's store really keeps values between sessions.
export async function storeWorks($: any): Promise<boolean> {
  try {
    await $.store.set('probe', 1)
    const ok = (await $.store.get('probe')) === 1
    await $.store.delete('probe')
    return ok
  } catch { return false }
}

// Which letter was picked on which question, so it stays lit in the chat. Kept
// by the question's text (a short hash), the newest 200 only.
export const hashText = (t: string) => { let h = 5381; for (let i = 0; i < t.length; i++) h = ((h * 33) ^ t.charCodeAt(i)) >>> 0; return h.toString(36) + t.length.toString(36) }
export async function loadPicks($: any): Promise<Record<string, string>> {
  try {
    const raw = await kvGet($, 'picks')
    if (raw && typeof raw === 'object') return raw as Record<string, string>
  } catch { /* none kept */ }
  return {}
}
export async function pickedOn($: any, text: string): Promise<string | undefined> {
  const v = (await loadPicks($))[hashText(text)]
  return typeof v === 'string' && /^[A-Z]$/.test(v) ? v : undefined
}
// the words he typed instead of a letter, kept beside the letters under the same key (marked with a leading "=")
export async function typedOn($: any, text: string): Promise<string | undefined> {
  const v = (await loadPicks($))[hashText(text)]
  return typeof v === 'string' && v.startsWith('=') ? v.slice(1) : undefined
}
export async function savePick($: any, text: string, letter: string): Promise<void> {
  try {
    const all = await loadPicks($)
    const k = hashText(text)
    delete all[k]
    all[k] = letter
    const keys = Object.keys(all)
    for (const old of keys.slice(0, Math.max(0, keys.length - 200))) delete all[old]
    await kvSet($, 'picks', all)
  } catch { /* a store that refuses keeps nothing */ }
}

// An undone pick: the question goes back to unpicked, as if never clicked.
export async function clearPick($: any, text: string): Promise<void> {
  try {
    const all = await loadPicks($)
    const k = hashText(text)
    if (!(k in all)) return
    delete all[k]
    await kvSet($, 'picks', all)
  } catch { /* a store that refuses keeps nothing */ }
}

// Does the chat still hold the answer to this question? The question's message is found
// in the transcript, then a later message of the owner's that is the letter, or the typed
// "Answer to ..." line. 'unknown' when the question itself is not in the transcript.
// What a click or typed answer calls its own question: the heading and the question's first line,
// so no answer can be read as the answer to another question.
export function answerTag(text: string): string {
  const ps = parse(text)?.pieces ?? []
  const head = ps.find(p => p.kind === 'title') as { word: string; job: string } | undefined
  const first = (ps.find(p => p.kind === 'md') as { text: string } | undefined)?.text.trim().split('\n')[0]!.replace(/[*_`#]/g, '').trim().slice(0, 60) ?? ''
  const h = head !== undefined ? `${head.word} \u00b7 ${head.job}` : ''
  return h !== '' ? (first !== '' ? `${h} (${first})` : h) : (first !== '' ? first : 'the question above')
}
// What a click sends: only the clicked option's own text, as the card shows it ("A. Arena only"),
// nothing before or after. Words the owner typed are sent as typed. (A letter this card has no
// option for goes as the bare letter.)
// The project's name from its root folder; a crew worktree (.../<project>/.claude/worktrees/<name>) names its project.
export function projectName(root: string): string {
  const base = root.replace(/\/+$/, '').split('/.claude/worktrees/')[0]!
  return base.split('/').pop() ?? ''
}
// What a click puts in the box is the owner's words in the owner's voice: the card's "(my pick)" is the
// assistant's, so it reads "(<project> pick)" there.
export function rename(line: string, name: string): string {
  return name === '' ? line : line.replace(/\(my pick\)/gi, `(${name} pick)`)
}
export function optionLine(text: string, letter: string, name = ''): string {
  const o = (parse(text)?.pieces ?? []).find(p => p.kind === 'choice' && p.letter === letter) as { text: string } | undefined
  const t = o?.text.replace(/[*_`]/g, '').replace(/\s+/g, ' ').trim() ?? ''
  return t !== '' ? rename(`${letter}. ${t}`, name) : letter
}
// A card can keep the props of an early draw while its message is still streaming, so the text a click
// names may be the question cut short. The finished question is the longest seen text it is the start of.
export function fullestText(text: string, seen: Iterable<string>): string {
  let best = text
  for (const t of seen) if (t.length > best.length && t.startsWith(text)) best = t
  return best
}
export const answerLine = (text: string, words: string, name = '') => (/^[A-Z]$/.test(words) ? optionLine(text, words, name) : words)
export type Said = { role: string; text: string }
export function answerIn(msgs: Said[], question: string, mark: string, name = ''): 'yes' | 'no' | 'unknown' {
  const q = question.trim()
  let at = -1
  msgs.forEach((m, i) => { if (m.role === 'assistant' && m.text.includes(q)) at = i })
  if (at < 0) return 'unknown'
  const typed = mark.startsWith('=')
  for (const m of msgs.slice(at + 1)) {
    if (m.role !== 'user') continue
    const t = m.text.trim()
    // the clicked option's own text, or the words he typed; the older "Answer to ..." line and a bare letter count too
    const old = `Answer to ${answerTag(question)}: `
    if (typed ? (t.startsWith(mark.slice(1)) || (t.startsWith(old) && t.includes(mark.slice(1, 40)))) : (t === optionLine(question, mark) || (name !== '' && t === optionLine(question, mark, name)) || t === old + mark || t.replace(/[*.)]/g, '').toUpperCase() === mark)) return 'yes'
  }
  return 'no'
}
// Questions whose answer this run just sent: shown picked until the chat is seen to hold it.
export const sent = new Set<string>()
// Questions whose answer was seen in the chat: if it later is not there, it was rewound.
export const seenIn = new Set<string>()
export async function answerStands($: any, question: string, mark: string): Promise<boolean> {
  let msgs: Said[]
  try {
    const got = await $.session.messages()
    if (!Array.isArray(got)) return true
    msgs = got
  } catch { return true }
  const name = await pickName($)
  const r = answerIn(msgs, question, mark, name)
  if (r === 'unknown') return true
  if (r === 'yes') { seenIn.add(question); sent.delete(question); return true }
  // not there: fine while it has only just been sent; gone once it was seen, or was never sent now
  return sent.has(question) && !seenIn.has(question)
}
