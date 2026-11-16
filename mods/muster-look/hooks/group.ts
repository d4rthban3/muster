// The look is kept per group. A group is a project: its git repository's main
// folder (so a project's worktrees share one look), or else the folder the
// session started in. Each group's choices are one entry in this plugin's own
// store file under the Claude Code configuration folder; a group with no entry
// uses the defaults.
const HEX = /^#[0-9a-fA-F]{6}$/
export const KEYS = ['chipFont', 'questionHeadingColor', 'cardHeadingColor', 'choiceChipColor', 'lineTopColor', 'lineBottomColor']

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
