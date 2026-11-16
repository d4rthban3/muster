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

// Is this question the newest thing the assistant said? Then a bare letter answers it clearly.
export async function isNewest($: any, text: string, latest: string): Promise<boolean> {
  try {
    const msgs = await $.session.messages()
    if (Array.isArray(msgs)) {
      for (let i = msgs.length - 1; i >= 0; i--) if (msgs[i].role === 'assistant') return String(msgs[i].text).includes(text.trim())
    }
  } catch { /* no transcript to read */ }
  return text === latest
}
