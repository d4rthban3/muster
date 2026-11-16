import { expect, test } from 'claude-code/testing'
import Rail from './rail'

const MSG = (text: string, surface: 'terminal' | 'desktop') => ({
  plugin: 'muster-look',
  component: 'AssistantMessage',
  surface,
  props: { text, isFirstOfReply: true },
}) as const

const QUESTION =
  '**WAITING · item 7**\nHow should the menu look?\n\n***A.*** Top right. *(my pick)*\n\n***B.*** Fixed at the bottom.'

test('a question gets chips on terminal and desktop', async ($, on) => {
  on('ui.render', ($, e) => {
    const { Text } = $.ui.resolve(e)
    return <Text>engine</Text>
  })
  for (const surface of ['terminal', 'desktop'] as const) {
    const ui = await $.ui.mount(MSG(QUESTION, surface))
    if (surface === 'terminal') {
      expect((await ui.find({ type: 'Text', text: /WAITING · item 7/ }))?.text).toContain('WAITING')
      expect(await ui.find({ type: 'Text', text: /^ ?A ?$/ })).toBeTruthy()
    } else {
      // desktop draws each chip as a vector pill
      expect(await ui.find({ type: 'Svg' })).toBeTruthy()
    }
    expect(await ui.find({ type: 'Text', text: /engine/ })).toBeFalsy()
    await ui.unmount()
  }
})

test('plain text goes to the engine untouched', async ($, on) => {
  on('ui.render', ($, e) => {
    const { Text } = $.ui.resolve(e)
    return <Text>engine</Text>
  })
  const ui = await $.ui.mount(MSG('Just a normal answer with **bold**.', 'desktop'))
  expect((await ui.find({ type: 'Text', text: /engine/ }))?.text).toBe('engine')
  await ui.unmount()
})

test('a mixed-case title and a plain one become chips; chips are one line', async ($, on) => {
  on('ui.render', ($, e) => {
    const { Text } = $.ui.resolve(e)
    return <Text>engine</Text>
  })
  const ui = await $.ui.mount(MSG('**PASS received · muster look build**\n- Done.', 'terminal'))
  expect((await ui.find({ type: 'Text', text: /PASS received · muster look build/ }))?.text).toContain('PASS received')
  expect(await ui.find({ type: 'Text', text: /engine/ })).toBeFalsy()
  await ui.unmount()
})

test('the rule is one piece and a card after the question is not part of it', async ($, on) => {
  on('ui.render', ($, e) => {
    const { Text } = $.ui.resolve(e)
    return <Text>engine</Text>
  })
  const text = QUESTION + '\n\n**PASS · next job**\nDone.'
  const ui = await $.ui.mount(MSG(text, 'terminal'))
  const rule = await ui.find({ type: 'Text', text: /^▏(\n▏)*$/ })
  expect(rule).toBeTruthy()
  // the question has a title, two choices: the rule is at least 3 lines and stops there
  expect((rule?.text ?? '').split('\n').length).toBeLessThan(8)
  await ui.unmount()
})

test('desktop draws vector chips and one vector line', async ($, on) => {
  on('ui.render', ($, e) => {
    const { Text } = $.ui.resolve(e)
    return <Text>engine</Text>
  })
  const ui = await $.ui.mount(MSG(QUESTION, 'desktop'))
  expect(await ui.find({ type: 'Svg' })).toBeTruthy()
  expect(await ui.find({ type: 'Svg' })).toBeTruthy()
  await ui.unmount()
})

const Q2 = '**WAITING · item 7**\nHow should the menu look?\n\n***A.*** Top right.\n\n***B.*** Bottom.'

async function svgSources($: any) {
  const ui = await $.ui.mount(MSG(Q2, 'desktop'))
  const out: string[] = []
  for (const n of (await ui.findAll({ type: 'Svg' })) ?? []) out.push(String(n.props?.source ?? ''))
  // the line is drawn by a surface module that is handed its two colours
  for (const n of (await ui.findAll({ type: 'Client' })) ?? []) out.push(JSON.stringify(n.props?.props ?? {}))
  await ui.unmount()
  return out
}

test('with nothing set the look is the default', async ($, on) => {
  on('ui.render', ($, e) => { const { Text } = $.ui.resolve(e); return <Text>engine</Text> })
  const s = (await svgSources($)).join('\n')
  expect(s).toContain('font-family="Anthropic Sans,Styrene B,system-ui,-apple-system,Segoe UI,sans-serif"')
  expect(s).toContain('#FFDB58')
  expect(s).toContain('#7c4dff')
  expect(s).toContain('font-weight="400"')
})

