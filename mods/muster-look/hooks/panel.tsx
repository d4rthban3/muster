import { YELLOW, HEX, svgChip, pillOf, pillPart, PILLS, type PillName } from './chip'
import { groupId, groupName, loadGroup, saveGroup, clearGroup, storeWorks } from './group'

// A small settings panel for the look: /look opens it. A dropdown for the font,
// and for each colour the real item it changes drawn in that colour, a colour
// picker, a box for your own #rrggbb and a reset. Every change is written as the plugin's own setting.
const PLUGIN = 'muster-look'
const PANE = 'muster-look-settings'

export const FONTS = ['Anthropic Sans', 'System sans', 'Helvetica Neue', 'Avenir Next', 'Georgia', 'Menlo']

const PILL_NAMES: { name: PillName; title: string }[] = [
  { name: 'question', title: 'Question heading chip' },
  { name: 'card', title: 'Card heading chip' },
  { name: 'choice', title: 'A, B and C chips' },
]
const PARTS = ['text', 'border', 'field'] as const

export const COLOURS: { key: string; label: string; short: string; group: string; dflt: string; pill?: PillName; part?: (typeof PARTS)[number] }[] = [
  ...PILL_NAMES.flatMap(p => PARTS.map(part => ({
    key: PILLS[p.name][part], label: `${p.title}: ${part}`, short: part[0].toUpperCase() + part.slice(1), group: p.name, dflt: pillPart(p.name, part, {}), pill: p.name, part,
  }))),
  { key: 'lineTopColor', label: 'Line, top', short: 'Top', group: 'line', dflt: '#FFDB58' },
  { key: 'lineBottomColor', label: 'Line, bottom', short: 'Bottom', group: 'line', dflt: '#7c4dff' },
]

// quiet colours, the same as the Muster site and pinr.io: hairline borders, muted words, one yellow dot
const LINE = '#3a3f4b'
const MUTED = '#b4b9c6'
const GROUPS = [...PILL_NAMES.map(p => ({ id: p.name as string, title: p.title })), { id: 'line', title: 'The line beside the chat' }]

// the whole item as it looks with the saved colours
function previewOf(Svg: any, Box: any, g: { id: string }, v: Record<string, string>) {
  if (g.id === 'line') return sampleOf(Svg, Box, COLOURS.filter(c => c.group === 'line')[0], v.lineTopColor || '#FFDB58', v)
  const c = COLOURS.filter(x => x.group === g.id)[0]
  return sampleOf(Svg, Box, c, v[c.key] || c.dflt, v)
}

const SAMPLE_FONT = 'Anthropic Sans,Styrene B,system-ui,-apple-system,Segoe UI,sans-serif'

// The real item a colour changes, drawn the way the chat draws it, in that colour.
function sampleOf(Svg: any, Box: any, c: (typeof COLOURS)[number], hex: string, v: Record<string, string>) {
  const key = c.key
  if (c.pill !== undefined) {
    // the real pill, drawn with this colour in place of the saved one
    const w = { ...v, [key]: hex }
    const one = (label: string) => svgChip(Svg, label, pillOf(c.pill as PillName, w), SAMPLE_FONT, null)
    if (c.pill === 'choice') {
      return (
        <Box flexDirection="row" gap={1}>
          {['A', 'B', 'C'].map(l => <Box key={l}>{one(l)}</Box>)}
        </Box>
      )
    }
    return one(c.pill === 'question' ? 'WAITING \u00b7 item 7' : 'DONE \u00b7 item 7')
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
// a colour code that was typed but is not #rrggbb, shown beside its box and never saved
const badCode: Record<string, string> = {}

async function open($: any) {
  await $.ui.open({ id: PANE, title: 'Muster look' })
}

// Every change is kept for this chat's group alone.
async function set($: any, key: string, value: string) {
  delete badCode[key]
  await saveGroup($, key, value)
  $.ui.invalidate('ui.render')
}

const current = ($: any) => loadGroup($)

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
      return {}
    }
    return next(e)
  })
  on('ui.render', { component: 'Pane', requestId: PANE }, async ($: any, e: any) => {
    const { Box, Text, Button, Input, Select, Client, Svg } = $.ui.resolve(e)
    const v = await current($)
    const gid = await groupId($)
    const kept = await storeWorks($)
    const fontNow = v.chipFont || 'Anthropic Sans'
    const showOther = otherFont || !FONTS.includes(fontNow)
    return (
      <Box flexDirection="column" gap={1}>
        <Box flexDirection="column">
          <Text bold>Change your look</Text>
          <Text color={MUTED}>{`For the group \u201c${groupName(gid)}\u201d only (${gid}). Other groups keep their own.`}</Text>
        </Box>
        {!kept && <Text color="#ff6b6b">{'Not saved between sessions: this host would not keep the look, so your colours and font last only until Claude Code closes.'}</Text>}
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
        {GROUPS.map(g => (
          <Box key={g.id} flexDirection="column" borderStyle="round" borderColor={LINE} paddingX={2} paddingY={0}>
            <Box flexDirection="row" justifyContent="space-between" alignItems="center">
              <Box flexDirection="row" gap={1}>
                <Text color={YELLOW.text}>{'\u25CF'}</Text>
                <Text bold>{g.title}</Text>
              </Box>
              <Box flexDirection="row" gap={1}>{previewOf(Svg, Box, g, v)}</Box>
            </Box>
            {COLOURS.filter(c => c.group === g.id).map(c => {
              const hex = v[c.key] || (c.pill !== undefined && c.part !== undefined ? pillPart(c.pill, c.part, v) : c.dflt)
              return (
                <Box key={c.key} flexDirection="row" gap={2} alignItems="center" marginTop={1}>
                  <Box key={`${c.key}-name`} width={12} flexShrink={0}><Text color={MUTED}>{c.short}</Text></Box>
                  <Box key={`${c.key}-right`} flexDirection="column" width={26} flexShrink={0}>
                    <Input
                      key={`${c.key}-hex-${hex}`}
                      placeholder="#rrggbb"
                      value={hex}
                      submitLabel="set"
                      onSubmit={(t: string) => {
                        const x = t.trim()
                        if (HEX.test(x)) { delete badCode[c.key]; void set($, c.key, x) }
                        else { badCode[c.key] = x; $.ui.invalidate('ui.render') }
                      }}
                    />
                    {badCode[c.key] !== undefined && <Text color="#ff6b6b">{`"${badCode[c.key]}" is not a colour code. Use #rrggbb. Not saved.`}</Text>}
                    <Button key={`${c.key}-reset`} label="Reset" onPress={() => { delete badCode[c.key]; void saveGroup($, c.key, null, gid).then(() => $.ui.invalidate('ui.render')) }} />
                  </Box>
                  {Client !== undefined && <Client key={`field-${c.key}`} module="./field.tsx" props={{ id: c.key, hex }} />}
                </Box>
              )
            })}
          </Box>
        ))}
        <Button
          key="reset-all"
          label="Reset all to default (this group)"
          onPress={() => { otherFont = false; void clearGroup($, gid).then(() => $.ui.invalidate('ui.render')) }}
        />
      </Box>
    )
  })
}
