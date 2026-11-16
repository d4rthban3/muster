// An opt-in whole-app background: a calm, slow liquid-glass scene (soft coloured light on a
// deep ground) or the owner's own small picture, with the app's own panels frosted over it.
// Off unless the owner switches it on in /look; its colours and picture are set there too.
import { kvGet, kvSet, kvDel } from './group'
import { HEX } from './chip'

const KEY = 'frostedBackground'
export const GLASS_COLOURS = [
  { key: 'glassColour1', label: 'Light 1', dflt: '#5b4bb8' },
  { key: 'glassColour2', label: 'Light 2', dflt: '#3b6fd6' },
  { key: 'glassColour3', label: 'Light 3', dflt: '#b89a3c' },
]
export const GLASS_IMAGE = 'glassImage'
const MAX_IMAGE = 90000 // bytes: a scene is at most 131,072 characters, and base64 adds a third

export async function glassOn($: any): Promise<boolean> {
  try { return (await kvGet($, KEY)) === 'on' } catch { return false }
}
export async function setGlassFlag($: any, on: boolean): Promise<void> {
  try { await kvSet($, KEY, on ? 'on' : 'off') } catch { /* a store that refuses keeps it off */ }
}
export async function glassSettings($: any): Promise<Record<string, string>> {
  const out: Record<string, string> = {}
  for (const c of GLASS_COLOURS) {
    let v: unknown
    try { v = await kvGet($, c.key) } catch { v = undefined }
    out[c.key] = typeof v === 'string' && HEX.test(v) ? v : c.dflt
  }
  let img: unknown
  try { img = await kvGet($, GLASS_IMAGE) } catch { img = undefined }
  out[GLASS_IMAGE] = typeof img === 'string' ? img : ''
  return out
}
export async function setGlassSetting($: any, key: string, value: string | null): Promise<void> {
  if (key !== GLASS_IMAGE && !GLASS_COLOURS.some(c => c.key === key)) return
  try { if (value === null) await kvDel($, key); else await kvSet($, key, value) } catch { /* kept as it was */ }
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

// Calm: three big soft lights that barely drift on a deep ground, a faint light from the top left.
const blob = (cx: number, cy: number, r: number, c: string, dx: number, dy: number, dur: number) =>
  `<circle cx="${cx}" cy="${cy}" r="${r}" fill="${c}" fill-opacity="0.55"><animateTransform attributeName="transform" type="translate" values="0 0;${dx} ${dy};${-dx / 2} ${dy * 0.6};0 0" dur="${dur}s" repeatCount="indefinite"/></circle>`
const HEAD = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1600 1000" preserveAspectRatio="xMidYMid slice">`
export function sceneOf(c1: string, c2: string, c3: string, uri?: string): string {
  if (uri !== undefined) {
    return HEAD + `<rect width="1600" height="1000" fill="#12141b"/><image href="${uri}" x="0" y="0" width="1600" height="1000" preserveAspectRatio="xMidYMid slice"/><rect width="1600" height="1000" fill="#12141b" fill-opacity="0.35"/></svg>`
  }
  return (
    HEAD + `<defs><filter id="b" x="-50%" y="-50%" width="200%" height="200%"><feGaussianBlur stdDeviation="110"/></filter>` +
    `<radialGradient id="l" cx="0.12" cy="0.05" r="0.8"><stop offset="0" stop-color="#ffffff" stop-opacity="0.07"/><stop offset="1" stop-color="#ffffff" stop-opacity="0"/></radialGradient></defs>` +
    `<rect width="1600" height="1000" fill="#12141b"/><g filter="url(#b)">` +
    blob(380, 300, 300, c1, 120, 70, 70) + blob(1200, 360, 280, c2, -110, 90, 80) + blob(820, 820, 320, c3, -130, -60, 90) +
    `</g><rect width="1600" height="1000" fill="url(#l)"/></svg>`
  )
}

export function glass(on: any) {
  on('ui.render', { component: 'Backdrop' }, async ($: any, e: any, next: any) => {
    if ((e.props as any).scene !== 'liquid' || (e.surface !== 'desktop' && e.surface !== 'mobile')) return next(e)
    const { Svg } = $.ui.resolve(e)
    const s = await glassSettings($)
    const img = await imageData($, s[GLASS_IMAGE])
    return <Svg source={sceneOf(s.glassColour1, s.glassColour2, s.glassColour3, img.uri)} alt="A calm, soft liquid-glass background behind the chat" isInteractive />
  })
}
