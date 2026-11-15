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
    expect((await ui.find({ type: 'Text', text: /WAITING · item 7/ }))?.text).toContain('WAITING')
    expect(await ui.find({ type: 'Text', text: /^ ?A ?$/ })).toBeTruthy()
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
  const ui = await $.ui.mount(MSG('**PASS received · muster look build**\n- Done.', 'desktop'))
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
  const ui = await $.ui.mount(MSG(text, 'desktop'))
  const rule = await ui.find({ type: 'Text', text: /^▏(\n▏)*$/ })
  expect(rule).toBeTruthy()
  // the question has a title, two choices: the rule is at least 3 lines and stops there
  expect((rule?.text ?? '').split('\n').length).toBeLessThan(8)
  await ui.unmount()
})
