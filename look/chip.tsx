import type { Cut } from './font'
import { labelWidth } from './metrics'

// Muster's colours, taken from the owner's reference chips: a low tint of the
// chip's own hue, a thin brighter border in it, text in it. Dark first.
export const YELLOW = { text: '#FFDB58', fill: '#3a3419', edge: '#8a7a30', glow: '#ffe066', lift: '#5c4f17' }
export const PURPLE = { label: '#a995ff', text: '#9b6dff', fill: '#2b2748', edge: '#5b3fd0', glow: '#8f5bff', lift: '#463d7c' }

// A bordered Box is always three rows tall in the apps, so on desktop the chip
// is drawn as a small vector pill: thin brighter border, lifted fill, a soft
// glow, 28px tall. The label is spaced to its measured width, never stretched.
const esc = (t: string) => t.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
// The purple a choice's circle fills with while the pointer is over its row; the letter turns white on it.
export const HOT = '#7c4dff'
export const HOT_EDGE = '#a98bff'
export function svgChip(Svg: any, label: string, c: { text: string; label?: string; glow: string; lift: string; field?: string }, font: string, cut: Cut | null, minTw = 0, pad = 0, hot = false) {
  // The pill is as wide as the same words in body text (measured widths of the
  // app's regular-weight text). The letters keep their own shape: the label is
  // only ever spaced to that width, never stretched.
  const measured = labelWidth(label, 14)
  const tw = Math.max(minTw, Math.ceil(measured ?? label.length * 6.6))
  let face = ''
  let family = font
  if (cut !== null && Array.from(label).every(ch => cut.advance[ch] !== undefined)) {
    face = `<style>@font-face{font-family:"MusterAS";src:url(${cut.dataUri})}</style>`
    family = `MusterAS,${font}`
  }
  // The cut is the font's lightest setting; a hair of outline brings it to the
  // regular weight the chat's body text has.
  const stretch = ` textLength="${tw}" lengthAdjust="spacing"` + (face === '' ? '' : ` stroke="${c.label ?? c.text}" stroke-width="0.3" stroke-linejoin="round"`)
  const w = tw + 24
  // a single letter (a choice chip) is centred in its pill both ways; longer labels keep their left start
  const single = Array.from(label).length === 1
  // the pill itself is always 28 tall; pad is clear air above and below it, inside the picture
  const pill = 28
  const ht = pill + pad * 2
  // a one-letter chip is a perfect circle (as wide as the pill is tall) in the middle of its picture
  const bw = single ? pill - 4.5 : w - 4.5
  const bx = single ? (w - bw) / 2 : 2.25
  const source =
    `<svg xmlns="http://www.w3.org/2000/svg" width="${w}" height="${ht}" viewBox="0 0 ${w} ${ht}" preserveAspectRatio="xMinYMid meet">` +
    face +
    `<g transform="translate(0 ${pad})">` +
    `<defs><filter id="g" x="-20%" y="-40%" width="140%" height="180%"><feGaussianBlur stdDeviation="1.2"/></filter><linearGradient id="sh" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#ffffff" stop-opacity="0.16"/><stop offset="0.5" stop-color="#ffffff" stop-opacity="0.02"/><stop offset="1" stop-color="#000000" stop-opacity="0.28"/></linearGradient><linearGradient id="rm" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#ffffff" stop-opacity="0.75"/><stop offset="0.45" stop-color="#ffffff" stop-opacity="0.08"/><stop offset="1" stop-color="#ffffff" stop-opacity="0.2"/></linearGradient></defs>` +
    `<rect x="${bx}" y="2.25" width="${bw}" height="${pill - 4.5}" rx="${(pill - 4.5) / 2}" fill="none" stroke="${hot ? HOT_EDGE : c.glow}" stroke-opacity="0.4" stroke-width="1" filter="url(#g)"/>` +
    `<rect x="${bx}" y="2.25" width="${bw}" height="${pill - 4.5}" rx="${(pill - 4.5) / 2}" fill="${hot ? HOT : (c.field ?? c.text)}" fill-opacity="${hot || c.field !== undefined ? 1 : 0.08}" stroke="${hot ? HOT_EDGE : c.glow}" stroke-width="${hot ? 1 : 0.5}"/>` +
    // liquid glass, as pinr.io draws it: a bright rim at the top left that fades away
    // to a dim one at the bottom right, a soft sheen in the top half and a shade low down
    `<rect x="${bx}" y="2.25" width="${bw}" height="${pill - 4.5}" rx="${(pill - 4.5) / 2}" fill="url(#sh)"/>` +
    `<rect x="${bx + 0.5}" y="2.75" width="${bw - 1}" height="${pill - 5.5}" rx="${(pill - 5.5) / 2}" fill="none" stroke="url(#rm)" stroke-width="1"/>` +
    (single
      ? `<text x="${w / 2}" y="${pill / 2}" text-anchor="middle" dominant-baseline="central" font-family="${family}" font-size="14" font-weight="400" font-style="normal" fill="${hot ? '#ffffff' : (c.label ?? c.text)}"${face === '' ? '' : ` stroke="${c.label ?? c.text}" stroke-width="0.3" stroke-linejoin="round"`}>${esc(label)}</text>`
      : `<text x="12" y="19" font-family="${family}" font-size="14" font-weight="400" font-style="normal" fill="${hot ? '#ffffff' : (c.label ?? c.text)}"${stretch}>${esc(label)}</text>`) +
    `</g></svg>`
  return <Svg alt={label} width={w} height={ht} source={source} />
}