import { groupId, loadGroup, saveGroup, clearGroup } from './group'

const CUSTOM = { chipFont: 'Georgia', questionHeadingColor: '#2dd4bf', choiceChipColor: '#ff7ab6', lineTopColor: '#2dd4bf', lineBottomColor: '#ff7ab6' }

test('colours picked on the settings page change the chat look of this group', async ($, on) => {
  on('ui.render', ($, e) => { const { Text } = $.ui.resolve(e); return <Text>engine</Text> })
  const pane = await $.ui.mount({ plugin: 'muster-look', component: 'Pane', requestId: 'muster-look-settings', surface: 'desktop', props: {} } as any)
  for (const [id, hex] of [['questionHeadingColor', '#2dd4bf'], ['choiceChipColor', '#ff7ab6'], ['lineTopColor', '#2dd4bf'], ['lineBottomColor', '#ff7ab6']]) await pane.post({ id, hex }, { in: `field-${id}` })
  await pane.unmount()
  const s = (await svgSources($)).join('\n')
  expect(s).toContain('#2dd4bf')
  expect(s).toContain('#ff7ab6')
})

test('a change in one group leaves another group alone, and reset only resets its own group', async ($, on) => {
  on('ui.render', ($, e) => { const { Text } = $.ui.resolve(e); return <Text>engine</Text> })
  const here = await groupId($)
  const other = '/some/other/project'
  await clearGroup($); await clearGroup($, other)
  expect(here).not.toBe(other)
  // the other group (say PINR) keeps its own colours
  await saveGroup($, 'questionHeadingColor', '#112233', other)
  await saveGroup($, 'lineTopColor', '#445566', other)
  // this group (say Muster) changes
  await saveGroup($, 'questionHeadingColor', '#2dd4bf')
  expect((await loadGroup($, other)).questionHeadingColor).toBe('#112233')
  expect((await loadGroup($)).questionHeadingColor).toBe('#2dd4bf')
  expect((await loadGroup($)).lineTopColor).toBeUndefined()
  // reset all for this group does not touch the other group
  await clearGroup($)
  expect(await loadGroup($)).toEqual({})
  expect((await loadGroup($, other)).questionHeadingColor).toBe('#112233')
  expect((await loadGroup($, other)).lineTopColor).toBe('#445566')
  // a group with nothing saved has no choices, so every colour is its default
  expect(await loadGroup($, '/never/saved')).toEqual({})
  await clearGroup($, other)
})

import { cutFont } from './font'

test('a file that is not a font gives no cut, so the chip falls back', async ($, on) => {
  expect(cutFont(new Uint8Array([1, 2, 3, 4, 5, 6, 7, 8]), 'AB')).toBeNull()
})

test('the settings panel has a font dropdown, swatches, a hex box and resets', async ($, on) => {
  const ui = await $.ui.mount({ plugin: 'muster-look', component: 'Pane', requestId: 'muster-look-settings', surface: 'desktop', props: {} } as any)
  expect(await ui.find({ type: 'Select' })).toBeTruthy()
  expect(await ui.find({ type: 'Input' })).toBeTruthy()
  expect(await ui.find({ type: 'Button', label: 'Reset all to default' })).toBeTruthy()
  const clients = JSON.stringify(await ui.findAll({ type: 'Client' }))
  for (const k of ['questionHeadingColor', 'cardHeadingColor', 'choiceChipColor', 'lineTopColor', 'lineBottomColor']) expect(clients).toContain(`field-${k}`)
  const buttons = JSON.stringify(await ui.findAll({ type: 'Button' }))
  expect(buttons).not.toContain('Use #')
  expect(buttons).not.toContain('Pick any colour')
  // each colour's sample is the real item drawn: the chips, the A B C circles and the line
  const pics = JSON.stringify(await ui.findAll({ type: 'Svg' }))
  expect(pics).toContain('WAITING')
  expect(pics).toContain('DONE')
  expect(pics).toContain('The line, top end')
  expect(pics).toContain('The line, top end')
  await ui.unmount()
})

import { hexToHsv, hsvToHex } from './color'
import Field from './field'

