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
async function kvGet($: any, k: string): Promise<unknown> { try { return await $.store.get(k) } catch { return memory.get(k) } }
async function kvSet($: any, k: string, v: unknown): Promise<void> { try { await $.store.set(k, v) } catch { memory.set(k, JSON.parse(JSON.stringify(v))) } }
async function kvDel($: any, k: string): Promise<void> { try { await $.store.delete(k) } catch { memory.delete(k) } }

export async function groupId($: any): Promise<string> {
  try {
    const repo = await $.session.repo()
    if (repo && typeof repo.root === 'string' && repo.root !== '') return repo.root
  } catch { /* not a repository */ }
  try { return String(await $.session.root()) } catch { /* fall through */ }
  try { return String(await $.session.cwd()) } catch { return 'unknown' }
}

export const groupName = (id: string) => id.split('/').filter(Boolean).pop() ?? id

export async function loadGroup($: any, id?: string): Promise<Record<string, string>> {
  const out: Record<string, string> = {}
  try {
    const raw = (await kvGet($, 'group:' + (id ?? (await groupId($))))) as Record<string, unknown> | undefined
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
    const now = await loadGroup($, gid)
    if (value === null) delete now[key]; else now[key] = value
    await kvSet($, 'group:' + gid, now)
  } catch { /* a store that refuses leaves the look as it was */ }
}

export async function clearGroup($: any, id?: string): Promise<void> {
  try { await kvDel($, 'group:' + (id ?? (await groupId($)))) } catch { /* nothing kept */ }
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
  const first = (ps.find(p => p.kind === 'md') as { text: string } | undefined)?.text.trim().split('\n')[0].replace(/[*_`#]/g, '').trim().slice(0, 60) ?? ''
  const h = head !== undefined ? `${head.word} \u00b7 ${head.job}` : ''
  return h !== '' ? (first !== '' ? `${h} (${first})` : h) : (first !== '' ? first : 'the question above')
}
export const answerLine = (text: string, words: string) => `Answer to ${answerTag(text)}: ${words}`
export type Said = { role: string; text: string }
export function answerIn(msgs: Said[], question: string, mark: string): 'yes' | 'no' | 'unknown' {
  const q = question.trim()
  let at = -1
  msgs.forEach((m, i) => { if (m.role === 'assistant' && m.text.includes(q)) at = i })
  if (at < 0) return 'unknown'
  const typed = mark.startsWith('=')
  for (const m of msgs.slice(at + 1)) {
    if (m.role !== 'user') continue
    const t = m.text.trim()
    // an answer names its own question; a bare letter (sent by an older version) counts too
    const line = `Answer to ${answerTag(question)}: `
    if (typed ? t.startsWith(line) && t.includes(mark.slice(1, 40)) : (t === line + mark || t.replace(/[*.)]/g, '').toUpperCase() === mark)) return 'yes'
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
  const r = answerIn(msgs, question, mark)
  if (r === 'unknown') return true
  if (r === 'yes') { seenIn.add(question); sent.delete(question); return true }
  // not there: fine while it has only just been sent; gone once it was seen, or was never sent now
  return sent.has(question) && !seenIn.has(question)
}
