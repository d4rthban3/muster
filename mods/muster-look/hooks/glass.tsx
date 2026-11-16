// An opt-in whole-app background: a calm, slow liquid-glass scene (soft coloured light on a
// deep ground) or the owner's own small picture, with the app's own panels frosted over it.
// Off unless the owner switches it on in /look; its colours and picture are set there too.
import { kvGet, kvSet, groupId } from './group'
import { HEX } from './chip'

const KEY = 'frostedBackground'
export const GLASS_COLOURS = [
  { key: 'glassColour1', label: 'Glow bottom-left', dflt: '#5b4bb8' },
  { key: 'glassColour2', label: 'Glow top-right', dflt: '#3b6fd6' },
]
export const GLASS_IMAGE = 'glassImage'
const MAX_IMAGE = 90000 // bytes: a scene is at most 131,072 characters, and base64 adds a third

// Kept per group, like the chip colours: one record under 'glass:<group>' holds the switch, the
// two glow colours and the picture, so setting them in one group never changes another's.
type Rec = Record<string, string>
async function recOf($: any, id?: string): Promise<Rec> {
  try {
    const raw = await kvGet($, 'glass:' + (id ?? (await groupId($))))
    if (raw && typeof raw === 'object') return { ...(raw as Rec) }
  } catch { /* nothing kept */ }
  return {}
}
async function putRec($: any, r: Rec, id?: string): Promise<void> {
  try { await kvSet($, 'glass:' + (id ?? (await groupId($))), r) } catch { /* kept as it was */ }
}
export async function glassOn($: any, id?: string): Promise<boolean> {
  return (await recOf($, id))[KEY] === 'on'
}
export async function setGlassFlag($: any, on: boolean, id?: string): Promise<void> {
  const r = await recOf($, id)
  r[KEY] = on ? 'on' : 'off'
  await putRec($, r, id)
}
export async function glassSettings($: any, id?: string): Promise<Record<string, string>> {
  const r = await recOf($, id)
  const out: Record<string, string> = {}
  for (const c of GLASS_COLOURS) {
    const v = r[c.key]
    out[c.key] = typeof v === 'string' && HEX.test(v) ? v : c.dflt
  }
  out[GLASS_IMAGE] = typeof r[GLASS_IMAGE] === 'string' ? r[GLASS_IMAGE] : ''
  return out
}
export async function setGlassSetting($: any, key: string, value: string | null, id?: string): Promise<void> {
  if (key !== GLASS_IMAGE && !GLASS_COLOURS.some(c => c.key === key)) return
  const r = await recOf($, id)
  if (value === null) delete r[key]; else r[key] = value
  await putRec($, r, id)
}

export const SCENE_ARGS = { backdrop: { scene: 'liquid', glass: { blur: 28, tint: 'rgba(25,28,36,1)', opacity: 0.42 } } }
export async function applyGlass($: any, on: boolean): Promise<void> {
  try {
    if (on) await $.theme.set(SCENE_ARGS)
    else await $.theme.clear()
  } catch { /* no theme here */ }
}

// The person's own picture: read from the path they gave, kept small enough to ride inside the scene.
export async function imageData($: any, path: string): Promise<{ uri?: string; why?: string }> {
  if (path === '') return {}
  const kind = /\.(jpe?g)$/i.test(path) ? 'jpeg' : /\.png$/i.test(path) ? 'png' : ''
  if (kind === '') return { why: 'Use a .jpg or .png file.' }
  try {
    const r = (await $.fs.read(path, { as: 'bytes' })) as { base64: string }
    if (r.base64.length * 0.75 > MAX_IMAGE) return { why: 'That picture is over 90 KB. Save a smaller copy (about 1000 pixels wide, low quality).' }
    return { uri: `data:image/${kind};base64,${r.base64}` }
  } catch { return { why: 'That file could not be read.' } }
}

// Calm: two soft glows, one rising from the bottom-left corner and one from the top-right, on a deep ground.
const HEAD = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1600 1000" preserveAspectRatio="xMidYMid slice">`
const glow = (id: string, cx: number, cy: number, c: string, dur: number) =>
  `<radialGradient id="${id}" gradientUnits="userSpaceOnUse" cx="${cx}" cy="${cy}" r="900"><stop offset="0" stop-color="${c}" stop-opacity="0.5"/><stop offset="0.5" stop-color="${c}" stop-opacity="0.16"/><stop offset="1" stop-color="${c}" stop-opacity="0"/><animate attributeName="r" values="900;980;900" dur="${dur}s" repeatCount="indefinite"/></radialGradient>`
export function sceneOf(c1: string, c2: string, uri?: string): string {
  if (uri !== undefined) {
    return HEAD + `<rect width="1600" height="1000" fill="#12141b"/><image href="${uri}" x="0" y="0" width="1600" height="1000" preserveAspectRatio="xMidYMid slice"/><rect width="1600" height="1000" fill="#12141b" fill-opacity="0.35"/></svg>`
  }
  return (
    HEAD + `<defs>${glow('a', 0, 1000, c1, 60)}${glow('b', 1600, 0, c2, 75)}</defs>` +
    `<rect width="1600" height="1000" fill="#12141b"/><rect width="1600" height="1000" fill="url(#a)"/><rect width="1600" height="1000" fill="url(#b)"/></svg>`
  )
}

export function glass(on: any) {
  on('ui.render', { component: 'Backdrop' }, async ($: any, e: any, next: any) => {
    if ((e.props as any).scene !== 'liquid' || (e.surface !== 'desktop' && e.surface !== 'mobile')) return next(e)
    const { Svg } = $.ui.resolve(e)
    const s = await glassSettings($)
    const img = await imageData($, s[GLASS_IMAGE])
    return <Svg source={sceneOf(s.glassColour1, s.glassColour2, img.uri)} alt="A calm, soft liquid-glass background behind the chat" isInteractive />
  })
}
