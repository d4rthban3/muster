// An opt-in whole-app background: a calm, slow liquid-glass scene (soft coloured light on a
// deep ground) or the owner's own small picture, with the app's own panels frosted over it.
// Off unless the owner switches it on in /look; its colours and picture are set there too.
import { kvSet, groupId, keptFor } from './group'
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
    const raw = await keptFor($, 'glass:', id)
    if (raw) return { ...(raw as Rec) }
  } catch { /* nothing kept */ }
  return {}
}
async function putRec($: any, r: Rec, id?: string): Promise<void> {
  shown = undefined // any change to the switch, a colour or the picture rebuilds the scene once
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

// Calm: two soft glows, one rising from the bottom-left corner and one from the top-right, on a deep
// ground. Smooth like liquid glass: each glow falls off along an eased (gaussian-like) curve with many
// stops, so there are no steps or rings; a very fine grain is laid over it so 8-bit colour cannot
// band; and a glow drifts by moving a finished picture slowly (a glide, never a redraw of the gradient).
const FALL = [1, 0.97, 0.9, 0.79, 0.66, 0.52, 0.39, 0.27, 0.18, 0.11, 0.06, 0.03, 0.01, 0]
const HEAD = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1600 1000" preserveAspectRatio="xMidYMid slice">`
const GRAIN = `<filter id="n" x="0" y="0" width="100%" height="100%"><feTurbulence type="fractalNoise" baseFrequency="0.8" numOctaves="2" seed="7" stitchTiles="stitch"/><feColorMatrix type="matrix" values="0 0 0 0 0.5  0 0 0 0 0.5  0 0 0 0 0.5  0 0 0 0.9 -0.2"/></filter>`
const glow = (id: string, c: string) =>
  `<radialGradient id="${id}" cx="0.5" cy="0.5" r="0.5">${FALL.map((f, i) => `<stop offset="${(i / (FALL.length - 1)).toFixed(3)}" stop-color="${c}" stop-opacity="${(f * 0.5).toFixed(3)}"/>`).join('')}</radialGradient>`
// a glow is a big disc that glides slowly back and forth, eased at both ends
const drift = (id: string, cx: number, cy: number, dx: number, dy: number, dur: number) =>
  `<rect x="${cx - 1100}" y="${cy - 1100}" width="2200" height="2200" fill="url(#${id})"><animateTransform attributeName="transform" type="translate" values="0 0;${dx} ${dy};0 0" dur="${dur}s" calcMode="spline" keyTimes="0;0.5;1" keySplines="0.45 0 0.55 1;0.45 0 0.55 1" repeatCount="indefinite"/></rect>`
export function sceneOf(c1: string, c2: string, uri?: string): string {
  if (uri !== undefined) {
    return HEAD + `<rect width="1600" height="1000" fill="#12141b"/><image href="${uri}" x="0" y="0" width="1600" height="1000" preserveAspectRatio="xMidYMid slice"/><rect width="1600" height="1000" fill="#12141b" fill-opacity="0.35"/></svg>`
  }
  return (
    HEAD + `<defs>${glow('a', c1)}${glow('b', c2)}${GRAIN}</defs>` +
    `<rect width="1600" height="1000" fill="#12141b"/>` +
    drift('a', 0, 1000, 60, -40, 90) + drift('b', 1600, 0, -60, 40, 110) +
    `<rect width="1600" height="1000" filter="url(#n)" opacity="0.05"/></svg>`
  )
}

// The scene a redraw needs is built once per group and kept: the stored settings, the picture file (read
// and turned into base64) and the 130,000-character picture are not made again on every Backdrop draw.
// A setting change (putRec) or a new chat (resetScene) drops it; a picture file edited in place under the
// same path shows at the next of those.
let shown: { id: string; source: string } | undefined
export function resetScene(): void { shown = undefined }
export async function sceneSource($: any): Promise<string> {
  const id = await groupId($)
  if (shown !== undefined && shown.id === id) return shown.source
  const s = await glassSettings($)
  const img = await imageData($, s[GLASS_IMAGE]!)
  const source = sceneOf(s.glassColour1!, s.glassColour2!, img.uri)
  shown = { id, source }
  return source
}

export function glass(on: any) {
  on('ui.render', { component: 'Backdrop' }, async ($: any, e: any, next: any) => {
    if ((e.props as any).scene !== 'liquid' || (e.surface !== 'desktop' && e.surface !== 'mobile')) return next(e)
    const { Svg } = $.ui.resolve(e)
    return <Svg source={await sceneSource($)} alt="A calm, soft liquid-glass background behind the chat" isInteractive />
  })
}
