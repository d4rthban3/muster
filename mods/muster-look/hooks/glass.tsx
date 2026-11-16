// An opt-in whole-app frosted background: a slow, soft, coloured scene behind the
// chat, with the app's own panels frosted over it (real blur, the app's own).
// Off unless the owner switches it on in /look.
import { kvGet, kvSet } from './group'

const KEY = 'frostedBackground'
export async function glassOn($: any): Promise<boolean> {
  try { return (await kvGet($, KEY)) === 'on' } catch { return false }
}
export async function setGlassFlag($: any, on: boolean): Promise<void> {
  try { await kvSet($, KEY, on ? 'on' : 'off') } catch { /* a store that refuses keeps it off */ }
}

const SCENE_ARGS = { backdrop: { scene: 'liquid', glass: { blur: 28, tint: 'rgba(25,28,36,1)', opacity: 0.42 } } }
export async function applyGlass($: any, on: boolean): Promise<void> {
  try {
    if (on) await $.theme.set(SCENE_ARGS)
    else await $.theme.clear()
  } catch { /* no theme here */ }
}

// Deep dark ground, four soft blobs drifting slowly, a faint light from the top left.
const blob = (cx: number, cy: number, r: number, c: string, dx: number, dy: number, dur: number) =>
  `<circle cx="${cx}" cy="${cy}" r="${r}" fill="${c}"><animateTransform attributeName="transform" type="translate" values="0 0;${dx} ${dy};${-dx / 2} ${dy * 0.6};0 0" dur="${dur}s" repeatCount="indefinite"/></circle>`
const SCENE =
  `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1600 1000" preserveAspectRatio="xMidYMid slice"><defs>` +
  `<filter id="b" x="-50%" y="-50%" width="200%" height="200%"><feGaussianBlur stdDeviation="90"/></filter>` +
  `<radialGradient id="l" cx="0.12" cy="0.05" r="0.8"><stop offset="0" stop-color="#ffffff" stop-opacity="0.10"/><stop offset="1" stop-color="#ffffff" stop-opacity="0"/></radialGradient></defs>` +
  `<rect width="1600" height="1000" fill="#12141b"/>` +
  `<g filter="url(#b)">` +
  blob(320, 260, 260, '#7c4dff', 220, 120, 38) +
  blob(1250, 220, 230, '#FFDB58', -180, 160, 44) +
  blob(900, 820, 300, '#2e6bff', -240, -120, 50) +
  blob(260, 840, 220, '#d24dff', 200, -140, 41) +
  `</g><rect width="1600" height="1000" fill="url(#l)"/></svg>`

export function glass(on: any) {
  on('ui.render', { component: 'Backdrop' }, ($: any, e: any, next: any) => {
    if ((e.props as any).scene !== 'liquid' || (e.surface !== 'desktop' && e.surface !== 'mobile')) return next(e)
    const { Svg } = $.ui.resolve(e)
    return <Svg source={SCENE} alt="A slow, soft, coloured light behind the chat" isInteractive />
  })
}
