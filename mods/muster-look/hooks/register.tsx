import type { Register } from 'claude-code'
import { parse } from './parse'
import { cutFont, fromBase64, type Cut } from './font'
import { labelWidth } from './metrics'
import { panel, registerLook } from './panel'
import { glass, glassOn, applyGlass } from './glass'
import { loadGroup, pickedOn, typedOn, savePick } from './group'
import { svgChip, pillOf, colourOr, YELLOW } from './chip'


// Anthropic Sans is read from the Claude app's own folder at run time, never copied.
const APP_FONT = ['/Applications/Claude.app', 'Contents', 'Resources', 'fonts', 'AnthropicSans-Romans-Variable-25x258.ttf'].join('/')
const FONT_TAIL = 'Anthropic Sans,Styrene B,system-ui,-apple-system,Segoe UI,sans-serif'
const fontList = (want: unknown) => {
  if (want === 'System sans') return 'system-ui,-apple-system,Segoe UI,sans-serif'
  const name = typeof want === 'string' ? want.replace(/[^A-Za-z0-9 ,-]/g, '').trim() : ''
  return name === '' || name === 'Anthropic Sans' ? FONT_TAIL : `${name},${FONT_TAIL}`
}

// true only for the owner's own typing (the composer, or the phone/web bridge)
export const isOwnerSubmit = (e: any): boolean => e?.origin?.kind === 'composer' || e?.origin?.kind === 'bridge'

