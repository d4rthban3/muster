import type { Register } from 'claude-code'
import { parse } from './parse'
import { cutFont, fromBase64, type Cut } from './font'
import { labelWidth } from './metrics'
import { panel, registerLook } from './panel'

// Muster's colours, taken from the owner's reference chips: a low tint of the
// chip's own hue, a thin brighter border in it, text in it. Dark first.
const YELLOW = { text: '#FFDB58', fill: '#3a3419', edge: '#8a7a30', glow: '#ffe066', lift: '#5c4f17' }
const PURPLE = { label: '#a995ff', text: '#9b6dff', fill: '#2b2748', edge: '#5b3fd0', glow: '#8f5bff', lift: '#463d7c' }

// A bordered Box is always three rows tall in the apps, so on desktop the chip
// is drawn as a small vector pill: thin brighter border, lifted fill, a soft
// glow, 28px tall. The label is spaced to its measured width, never stretched.
const esc = (t: string) => t.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
function svgChip(Svg: any, label: string, c: { text: string; label?: string; glow: string; lift: string }, font: string, cut: Cut | null, minTw = 0, pad = 0) {
  // The pill is as wide as the same words in body text (measured widths of the
  // app's regular-weight text). The letters keep their own shape: the label is
  // only ever spaced to that width, never stretched.
  const measured = labelWidth(label, 14)
  const tw = Math.max(minTw, Math.ceil(measured ?? label.length * 6.6))
  let face = ''
  let family = font
  if (cut !== null && Array.from(label).every(ch => cut.advance[ch] !== undefined)) {
    face = `<style>@font-face{font-family:"MusterAS";src:url(${cut.dataUri})}</style>`
    family = `MusterAS,${font}`
  }
  // The cut is the font's lightest setting; a hair of outline brings it to the
  // regular weight the chat's body text has.
  const stretch = ` textLength="${tw}" lengthAdjust="spacing"` + (face === '' ? '' : ` stroke="${c.label ?? c.text}" stroke-width="0.3" stroke-linejoin="round"`)
  const w = tw + 24
  // a single letter (a choice chip) is centred in its pill both ways; longer labels keep their left start
  const single = Array.from(label).length === 1
  // the pill itself is always 28 tall; pad is clear air above and below it, inside the picture
  const pill = 28
  const ht = pill + pad * 2
  const source =
    `<svg xmlns="http://www.w3.org/2000/svg" width="${w}" height="${ht}" viewBox="0 0 ${w} ${ht}" preserveAspectRatio="xMinYMid meet">` +
    face +
    `<g transform="translate(0 ${pad})">` +
    `<defs><filter id="g" x="-20%" y="-40%" width="140%" height="180%"><feGaussianBlur stdDeviation="1.2"/></filter></defs>` +
    `<rect x="2.25" y="2.25" width="${w - 4.5}" height="${pill - 4.5}" rx="${(pill - 4.5) / 2}" fill="none" stroke="${c.glow}" stroke-opacity="0.4" stroke-width="1" filter="url(#g)"/>` +
    `<rect x="2.25" y="2.25" width="${w - 4.5}" height="${pill - 4.5}" rx="${(pill - 4.5) / 2}" fill="${c.text}" fill-opacity="0.08" stroke="${c.glow}" stroke-width="0.5"/>` +
    (single
      ? `<text x="${w / 2}" y="${pill / 2}" text-anchor="middle" dominant-baseline="central" font-family="${family}" font-size="14" font-weight="400" font-style="normal" fill="${c.label ?? c.text}"${face === '' ? '' : ` stroke="${c.label ?? c.text}" stroke-width="0.3" stroke-linejoin="round"`}>${esc(label)}</text>`
      : `<text x="12" y="19" font-family="${family}" font-size="14" font-weight="400" font-style="normal" fill="${c.label ?? c.text}"${stretch}>${esc(label)}</text>`) +
    `</g></svg>`
  return <Svg alt={label} width={w} height={ht} source={source} />
}

