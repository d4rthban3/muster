import { expect, test } from 'claude-code/testing'

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

async function svgSources($: any, options?: Record<string, string>) {
  const ui = await $.ui.mount(MSG(Q2, 'desktop'))
  const out: string[] = []
  for (const n of (await ui.findAll({ type: 'Svg' })) ?? []) out.push(String(n.props?.source ?? ''))
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

test('custom settings change the chip font, colours and line', { options: { chipFont: 'Georgia', questionHeadingColor: '#2dd4bf', choiceChipColor: '#ff7ab6', lineTopColor: '#2dd4bf', lineBottomColor: '#ff7ab6' } }, async ($, on) => {
  on('ui.render', ($, e) => { const { Text } = $.ui.resolve(e); return <Text>engine</Text> })
  const s = (await svgSources($)).join('\n')
  expect(s).toContain('font-family="Georgia,Anthropic Sans')
  expect(s).toContain('#2dd4bf')
  expect(s).toContain('#ff7ab6')
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
  expect(await ui.find({ type: 'Button', label: 'Use #9b6dff' })).toBeTruthy()
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
  ;(globalThis as any).h = (t: any, p: any, ...c: any[]) => ({ t, p, c })
  Field({ id: 'lineTopColor', hex: '#ff0000' }, surface)
  pointer({ type: 'down', x: 31, y: 6, button: 'left' })
  pointer({ type: 'up', x: 0, y: 6, button: 'left' })
  expect(posts.length).toBe(1)
  expect(posts[0].id).toBe('lineTopColor')
  expect(posts[0].hex).toBe('#ff0000')
})