export const BACKDROP = [0x19, 0x1c, 0x24]
export const HEX = /^#[0-9a-fA-F]{6}$/

// A user's colour for a chip: the default palette exactly when it is the
// default colour, else a fill, lift and borders mixed from it and the dark page.
export function palette(base: typeof YELLOW, want: unknown): typeof YELLOW {
  if (typeof want !== 'string' || !HEX.test(want) || want.toLowerCase() === base.text.toLowerCase()) return base
  const rgb = [1, 3, 5].map(i => parseInt(want.slice(i, i + 2), 16))
  const mix = (k: number) =>
    '#' + rgb.map((v, i) => Math.round(BACKDROP[i]! * (1 - k) + v * k).toString(16).padStart(2, '0')).join('')
  return { text: want, fill: mix(0.2), lift: mix(0.42), edge: mix(0.55), glow: mix(0.95) }
}
export const colourOr = (want: unknown, dflt: string) => (typeof want === 'string' && HEX.test(want) ? want : dflt)

// A colour mixed over the dark page, k of the way from the page to the colour.
export function mixHex(hex: string, k: number): string {
  const rgb = [1, 3, 5].map(i => parseInt(hex.slice(i, i + 2), 16))
  return '#' + rgb.map((v, i) => Math.round(BACKDROP[i]! * (1 - k) + v * k).toString(16).padStart(2, '0')).join('')
}

// Each pill has three colours the owner can set apart: its text, its border and its field.
// Text is the pill's own colour (the border and field follow it until they are set).
export const PILLS = {
  question: { base: YELLOW, text: 'questionHeadingColor', border: 'questionBorderColor', field: 'questionFieldColor' },
  card: { base: PURPLE, text: 'cardHeadingColor', border: 'cardBorderColor', field: 'cardFieldColor' },
  choice: { base: YELLOW, text: 'choiceChipColor', border: 'choiceBorderColor', field: 'choiceFieldColor' },
} as const
export type PillName = keyof typeof PILLS

export function pillOf(name: PillName, v: Record<string, string | undefined>) {
  const d = PILLS[name]
  const c = palette(d.base, v[d.text]) as typeof YELLOW & { field?: string }
  const border = colourOr(v[d.border], '')
  const field = colourOr(v[d.field], '')
  return { ...c, glow: border !== '' ? border : c.glow, field: field !== '' ? field : undefined }
}

// The code each part shows in the settings: what is set, else what is drawn now.
export function pillPart(name: PillName, part: 'text' | 'border' | 'field', v: Record<string, string | undefined>): string {
  const d = PILLS[name]
  const c = pillOf(name, v)
  if (part === 'text') return colourOr(v[d.text], d.base.text)
  if (part === 'border') return c.glow
  return c.field ?? mixHex(c.text, 0.08)
}
