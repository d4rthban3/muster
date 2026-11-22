// One-time copy of what the look kept while it was its own plugin (muster-look): each project's
// colours, glass background and picked answers. Claude Code keeps a plugin's saved values in a file
// of its own under <config>/plugins/store, named for the plugin ("muster-look_<marketplace>-<id>.json"),
// so the look, now part of the main plugin, starts with an empty store. This reads those old files
// once and puts their values into this plugin's store. It never overwrites a value already here,
// never deletes or changes the old file, and a failed read is tried again at the next start.
const DONE = 'migrated:muster-look'

// every value this run wrote (new keys and merged picks), so the look knows when what it read is out of date
export const wrote = { n: 0 }
export async function migrateLook($: any): Promise<number> {
  let copied = 0
  try {
    if ((await $.store.get(DONE)) !== undefined) return 0
    let dir = (await $.env.get('CLAUDE_CONFIG_DIR')) as string | undefined
    if (dir === undefined || dir === '') {
      const home = ((await $.env.get('HOME')) ?? (await $.env.get('USERPROFILE'))) as string | undefined
      if (home === undefined || home === '') return 0
      dir = home + '/.claude'
    }
    dir = dir.replace(/[\\/]+$/, '') + '/plugins/store'
    let rows: Array<{ name: string; kind: string; mtimeMs: number }>
    try { rows = await $.fs.list(dir) } catch { rows = [] }
    // newest file first: where two old files hold the same key, the newer one wins
    const old = rows.filter(r => r.kind === 'file' && /^muster-look_.*\.json$/.test(r.name)).sort((a, b) => b.mtimeMs - a.mtimeMs)
    for (const f of old) {
      let data: Record<string, unknown>
      try {
        const parsed = JSON.parse(await $.fs.read(dir + '/' + f.name))
        if (parsed === null || typeof parsed !== 'object' || Array.isArray(parsed)) continue
        data = parsed as Record<string, unknown>
      } catch { return copied }
      for (const k of Object.keys(data)) {
        if (k === DONE) continue
        const have = await $.store.get(k)
        if (have === undefined || have === null) {
          await $.store.set(k, data[k])
          copied++
          wrote.n++
        } else if (k === 'picks' && typeof have === 'object' && typeof data[k] === 'object' && data[k] !== null) {
          // picked answers: add the ones this store does not have yet
          await $.store.set(k, { ...(data[k] as object), ...(have as object) })
          wrote.n++
        }
      }
    }
    await $.store.set(DONE, { at: Date.now(), copied })
  } catch { /* tried again at the next start */ }
  return copied
}
