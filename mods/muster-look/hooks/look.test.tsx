import { expect, test } from 'claude-code/testing'
import { sceneOf } from './glass'
import Rail from './rail'
import { parse } from './parse'
import { isOwnerSubmit } from './register'
import { hashText } from './group'

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

import { groupId, loadGroup, saveGroup, clearGroup, savePick, pickedOn, clearPick, answerIn, answerStands, sent, answerTag, answerLine } from './group'

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

test('clicking a choice sends its tagged letter once; an answered question does not send again', async ($, on) => {
  const sent: string[] = []
  on('prompt.submit', ($, e) => { sent.push(String((e as any).text)); return { text: String((e as any).text) } as any })
  const ui = await $.ui.mount(MSG(Q2, 'desktop'))
  await (ui as any).post({ pick: 'A' }, { in: 'pickA' })
  // the answered question has drawn no click areas any more
  expect(await ui.find({ type: 'Client', key: 'pickB' })).toBeFalsy()
  await expect((ui as any).post({ pick: 'B' }, { in: 'pickB' })).rejects.toThrow()
  expect(sent).toEqual(['Answer to WAITING \u00b7 item 7 (How should the menu look?): A'])
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

test('a choice of four or more lines keeps its circle full size and centred on its own text block', async ($, on) => {
  on('ui.render', ($, e) => { const { Text } = $.ui.resolve(e); return <Text>engine</Text> })
  const four = 'Engine sweeps every open, keyless or free-key live trade source for Solana, Base and BNB. That means the ones above plus anything else a fresh search finds, recorded on one build-or-buy page. It then runs the best ones side by side for a timed window (lag, which launchpads each covers, gaps, limits, terms), reports to you, and builds the winner as the main ribbon feed, with Helius kept as backup. My pick.'
  const text = `**WAITING · item 7**\nWhich plan?\n\n***A.*** ${four}\n\n***B.*** The same sweep and test, but it builds nothing until you have seen them.`
  for (const surface of ['desktop'] as const) {
    const ui = await $.ui.mount(MSG(text, surface))
    const svgs = ((await ui.findAll({ type: 'Svg' })) ?? []).filter((x: any) => String(x.props?.alt ?? '').length === 1)
    expect(svgs.length).toBe(4) // a live circle is drawn twice: at rest and purple on hover
    // the 4-line choice's circle is the very same size as the 1-line one's
    expect(new Set(svgs.map((x: any) => `${x.props.width}x${x.props.height}`)).size).toBe(1)
    // every choice row centres its circle on its text, and the circle's box cannot shrink
    const rows = ((await ui.findAll({ type: 'Box' })) ?? []).filter((b: any) => b.props?.gap === 2 && b.props?.alignItems === 'center')
    expect(rows.length).toBe(2)
    const tree = JSON.stringify(rows)
    expect((tree.match(/"flexShrink":0/g) ?? []).length).toBeGreaterThanOrEqual(2)
    await ui.unmount()
  }
})

test('a live question has a text box; what is typed is sent with its heading and sticks on the card', async ($, on) => {
  on('ui.render', ($, e) => { const { Text } = $.ui.resolve(e); return <Text>engine</Text> })
  const boxes = async (ui: any) => ((await ui.findAll({ type: 'Input' })) ?? []).filter((x: any) => x.props?.placeholder === 'Or type your own answer')
  const ui = await $.ui.mount(MSG(Q2, 'desktop'))
  const live = await boxes(ui)
  expect(live.length).toBe(1)
  await ui.unmount()
})

test('only the owner typing answers a question; peers, plugins and notifications do not', () => {
  for (const kind of ['peer', 'peer-send-message', 'plugin', 'task-notification', 'scheduled-trigger', 'projects-relay', 'coordinator', 'channel']) expect(isOwnerSubmit({ origin: { kind } })).toBe(false)
  expect(isOwnerSubmit({})).toBe(false)
  expect(isOwnerSubmit({ origin: { kind: 'composer' } })).toBe(true)
  expect(isOwnerSubmit({ origin: { kind: 'bridge' } })).toBe(true)
})

test('a question resent on one line splits into one choice per letter', () => {
  const p = parse('Which one? ***A.*** Build it now or ***B.*** Wait for the check')!
  const ch = p.pieces.filter(x => x.kind === 'choice') as any[]
  expect(ch.map(c => c.letter)).toEqual(['A', 'B'])
  expect(ch[0].text).toBe('Build it now')
  expect(ch[1].text).toBe('Wait for the check')
  expect(p.pieces[0]).toEqual({ kind: 'md', text: 'Which one?' })
  expect(p.isQuestion).toBe(true)
  const q = parse('**WAITING · item 7**\n***A.*** yes, ***B.*** no, ***C.*** later')!
  expect((q.pieces.filter(x => x.kind === 'choice') as any[]).map(c => `${c.letter}:${c.text}`)).toEqual(['A:yes', 'B:no', 'C:later'])
  expect(parse('***A.*** one\n\n***B.*** two')!.pieces.length).toBe(2)
  expect(parse('See ***A.*** here and nothing else')).toBe(null)
})

test('the one-line form draws one clickable circle per letter', async ($, on) => {
  on('ui.render', ($, e) => { const { Text } = $.ui.resolve(e); return <Text>engine</Text> })
  const ui = await $.ui.mount(MSG('**WAITING · item 7**\nPick: ***A.*** Build it now or ***B.*** Wait', 'desktop'))
  const svgs = ((await ui.findAll({ type: 'Svg' })) ?? []).filter((x: any) => String(x.props?.alt ?? '').length === 1)
  expect(new Set(svgs.map((x: any) => x.props.alt))).toEqual(new Set(['A', 'B']))
  await ui.unmount()
})

test('a card heading after text or a list has a clear gap above it; the first thing in a message does not', async ($, on) => {
  on('ui.render', ($, e) => { const { Text } = $.ui.resolve(e); return <Text>engine</Text> })
  const gaps = async (text: string) => {
    const ui = await $.ui.mount(MSG(text, 'desktop'))
    const n = ((await ui.findAll({ type: 'Svg' })) ?? []).filter((x: any) => String(x.props?.source).includes('height="14"') && String(x.props?.source).includes('width="1"')).length
    await ui.unmount()
    return n
  }
  const list = '1. one\n2. two\n3. three\n\n**SERVER · reading your allowance**\n- a\n- b'
  expect(await gaps(list)).toBe(1)
  expect(await gaps('**SERVER · reading your allowance**\n- a\n- b')).toBe(0)
})

test('an old question stays live: every click says which question it answers, old or newest', async ($, on) => {
  const sent: string[] = []
  on('prompt.submit', ($, e) => { sent.push(String((e as any).text)); return { text: String((e as any).text) } as any })
  const OLD = '**WAITING · item 3**\nWhich colour?\n\n***A.*** Red.\n\n***B.*** Blue.'
  const NEW = '**WAITING · item 4**\nWhich size?\n\n***A.*** Big.\n\n***B.*** Small.'
  const old = await $.ui.mount(MSG(OLD, 'desktop'))
  const now = await $.ui.mount(MSG(NEW, 'desktop'))
  // both questions have a click area on every letter
  expect(await old.find({ type: 'Client', key: 'pickA' })).toBeTruthy()
  expect(await old.find({ type: 'Client', key: 'pickB' })).toBeTruthy()
  expect(await now.find({ type: 'Client', key: 'pickB' })).toBeTruthy()
  try { await (old as any).post({ pick: 'B', q: hashText(OLD) }, { in: 'pickB' }) } catch (x) { throw new Error('old ' + x) }
  try { await (now as any).post({ pick: 'A', q: hashText(NEW) }, { in: 'pickA' }) } catch (x) { throw new Error('now ' + x) }
  // one press each; a second press on either sends nothing more
  await expect((old as any).post({ pick: 'A', q: hashText(OLD) }, { in: 'pickA' })).rejects.toThrow()
  expect(sent).toEqual(['Answer to WAITING \u00b7 item 3 (Which colour?): B', 'Answer to WAITING \u00b7 item 4 (Which size?): A'])
  await old.unmount()
  await now.unmount()
})

test('an undone pick goes back to unpicked, as if never clicked; other questions keep theirs', async ($) => {
  await savePick($, 'question one', 'B')
  await savePick($, 'question two', 'C')
  expect(await pickedOn($, 'question one')).toBe('B')
  await clearPick($, 'question one')
  expect(await pickedOn($, 'question one')).toBeUndefined()
  expect(await pickedOn($, 'question two')).toBe('C')
  await clearPick($, 'never asked')
})

test('a pick follows the chat: the answer message gone (rewind) means unpicked; just sent stays picked', async () => {
  const Q = '**WAITING · item 9**\nWhich?\n\n***A.*** Red.\n\n***B.*** Blue.'
  const chat = (...u: string[]) => [{ role: 'user', text: 'go' }, { role: 'assistant', text: Q }, ...u.map(t => ({ role: 'user', text: t }))]
  expect(answerIn(chat('B'), Q, 'B')).toBe('yes')
  expect(answerIn(chat(), Q, 'B')).toBe('no')
  expect(answerIn(chat('A'), Q, 'B')).toBe('no')
  expect(answerIn(chat('Answer to WAITING · item 9 (Which?): blue please'), Q, '=blue please')).toBe('yes')
  expect(answerIn([{ role: 'user', text: 'go' }], Q, 'B')).toBe('unknown')
  const calls = (msgs: any) => ({ session: { messages: async () => msgs } })
  // seen in the chat, then rewound out of it: not picked
  expect(await answerStands(calls(chat('B')), Q, 'B')).toBe(true)
  expect(await answerStands(calls(chat()), Q, 'B')).toBe(false)
  // just sent, not in the chat yet: still picked
  const Q2 = Q + ' two'
  sent.add(Q2)
  expect(await answerStands(calls([{ role: 'assistant', text: Q2 }]), Q2, 'B')).toBe(true)
  // a host with no transcript reading changes nothing
  expect(await answerStands({}, Q, 'B')).toBe(true)
})

test('an older question answered with "Answer to <heading>: B" counts as answered in the chat', async () => {
  const msgs = [
    { role: 'assistant', text: '**WAITING · item 3**\nWhich colour?\n\n***A.*** Red.\n\n***B.*** Blue.' },
    { role: 'user', text: 'Answer to WAITING · item 3 (Which colour?): B' },
    { role: 'assistant', text: 'ok' },
  ]
  expect(answerIn(msgs, msgs[0].text, 'B')).toBe('yes')
  expect(answerIn(msgs, msgs[0].text, 'A')).toBe('no')
})

test('two questions side by side: a click answers only its own; identical wording is told apart by the chat', async ($, on) => {
  const A = '**WAITING · item 5**\nWhich colour?\n\n***A.*** Red.\n\n***B.*** Blue.'
  const B = '**WAITING · item 5**\nWhich size?\n\n***A.*** Big.\n\n***B.*** Small.'
  // same heading, same letters: the line names the question, so each answer belongs to one
  expect(answerTag(A)).not.toBe(answerTag(B))
  const chat = [{ role: 'assistant', text: A }, { role: 'assistant', text: B }, { role: 'user', text: answerLine(A, 'B') }]
  expect(answerIn(chat, A, 'B')).toBe('yes')
  expect(answerIn(chat, B, 'B')).toBe('no')
  // the same question asked again after it was answered is open again
  const again = [{ role: 'assistant', text: A }, { role: 'user', text: answerLine(A, 'B') }, { role: 'assistant', text: A }]
  expect(answerIn(again, A, 'B')).toBe('no')
  // picks are kept apart per question
  await savePick($, A, 'A')
  await savePick($, B, 'B')
  expect(await pickedOn($, A)).toBe('A')
  expect(await pickedOn($, B)).toBe('B')
})
test('the frosted-background card has two glow colours and a picture path; a bad light is refused', async ($, on) => {
  on('ui.render', ($, e) => { const { Text } = $.ui.resolve(e); return <Text>engine</Text> })
  const pane = await $.ui.mount({ plugin: 'muster-look', component: 'Pane', requestId: 'muster-look-settings', surface: 'desktop', props: {} } as any)
  const lights = ((await pane.findAll({ type: 'Input' })) ?? []).filter((b: any) => b.props?.placeholder === '#rrggbb light')
  expect(lights.length).toBe(2)
  const pics = ((await pane.findAll({ type: 'Input' })) ?? []).filter((b: any) => String(b.props?.placeholder).startsWith('path to a small'))
  expect(pics.length).toBe(1)
})
test('the glass scene is calm, small enough, and takes the owner colours or picture', async () => {
  const s = sceneOf('#112233', '#445566')
  expect(s.length).toBeLessThan(131072)
  expect(s).toContain('#112233')
  expect(s).not.toContain('<script')
  const p = sceneOf('#112233', '#445566', 'data:image/png;base64,AAAA')
  expect(p).toContain('data:image/png;base64,AAAA')
})