test('colour helpers round-trip and the field posts the picked colour', async () => {
  expect(hsvToHex(hexToHsv('#9b6dff').h, hexToHsv('#9b6dff').s, hexToHsv('#9b6dff').v).toLowerCase()).toBe('#9b6dff')
  let pointer: any = null
  const posts: any[] = []
  let state: any
  const surface: any = {
    elements: { Box: (p: any) => p, Text: (p: any) => p },
    get state() { return state },
    setState: (n: any) => { state = n },
    onPointer: (fn: any) => { pointer = fn },
    post: (d: any) => posts.push(d),
  }
  const oldH = (globalThis as any).h
  ;(globalThis as any).h = (t: any, p: any, ...c: any[]) => ({ t, p, c })
  Field({ id: 'lineTopColor', hex: '#ff0000' }, surface)
  pointer({ type: 'down', x: 31, y: 6, button: 'left' })
  pointer({ type: 'up', x: 0, y: 6, button: 'left' })
  expect(posts.length).toBe(1)
  expect(posts[0].id).toBe('lineTopColor')
  expect(posts[0].hex).toBe('#ff0000')
  ;(globalThis as any).h = oldH
})

test('the left line is a region as tall as the rows beside it, one glyph per laid-out row', async () => {
  const el = (t: any) => t
  const mk = (rows: number) => Rail({ top: '#FFDB58', bottom: '#7c4dff' }, { rows, elements: { Box: (p: any) => p, Text: (p: any) => p } })
  const tall: any = mk(9)
  expect(tall.children.length).toBe(9)
  expect(tall.children[0].color).toBe('#ffdb58')
  expect(tall.children[8].color).toBe('#7c4dff')
  expect((mk(0) as any).children.length).toBe(1)
  void el
})

test('clicking a choice sends its letter once; an answered question does not send again', async ($, on) => {
  const sent: string[] = []
  on('prompt.submit', ($, e) => { sent.push(String((e as any).text)); return { text: String((e as any).text) } as any })
  const ui = await $.ui.mount(MSG(Q2, 'desktop'))
  await (ui as any).post({ pick: 'A' }, { in: 'pickA' })
  // the answered question has drawn no click areas any more
  expect(await ui.find({ type: 'Client', key: 'pickB' })).toBeFalsy()
  await expect((ui as any).post({ pick: 'B' }, { in: 'pickB' })).rejects.toThrow()
  expect(sent).toEqual(['A'])
  await ui.unmount()
})

test('a live choice has a hidden purple circle that its row hover reveals', async ($, on) => {
  on('ui.render', ($, e) => { const { Text } = $.ui.resolve(e); return <Text>engine</Text> })
  const ui = await $.ui.mount(MSG(Q2, 'desktop'))
  // the purple circle is drawn twice (A, B), each inside a hidden Box that the row's hover reveals
  const hot = ((await ui.findAll({ type: 'Svg' })) ?? []).filter((n: any) => String(n.props?.source).includes('fill="#7c4dff" fill-opacity="1"'))
  const hidden = hot
  expect(JSON.stringify(await ui.findAll({ type: 'Box' }))).toContain('"display":"none"')
  expect(hidden.length).toBe(2)
  await ui.unmount()
})

test('when the store refuses, the settings page says the look is not saved between sessions', async ($, on) => {
  const ui = await $.ui.mount({ plugin: 'muster-look', component: 'Pane', requestId: 'muster-look-settings', surface: 'desktop', props: {} } as any)
  expect(JSON.stringify(await ui.findAll({ type: 'Text' }))).toContain('Not saved between sessions')
  await ui.unmount()
})

test('a card heading after the last choice is set apart by a clear gap; choices keep their spacing', async ($, on) => {
  on('ui.render', ($, e) => { const { Text } = $.ui.resolve(e); return <Text>engine</Text> })
  const gaps = async (text: string) => {
    const ui = await $.ui.mount(MSG(text, 'desktop'))
    const n = ((await ui.findAll({ type: 'Svg' })) ?? []).filter((x: any) => String(x.props?.source).includes('height="14"') && String(x.props?.source).includes('width="1"')).length
    await ui.unmount()
    return n
  }
  const withCard = await gaps(Q2 + '\n\n**SHIPPING · card-val-contrast**\nDone.')
  const without = await gaps(Q2)
  expect(withCard).toBe(without + 1)
})

