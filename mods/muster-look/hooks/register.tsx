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
      <Text color={c.text} backgroundColor={c.fill} bold>{` ${label} `}</Text>
    )

    const rows = parsed.pieces.map((p, i) => {
      const inQ = parsed.isQuestion && i >= parsed.startsAt
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
    const question = parsed.isQuestion ? rows.slice(parsed.startsAt) : []

    return (
      <Box flexDirection="column">
        {before}
        {question.length > 0 && (
          <Box flexDirection="row">
            <Box width={1} flexShrink={0} backgroundColor={YELLOW.text} />
            <Box flexDirection="column" paddingLeft={1}>
              {question}
            </Box>
          </Box>
        )}
      </Box>
    )
  })
}
