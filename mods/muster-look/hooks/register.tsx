import type { Register } from 'claude-code'
import { parse } from './parse'

// Muster's colours, taken from the owner's reference chips: a low tint of the
// chip's own hue, a thin brighter border in it, text in it. Dark first.
const YELLOW = { text: '#FFDB58', fill: '#3a3419', edge: '#8a7a30' }
const PURPLE = { text: '#a995ff', fill: '#2b2748', edge: '#5f55a8' }

export const register: Register = on => {
  on('ui.render', { component: 'AssistantMessage' }, ($, e, next) => {
    const parsed = parse(e.props.text)
    if (parsed === null) return next(e)

    const { Box, Text, Markdown } = $.ui.resolve(e)

    // One line tall on every surface: a tinted fill and text in the chip's own
    // colour (the owner asked for smaller chips than the bordered box).
    const chip = (label: string, c: typeof YELLOW) => (
      <Text>
        <Text color={c.edge}>{'\u25D6'}</Text>
        <Text color={c.text} backgroundColor={c.fill} bold>{` ${label} `}</Text>
        <Text color={c.edge}>{'\u25D7'}</Text>
      </Text>
    )

    let lastChoice = -1
    parsed.pieces.forEach((p, i) => { if (p.kind === 'choice') lastChoice = i })
    // Terminal width is not known here: a wrapped line is guessed at 70 columns.
    const lines = (p: (typeof parsed.pieces)[number]) =>
      p.kind === 'title' ? 1 : p.kind === 'choice' ? Math.max(1, Math.ceil((p.text.length + 5) / 70)) : p.text.split('\n').reduce((n, l) => n + Math.max(1, Math.ceil(l.length / 70)), 0)

    const rows = parsed.pieces.map((p, i) => {
      const inQ = parsed.isQuestion && i >= parsed.startsAt && i <= lastChoice
      if (p.kind === 'md') return <Markdown key={`m${i}`} text={p.text} />
      if (p.kind === 'title') {
        return (
          <Box key={`t${i}`}>{chip(`${p.word} · ${p.job}`, inQ ? YELLOW : PURPLE)}</Box>
        )
      }
      return (
        <Box key={`c${i}`} gap={1}>
          {chip(p.letter, YELLOW)}
          <Markdown key={`cm${i}`} text={p.text} />
        </Box>
      )
    })

    const before = rows.slice(0, parsed.isQuestion ? parsed.startsAt : rows.length)
    const question = parsed.isQuestion ? rows.slice(parsed.startsAt, lastChoice + 1) : []
    const after = parsed.isQuestion ? rows.slice(lastChoice + 1) : []
    const height = parsed.isQuestion
      ? parsed.pieces.slice(parsed.startsAt, lastChoice + 1).reduce((n, p) => n + lines(p), 0)
      : 0
    // One unbroken rule: a single column of thin bars as tall as the question.
    const rule = Array.from({ length: height }, () => '\u258F').join('\n')

    return (
      <Box flexDirection="column">
        {before}
        {question.length > 0 && (
          <Box flexDirection="row">
            <Box flexShrink={0}><Text color={YELLOW.text}>{rule}</Text></Box>
            <Box flexDirection="column" paddingLeft={1}>
              {question}
            </Box>
          </Box>
        )}
        {after}
      </Box>
    )
  })
}
