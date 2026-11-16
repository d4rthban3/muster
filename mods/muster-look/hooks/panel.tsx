// A small settings panel for the look: /look opens it. A dropdown for the font,
// and for each of the six colours a row of swatches, a box for your own #rrggbb
// and a reset. Every change is written as the plugin's own setting.
const PLUGIN = 'muster-look'
const PANE = 'muster-look-settings'
const HEX = /^#[0-9a-fA-F]{6}$/

export const FONTS = ['Anthropic Sans', 'System sans', 'Helvetica Neue', 'Avenir Next', 'Georgia', 'Menlo']

const SWATCHES = ['#FFDB58', '#ff9f43', '#ff7ab6', '#9b6dff', '#7c4dff', '#5aa9ff', '#2dd4bf', '#7ddc8a', '#e8e6e1']

export const COLOURS: { key: string; label: string; dflt: string }[] = [
  { key: 'questionHeadingColor', label: 'Question heading chip', dflt: '#FFDB58' },
  { key: 'cardHeadingColor', label: 'Card heading chip', dflt: '#9b6dff' },
  { key: 'choiceChipColor', label: 'A, B and C chips', dflt: '#FFDB58' },
  { key: 'lineTopColor', label: 'Line, top', dflt: '#FFDB58' },
  { key: 'lineBottomColor', label: 'Line, bottom', dflt: '#7c4dff' },
]

let otherFont = false
let openKey = COLOURS[0].key

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
    const { Box, Text, Button, Input, Select, Client } = $.ui.resolve(e)
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
          const isOpen = openKey === c.key
          return (
            <Box key={c.key} flexDirection="column">
              <Box flexDirection="row" gap={1}>
                <Text>{c.label}</Text>
                <Text color={hex} backgroundColor="#191c24">{` Sample ${hex} `}</Text>
              </Box>
              <Box flexDirection="row" gap={1}>
                {SWATCHES.map(sw => (
                  <Button key={`${c.key}-${sw}`} label={`Use ${sw}`} onPress={() => { void set($, c.key, sw) }}>
                    <Text color={sw} backgroundColor={sw}>{'    '}</Text>
                  </Button>
                ))}
                <Button key={`${c.key}-reset`} label="Reset" onPress={() => { void set($, c.key, c.dflt) }} />
              </Box>
              {isOpen && Client !== undefined ? (
                <Client key={`field-${c.key}`} module="./field.tsx" props={{ id: c.key, hex }} />
              ) : (
                <Button key={`${c.key}-open`} label={`Pick any colour for ${c.label}`} onPress={() => { openKey = c.key; $.ui.invalidate('ui.render') }} />
              )}
              <Input
                key={`${c.key}-hex`}
                label="Or type #rrggbb "
                placeholder="#rrggbb"
                value=""
                submitLabel="set"
                onSubmit={(t: string) => { const x = t.trim(); if (HEX.test(x)) void set($, c.key, x) }}
              />
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