// Anthropic Sans is read from the Claude app's own folder at run time, never copied.
const APP_FONT = ['/Applications/Claude.app', 'Contents', 'Resources', 'fonts', 'AnthropicSans-Romans-Variable-25x258.ttf'].join('/')
const FONT_TAIL = 'Anthropic Sans,Styrene B,system-ui,-apple-system,Segoe UI,sans-serif'
const BACKDROP = [0x19, 0x1c, 0x24]
const HEX = /^#[0-9a-fA-F]{6}$/

// A user's colour for a chip: the default palette exactly when it is the
// default colour, else a fill, lift and borders mixed from it and the dark page.
function palette(base: typeof YELLOW, want: unknown): typeof YELLOW {
  if (typeof want !== 'string' || !HEX.test(want) || want.toLowerCase() === base.text.toLowerCase()) return base
  const rgb = [1, 3, 5].map(i => parseInt(want.slice(i, i + 2), 16))
  const mix = (k: number) =>
    '#' + rgb.map((v, i) => Math.round(BACKDROP[i] * (1 - k) + v * k).toString(16).padStart(2, '0')).join('')
  return { text: want, fill: mix(0.2), lift: mix(0.42), edge: mix(0.55), glow: mix(0.95) }
}
const colourOr = (want: unknown, dflt: string) => (typeof want === 'string' && HEX.test(want) ? want : dflt)
const fontList = (want: unknown) => {
  if (want === 'System sans') return 'system-ui,-apple-system,Segoe UI,sans-serif'
  const name = typeof want === 'string' ? want.replace(/[^A-Za-z0-9 ,-]/g, '').trim() : ''
  return name === '' || name === 'Anthropic Sans' ? FONT_TAIL : `${name},${FONT_TAIL}`
}

