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
  on('ui.render', { component: 'Pane', requestId: PANE }, async ($: any, e: any) => {
    const { Box, Text, Button, Input, Select } = $.ui.resolve(e)
    const v = await current($)
    return (
      <Box flexDirection="column" gap={1}>
        <Text bold>Change your look</Text>
        <Select
          key="font"
          label="Chip font "
          options={FONTS.map(f => ({ value: f, label: f }))}
          value={v.chipFont || 'Anthropic Sans'}
          onSelect={(val: string) => { void set($, 'chipFont', val) }}
        />
        {COLOURS.map(c => (
          <Box key={c.key} flexDirection="column">
            <Text>{c.label} <Text dimColor>{v[c.key] || c.dflt}</Text></Text>
            <Box flexDirection="row" gap={1}>
              {SWATCHES.map(s => (
                <Button key={`${c.key}-${s}`} label={s} onPress={() => { void set($, c.key, s) }}>
                  <Text color={s}>{'●●'}</Text>
                </Button>
              ))}
              <Button key={`${c.key}-reset`} label="Reset" onPress={() => { void set($, c.key, c.dflt) }} />
            </Box>
            <Input
              key={`${c.key}-hex`}
              label="Your own "
              placeholder="#rrggbb"
              value=""
              submitLabel="set"
              onSubmit={(t: string) => { const x = t.trim(); if (HEX.test(x)) void set($, c.key, x) }}
            />
          </Box>
        ))}
        <Button
          key="reset-all"
          label="Reset all to default"
          onPress={() => { void set($, 'chipFont', 'Anthropic Sans'); COLOURS.forEach(c => { void set($, c.key, c.dflt) }) }}
        />
      </Box>
    )
  })
}