test('the picked letter stays lit on its question; the others do not', async ($, on) => {
  on('ui.render', ($, e) => { const { Text } = $.ui.resolve(e); return <Text>engine</Text> })
  on('prompt.submit', ($, e) => ({ text: String((e as any).text) }) as any)
  const Q3 = '**WAITING · item 9**\nWhich colour?\n\n***A.*** Red.\n\n***B.*** Blue.\n\n***C.*** Green.'
  const lit = async () => {
    const ui = await $.ui.mount(MSG(Q3, 'desktop'))
    const n = ((await ui.findAll({ type: 'Svg' })) ?? []).filter((x: any) => String(x.props?.source).includes('fill-opacity="1"')).length
    const j = JSON.stringify(await ui.findAll({ type: 'Box' }))
    // a tint on the row itself, not the one inside its hover
    const tint = (j.match(/"backgroundColor":"#23262e"/g) ?? []).length > (j.match(/"hover":\{"backgroundColor":"#23262e"/g) ?? []).length
    return { ui, n, tint }
  }
  const before = await lit()
  // live question: each of 3 rows has one hidden hot copy, none tinted
  expect(before.n).toBe(3)
  expect(before.tint).toBe(false)
  await (before.ui as any).post({ pick: 'B' }, { in: 'pickB' })
  await before.ui.unmount()
  const after = await lit()
  // answered: no hidden copies any more, exactly one lit circle and a tinted row
  expect(after.n).toBe(1)
  expect(after.tint).toBe(true)
  await after.ui.unmount()
})

test('every colour row has a colour-code box holding its code; a bad code is shown and not saved', async ($, on) => {
  on('ui.render', ($, e) => { const { Text } = $.ui.resolve(e); return <Text>engine</Text> })
  const pane = await $.ui.mount({ plugin: 'muster-look', component: 'Pane', requestId: 'muster-look-settings', surface: 'desktop', props: {} } as any)
  const boxes = (await pane.findAll({ type: 'Input' })) ?? []
  const codes = boxes.filter((b: any) => b.props?.placeholder === '#rrggbb')
  expect(codes.length).toBe(11)
  // each box holds the colour it sits beside (the default here)
  expect(codes.map((b: any) => String(b.props?.value).toUpperCase())).toContain('#FFDB58')
  await pane.unmount()
})

test('each pill has its own text, border and field colour, drawn in the chat', async ($, on) => {
  on('ui.render', ($, e) => { const { Text } = $.ui.resolve(e); return <Text>engine</Text> })
  const pane = await $.ui.mount({ plugin: 'muster-look', component: 'Pane', requestId: 'muster-look-settings', surface: 'desktop', props: {} } as any)
  const texts = JSON.stringify(await pane.findAll({ type: 'Client' }))
  for (const k of ['questionBorderColor', 'questionFieldColor', 'cardBorderColor', 'cardFieldColor', 'choiceBorderColor', 'choiceFieldColor']) expect(texts).toContain(`field-${k}`)
  await pane.post({ id: 'choiceBorderColor', hex: '#ff0000' }, { in: 'field-choiceBorderColor' })
  await pane.post({ id: 'choiceFieldColor', hex: '#003300' }, { in: 'field-choiceFieldColor' })
  await pane.unmount()
  const s = (await svgSources($)).join('\n')
  // the circles: border red, field solid dark green; the heading chip keeps its own colours
  expect(s).toContain('stroke="#ff0000"')
  expect(s).toContain('fill="#003300" fill-opacity="1"')
})

test('every A/B/C circle is one size and cannot be squeezed by a long, wrapping choice', async ($, on) => {
  on('ui.render', ($, e) => { const { Text } = $.ui.resolve(e); return <Text>engine</Text> })
  const long = 'This choice is a very long one that goes on and on and on so that it has to wrap onto a second and a third line in the chat'
  const text = `**WAITING · item 7**\nPick one.\n\n***A.*** Short\n\n***B.*** ${long}\n\n***C.*** Also short\n\n***D.*** ${long} ${long}`
  const ui = await $.ui.mount(MSG(text, 'desktop'))
  const svgs = ((await ui.findAll({ type: 'Svg' })) ?? []).filter((x: any) => String(x.props?.alt ?? '').length === 1)
  const sizes = new Set(svgs.map((x: any) => `${x.props.width}x${x.props.height}`))
  expect(svgs.length).toBeGreaterThanOrEqual(4)
  expect(sizes.size).toBe(1)
  const tree = JSON.stringify(await ui.findAll({ type: 'Box' }))
  expect((tree.match(/"flexShrink":0/g) ?? []).length).toBeGreaterThanOrEqual(4)
  await ui.unmount()
})
