import { YELLOW, PURPLE, HEX, svgChip, palette } from './chip'

// A small settings panel for the look: /look opens it. A dropdown for the font,
// and for each colour the real item it changes drawn in that colour, a colour
// picker, a box for your own #rrggbb and a reset. Every change is written as the plugin's own setting.
const PLUGIN = 'muster-look'
const PANE = 'muster-look-settings'

export const FONTS = ['Anthropic Sans', 'System sans', 'Helvetica Neue', 'Avenir Next', 'Georgia', 'Menlo']

export const COLOURS: { key: string; label: string; dflt: string }[] = [
  { key: 'questionHeadingColor', label: 'Question heading chip', dflt: '#FFDB58' },
  { key: 'cardHeadingColor', label: 'Card heading chip', dflt: '#9b6dff' },
  { key: 'choiceChipColor', label: 'A, B and C chips', dflt: '#FFDB58' },
  { key: 'lineTopColor', label: 'Line, top', dflt: '#FFDB58' },
  { key: 'lineBottomColor', label: 'Line, bottom', dflt: '#7c4dff' },
]

const SAMPLE_FONT = 'Anthropic Sans,Styrene B,system-ui,-apple-system,Segoe UI,sans-serif'

// The real item a colour changes, drawn the way the chat draws it, in that colour.
function sampleOf(Svg: any, Box: any, key: string, hex: string, v: Record<string, string>) {
  const chip = (label: string, base: typeof YELLOW) => svgChip(Svg, label, palette(base, hex), SAMPLE_FONT, null)
  if (key === 'questionHeadingColor') return chip('WAITING \u00b7 item 7', YELLOW)
  if (key === 'cardHeadingColor') return chip('DONE \u00b7 item 7', PURPLE)
  if (key === 'choiceChipColor') {
    return (
      <Box flexDirection="row" gap={1}>
        {['A', 'B', 'C'].map(l => <Box key={l}>{chip(l, YELLOW)}</Box>)}
      </Box>
    )
  }
  const top = key === 'lineTopColor' ? hex : (HEX.test(v.lineTopColor || '') ? v.lineTopColor : YELLOW.text)
  const bottom = key === 'lineBottomColor' ? hex : (HEX.test(v.lineBottomColor || '') ? v.lineBottomColor : '#7c4dff')
  const end = key === 'lineTopColor' ? 'top' : 'bottom'
  const mark = end === 'top' ? 'y="2"' : 'y="58"'
  const source =
    `<svg xmlns="http://www.w3.org/2000/svg" width="40" height="64" viewBox="0 0 40 64"><defs><linearGradient id="f" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="${top}"/><stop offset="1" stop-color="${bottom}"/></linearGradient></defs>` +
    `<rect x="12" y="2" width="2" height="60" fill="url(#f)" shape-rendering="crispEdges"/>` +
    `<circle cx="13" cy="${end === 'top' ? 3 : 61}" r="3.5" fill="${hex}"/></svg>`
  void mark
  return <Svg alt={`The line, ${end} end`} width={40} height={64} source={source} />
}

let otherFont = false

async function open($: any) {
  await $.ui.open({ id: PANE, title: 'Muster look' })
}

async function set($: any, key: string, value: string) {
  try { await $.config.set({ key: `${PLUGIN}.${key}`, value }) } catch { /* a row the app refuses stays as it was */ }
}

async function current($: any) {
  const out: Record<string, string> = {}
  try {
    for (const r of await $.config.list()) {
      if (typeof r.key === 'string' && r.key.startsWith(PLUGIN + '.')) out[r.key.slice(PLUGIN.length + 1)] = String(r.value ?? '')
    }
  } catch { /* no list: show defaults */ }
  return out
}

export async function registerLook($: any): Promise<void> {
  try { await $.command.register({ name: 'look', description: 'Change the colours and font of the Muster look' }) } catch { /* no commands here */ }
}

export function panel(on: any) {
  on('command.run', { command: 'look' }, async ($: any) => {
    await open($)
    return { text: 'Muster look settings opened.' }
  })
  on('ui.message', async ($: any, e: any, next: any) => {
    const d = e.data as { id?: string; hex?: string } | undefined
    if (d !== undefined && typeof d.id === 'string' && typeof d.hex === 'string' && HEX.test(d.hex) && COLOURS.some(c => c.key === d.id)) {
      await set($, d.id, d.hex)
      $.ui.invalidate('ui.render')
      return {}
    }
    return next(e)
  })
  on('ui.render', { component: 'Pane', requestId: PANE }, async ($: any, e: any) => {
    const { Box, Text, Button, Input, Select, Client, Svg } = $.ui.resolve(e)
    const v = await current($)
    const fontNow = v.chipFont || 'Anthropic Sans'
    const showOther = otherFont || !FONTS.includes(fontNow)
    return (
      <Box flexDirection="column" gap={1}>
        <Text bold>Change your look</Text>
        <Select
          key="font"
          label="Chip font "
          options={[...FONTS, 'Other\u2026'].map(f => ({ value: f, label: f }))}
          value={showOther ? 'Other\u2026' : fontNow}
          onSelect={(val: string) => {
            if (val === 'Other\u2026') { otherFont = true; $.ui.invalidate('ui.render') } else { otherFont = false; void set($, 'chipFont', val) }
          }}
        />
        {showOther && (
          <Input
            key="font-other"
            label="Font name "
            placeholder="any font your computer has"
            value={FONTS.includes(v.chipFont || '') ? '' : v.chipFont}
            submitLabel="set"
            onSubmit={(t: string) => { const x = t.replace(/[^A-Za-z0-9 ,-]/g, '').trim(); if (x !== '') void set($, 'chipFont', x) }}
          />
        )}
        {COLOURS.map(c => {
          const hex = v[c.key] || c.dflt
          return (
            <Box key={c.key} flexDirection="column" gap={1}>
              <Box flexDirection="row" gap={1}>
                <Text bold>{c.label}</Text>
                <Text>{hex}</Text>
              </Box>
              <Box key={`${c.key}-sample`} flexDirection="row">{sampleOf(Svg, Box, c.key, hex, v)}</Box>
              {Client !== undefined && <Client key={`field-${c.key}`} module="./field.tsx" props={{ id: c.key, hex }} />}
              <Box flexDirection="row" gap={1}>
                <Input
                  key={`${c.key}-hex`}
                  label="Or type #rrggbb "
                  placeholder="#rrggbb"
                  value=""
                  submitLabel="set"
                  onSubmit={(t: string) => { const x = t.trim(); if (HEX.test(x)) void set($, c.key, x) }}
                />
                <Button key={`${c.key}-reset`} label="Reset" onPress={() => { void set($, c.key, c.dflt) }} />
              </Box>
            </Box>
          )
        })}
        <Button
          key="reset-all"
          label="Reset all to default"
          onPress={() => { otherFont = false; void set($, 'chipFont', 'Anthropic Sans'); COLOURS.forEach(c => { void set($, c.key, c.dflt) }) }}
        />
      </Box>
    )
  })
}