export const register: Register = (on) => {
  panel(on)
  glass(on)
  let fontBytes: Uint8Array | null = null
  // Clickable choices: only the newest question is live, and one that has been
  // answered (by a click here, or by typing a reply) is not sent again.
  let latestQuestion = ''
  const answered = new Set<string>()
  on('prompt.submit', async ($, e, next) => {
    // only the owner's own typing answers a question; a peer's message, a
    // notification, a scheduled prompt or another plugin's submit leaves it live
    const owner = isOwnerSubmit(e)
    if (owner && latestQuestion !== '') {
      answered.add(latestQuestion)
      // a reply that is just a letter of that question sticks on it
      const m = /^\s*\**([A-Za-z])[.)]?\**\s*$/.exec(String((e as any).text ?? ''))
      const q = parse(latestQuestion)
      if (m !== null && q !== null && q.pieces.some(p => p.kind === 'choice' && p.letter === m[1].toUpperCase())) {
        await savePick($, latestQuestion, m[1].toUpperCase())
        $.ui.invalidate('ui.render')
      }
    }
    return next(e)
  })
  on('ui.message', { component: 'AssistantMessage' }, async ($, e, next) => {
    const d = e.data as { pick?: string } | undefined
    if (/(^|\/)choice\.tsx$/.test(e.module) && d !== undefined && typeof d.pick === 'string' && /^[A-Z]$/.test(d.pick)) {
      if (latestQuestion !== '' && !answered.has(latestQuestion)) {
        answered.add(latestQuestion)
        await savePick($, latestQuestion, d.pick)
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
    if (await glassOn($)) await applyGlass($, true)
    {
      try {
        const { base64 } = (await $.fs.read(APP_FONT, { as: 'bytes' })) as { base64: string }
        fontBytes = fromBase64(base64)
      } catch {
        fontBytes = null
      }
    }
    return next(e)
  })
  on('ui.render', { component: 'AssistantMessage' }, async ($, e, next) => {
    const parsed = parse(e.props.text)
    if (parsed === null) return next(e)
    // this group's own look; a group with none gets the defaults
    const opts = await loadGroup($)
    const picked = parsed.isQuestion ? await pickedOn($, e.props.text) : undefined
    const typed = parsed.isQuestion ? await typedOn($, e.props.text) : undefined
    const QUESTION = pillOf('question', opts)
    const CARD = pillOf('card', opts)
    const CHOICE = pillOf('choice', opts)
    const TOP = colourOr(opts.lineTopColor, YELLOW.text)
    const BOTTOM = colourOr(opts.lineBottomColor, '#7c4dff')
    const FONT = fontList(opts.chipFont)
    const useAppFont = FONT === FONT_TAIL

    const ui = $.ui.resolve(e) as any
    if (parsed.isQuestion) latestQuestion = e.props.text
    const live = parsed.isQuestion && e.props.text === latestQuestion && !answered.has(e.props.text)
    const { Box, Text, Markdown, Svg, Client, Input } = ui
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
    if (useAppFont && fontBytes !== null && !isTerminal) {
      const letters = Array.from(new Set(Array.from(
        parsed.pieces.map(p => (p.kind === 'title' ? `${p.word} · ${p.job}` : p.kind === 'choice' ? p.letter : '')).join(''),
      ))).sort().join('')
      if (!(letters in cuts)) cuts[letters] = cutFont(fontBytes, letters)
      cut = cuts[letters]
    }

    // Desktop and the other apps: the one-line rounded bordered chip, as first
    // built. Terminal: one line with thin bars at each end.
    const chip = (label: string, c: typeof YELLOW, minTw = 0, pad = 0, hot = false) =>
      isTerminal ? (
        <Text>
          <Text color={c.edge}>{'\u258F'}</Text>
          <Text color={(c as any).label ?? c.text} backgroundColor={hot ? c.edge : c.fill} bold>{` ${label} `}</Text>
          <Text color={c.edge}>{'\u2595'}</Text>
        </Text>
      ) : (
        svgChip(Svg, label, c, FONT, cut, minTw, pad, hot)
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
        // a card heading right after text or a list gets clear air above it, so it reads as a new card
        const gapAbove = !inQ && parsed.pieces[i - 1]?.kind === 'md'
        return (
          <Box key={`t${i}`} flexDirection="column">
            {gapAbove && (isTerminal ? <Text key="tgap"> </Text> : spacer(14))}
            {chip(`${p.word} · ${p.job}`, inQ ? QUESTION : CARD)}
          </Box>
        )
      }
      const firstChoice = parsed.pieces[i - 1]?.kind === 'md'
      const row = (
        <Box key={`c${i}`} gap={2} alignItems="center" position="relative" backgroundColor={p.letter === picked && !isTerminal ? '#23262e' : undefined} hover={live && !isTerminal && Client !== undefined ? { backgroundColor: '#23262e' } : undefined}>
          {live && !isTerminal ? (
            <Box position="relative" flexShrink={0}>
              {chip(p.letter, CHOICE, letterTw, 4)}
              <Box position="absolute" top={0} left={0} display="none" hover={{ display: 'flex' }}>
                {chip(p.letter, CHOICE, letterTw, 4, true)}
              </Box>
            </Box>
          ) : <Box flexShrink={0}>{chip(p.letter, CHOICE, letterTw, 4, p.letter === picked)}</Box>}
          <Box key={`cb${i}`} flexShrink={1} flexGrow={1}><Markdown key={`cm${i}`} text={p.text} /></Box>
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
        {parsed.isQuestion && live && Input !== undefined && (
          <Box key="own" flexDirection="column" paddingLeft={1}>
            {isTerminal ? null : spacer(6)}
            <Input
              key="own-answer"
              placeholder="Or type your own answer"
              submitLabel="send"
              onSubmit={(t: string) => {
                const words = String(t).trim()
                const head = parsed.pieces[parsed.startsAt]
                if (words === '' || e.props.text !== latestQuestion || answered.has(e.props.text)) return
                answered.add(e.props.text)
                const tag = head !== undefined && head.kind === 'title' ? `${head.word} \u00b7 ${head.job}` : 'the question above'
                void savePick($, e.props.text, '=' + words.slice(0, 300)).then(() => $.ui.invalidate('ui.render'))
                void $.prompt.submit({ text: `Answer to ${tag}: ${words}` })
              }}
            />
          </Box>
        )}
        {parsed.isQuestion && typed !== undefined && (
          <Box key="typed" paddingLeft={1}>
            <Text color="#b4b9c6">{`Your answer: ${typed}`}</Text>
          </Box>
        )}
        {after.length > 0 && parsed.pieces[lastChoice + 1]?.kind === 'title' && (isTerminal ? <Text key="gap"> </Text> : spacer(14))}
        {after}
      </Box>
    )
  })
}