export const register: Register = (on, options: any) => {
  const opts = options ?? {}
  const QUESTION = palette(YELLOW, opts.questionHeadingColor)
  const CARD = palette(PURPLE, opts.cardHeadingColor)
  const CHOICE = palette(YELLOW, opts.choiceChipColor)
  const TOP = colourOr(opts.lineTopColor, YELLOW.text)
  const BOTTOM = colourOr(opts.lineBottomColor, '#7c4dff')
  const FONT = fontList(opts.chipFont)
  const useAppFont = FONT === FONT_TAIL
  panel(on)
  let fontBytes: Uint8Array | null = null
  // Clickable choices: only the newest question is live, and one that has been
  // answered (by a click here, or by typing a reply) is not sent again.
  let latestQuestion = ''
  const answered = new Set<string>()
  on('prompt.submit', ($, e, next) => {
    if (latestQuestion !== '') answered.add(latestQuestion)
    return next(e)
  })
  on('ui.message', { component: 'AssistantMessage' }, async ($, e, next) => {
    const d = e.data as { pick?: string } | undefined
    if (/(^|\/)choice\.tsx$/.test(e.module) && d !== undefined && typeof d.pick === 'string' && /^[A-Z]$/.test(d.pick)) {
      if (latestQuestion !== '' && !answered.has(latestQuestion)) {
        answered.add(latestQuestion)
        void $.prompt.submit({ text: d.pick })
        $.ui.invalidate('ui.render')
      }
      return {}
    }
    return next(e)
  })
  const cuts: Record<string, Cut | null> = {}

  on('session.start', async ($, e, next) => {
    await registerLook($)
    if (useAppFont) {
      try {
        const { base64 } = (await $.fs.read(APP_FONT, { as: 'bytes' })) as { base64: string }
        fontBytes = fromBase64(base64)
      } catch {
        fontBytes = null
      }
    }
    return next(e)
  })
  on('ui.render', { component: 'AssistantMessage' }, ($, e, next) => {
    const parsed = parse(e.props.text)
    if (parsed === null) return next(e)

    const ui = $.ui.resolve(e) as any
    if (parsed.isQuestion) latestQuestion = e.props.text
    const live = parsed.isQuestion && e.props.text === latestQuestion && !answered.has(e.props.text)
    const { Box, Text, Markdown, Svg, Client } = ui
    const isTerminal = e.surface === 'terminal'
    // an empty picture h px tall: air in pixels (Box padding counts character cells)
    const spacerW = (px: number) => (
      <Svg alt="" width={px} height={1} source={`<svg xmlns="http://www.w3.org/2000/svg" width="${px}" height="1"/>`} />
    )
    const spacer = (px: number) => (
      <Svg alt="" width={1} height={px} source={`<svg xmlns="http://www.w3.org/2000/svg" width="1" height="${px}"/>`} />
    )

    // The letters this message's chips need, cut from the app's font once.
    let cut: Cut | null = null
    if (fontBytes !== null && !isTerminal) {
      const letters = Array.from(new Set(Array.from(
        parsed.pieces.map(p => (p.kind === 'title' ? `${p.word} · ${p.job}` : p.kind === 'choice' ? p.letter : '')).join(''),
      ))).sort().join('')
      if (!(letters in cuts)) cuts[letters] = cutFont(fontBytes, letters)
      cut = cuts[letters]
    }

    // Desktop and the other apps: the one-line rounded bordered chip, as first
    // built. Terminal: one line with thin bars at each end.
    const chip = (label: string, c: typeof YELLOW, minTw = 0, pad = 0) =>
      isTerminal ? (
        <Text>
          <Text color={c.edge}>{'\u258F'}</Text>
          <Text color={(c as any).label ?? c.text} backgroundColor={c.fill} bold>{` ${label} `}</Text>
          <Text color={c.edge}>{'\u2595'}</Text>
        </Text>
      ) : (
        svgChip(Svg, label, c, FONT, cut, minTw, pad)
      )

    let lastChoice = -1
    parsed.pieces.forEach((p, i) => { if (p.kind === 'choice') lastChoice = i })
    // Terminal width is not known here: a wrapped line is guessed at 70 columns.
    const lines = (p: (typeof parsed.pieces)[number]) =>
      p.kind === 'title' ? 1 : p.kind === 'choice' ? Math.max(1, Math.ceil((p.text.length + 5) / 70)) : p.text.split('\n').reduce((n, l) => n + Math.max(1, Math.ceil(l.length / 70)), 0)

    // Every choice chip is as wide as the widest letter, so all the choice text
    // starts at one x; each gets 4px of air above and below inside its own
    // picture, so the rows are even and a little looser. Sizes are unchanged.
    const letterTw = Math.max(0, ...parsed.pieces.map(p => (p.kind === 'choice' ? Math.ceil(labelWidth(p.letter, 14) ?? 9) : 0)))
    const rows = parsed.pieces.map((p, i) => {
      const inQ = parsed.isQuestion && i >= parsed.startsAt && i <= lastChoice
      if (p.kind === 'md') return <Markdown key={`m${i}`} text={p.text} />
      if (p.kind === 'title') {
        return (
          <Box key={`t${i}`}>{chip(`${p.word} · ${p.job}`, inQ ? QUESTION : CARD)}</Box>
        )
      }
      const firstChoice = parsed.pieces[i - 1]?.kind === 'md'
      const row = (
        <Box key={`c${i}`} gap={2} alignItems="center" position="relative" hover={live && !isTerminal && Client !== undefined ? { backgroundColor: '#23262e' } : undefined}>
          {chip(p.letter, CHOICE, letterTw, 4)}
          <Markdown key={`cm${i}`} text={p.text} />
          {live && !isTerminal && Client !== undefined && (
            <Box position="absolute" top={0} left={0} right={0} bottom={0}>
              <Client key={`pick${p.letter}`} module="./choice.tsx" props={{ letter: p.letter }} width="100%" height="100%" />
            </Box>
          )}
        </Box>
      )
      // the first choice under body text gets 4px more above it (its own 4 + these 4 =
      // the 8px between choice rows)
      return firstChoice && !isTerminal ? <Box key={`cw${i}`} flexDirection="column">{spacer(4)}{row}</Box> : row
    })

    const before = rows.slice(0, parsed.isQuestion ? parsed.startsAt : rows.length)
    const question = parsed.isQuestion ? rows.slice(parsed.startsAt, lastChoice + 1) : []
    const after = parsed.isQuestion ? rows.slice(lastChoice + 1) : []
    // Terminal: a column of thin bars as tall as the question, beside all of it.
    const termHeight = parsed.isQuestion
      ? parsed.pieces.slice(parsed.startsAt, lastChoice + 1).reduce((n, p) => n + lines(p), 0)
      : 0
    const rule = Array.from({ length: termHeight }, () => '\u258F').join('\n')

    // Apps: the yellow heading chip sits flush left; under it one solid thin
    // yellow line, and the intro and choices sit to the right of it. The line
    // is a vector the height of what it sits beside, worked out from line
    // counts (a text line about 18.5px, a choice row 28px at least), a little
    // short rather than long so it never runs into the next card.
    const px = (p: (typeof parsed.pieces)[number]) => {
      if (p.kind === 'title') return 0
      const wrap = (n: number) => Math.max(1, Math.ceil(n / 80))
      if (p.kind === 'choice') return Math.max(28, wrap(p.text.length + 5) * 18.5)
      return p.text.split('\n').reduce((n, l) => n + wrap(l.length) * 18.5, 0)
    }
    // The vector is as tall as what it sits beside; the line inside it keeps
    // 5px clear at the top and at the bottom, so the gap under the yellow chip
    // equals the gap above the next card's chip. It fades yellow to purple.
    const lineH = Math.max(
      14,
      Math.round(parsed.pieces.slice(parsed.startsAt + 1, lastChoice + 1).reduce((n, p) => n + px(p), 0)),
    )
    const railLine = Client !== undefined ? (
      // The line's region is laid over the column beside it (absolute), so the
      // glyph rows it draws can never make that column taller: the line ends
      // where the last choice ends. A 15px-wide empty picture holds its width.
      <Box flexShrink={0} position="relative">
        {spacerW(15)}
        <Box position="absolute" top={0} left={0} right={0} bottom={0} overflow="hidden">
          <Client key="rail" module="./rail.tsx" props={{ top: TOP, bottom: BOTTOM }} width="100%" height="100%" />
        </Box>
      </Box>
    ) : null
    const appLine = railLine ?? (
      <Box flexShrink={0} alignSelf="flex-start">
        <Svg
          alt="line"
          width={15}
          height={lineH}
          source={`<svg xmlns="http://www.w3.org/2000/svg" width="15" height="${lineH}"><defs><linearGradient id="f" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="${TOP}"/><stop offset="1" stop-color="${BOTTOM}"/></linearGradient></defs><rect x="12" y="5" width="1" height="${lineH - 10}" fill="url(#f)" shape-rendering="crispEdges"/></svg>`}
        />
      </Box>
    )

    return (
      <Box flexDirection="column">
        {before}
        {question.length > 0 && isTerminal && (
          <Box flexDirection="row">
            <Box flexShrink={0}><Text color={TOP}>{rule}</Text></Box>
            <Box flexDirection="column" paddingLeft={1}>
              {question}
            </Box>
          </Box>
        )}
        {question.length > 0 && !isTerminal && (
          <Box flexDirection="column">
            {question[0]}
            <Box flexDirection="row">
              {appLine}
              <Box flexDirection="column" paddingLeft={1}>
                {spacer(8)}
                {question.slice(1)}
              </Box>
            </Box>
          </Box>
        )}
        {after}
      </Box>
    )
  })
}
