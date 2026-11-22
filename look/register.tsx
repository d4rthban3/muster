import type { Register } from 'claude-code'
import { parse } from './parse'
import { cutFont, fromBase64, type Cut } from './font'
import { labelWidth } from './metrics'
import { panel, registerLook } from './panel'
import { glass, glassOn, applyGlass, resetScene } from './glass'
import { pickName, loadGroup, pickedOn, typedOn, savePick, hashText, answerLine, optionLine, fullestText, clearPick, answerStands, sent, resetCaches, dropMessages, warmUp, dropSaved } from './group'
import { migrateLook, wrote } from './migrate'
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

// Which question and letter a sent line picks, or undefined (free words pick nothing): the option line
// a click put in the box, for any question not yet answered (newest first), or a lone letter of the newest.
export async function findPick($: any, line: string, questions: string[], answered: Set<string>, latest: string): Promise<{ text: string; letter: string } | undefined> {
  const sentLine = line.trim()
  const name = await pickName($)
  for (const text of [...questions].reverse()) {
    if (answered.has(text) || (await pickedOn($, text)) !== undefined) continue
    const q = parse(text)
    const c = q === null ? undefined : q.pieces.find(p => p.kind === 'choice' && (optionLine(text, p.letter) === sentLine || optionLine(text, p.letter, name) === sentLine))
    if (c !== undefined && c.kind === 'choice') return { text, letter: c.letter }
  }
  if (latest !== '' && !answered.has(latest) && (await pickedOn($, latest)) === undefined) {
    const m = /^\s*\**([A-Za-z])[.)]?\**\s*$/.exec(sentLine)
    const q = parse(latest)
    if (m !== null && q !== null && q.pieces.some(p => p.kind === 'choice' && p.letter === m[1]!.toUpperCase())) return { text: latest, letter: m[1]!.toUpperCase() }
  }
  return undefined
}

export const register: Register = (on) => {
  panel(on)
  glass(on)
  let fontBytes: Uint8Array | null = null
  // Clickable choices: only the newest question is live, and one that has been
  // answered (by a click here, or by typing a reply) is not sent again.
  let latestQuestion = ''
  const answered = new Set<string>()
  // what a click sent: the click already did its own bookkeeping, so it is not the owner typing
  const ours = new Set<string>()
  on('prompt.submit', async ($, e, next) => {
    // a message was sent: the kept conversation is read again the next time a card needs it
    dropMessages()
    // only the owner's own typing answers a question; a peer's message, a
    // notification, a scheduled prompt or another plugin's submit leaves it live
    const mine = ours.delete(String((e as any).text ?? ''))
    const owner = !mine && isOwnerSubmit(e)
    if (owner && latestQuestion !== '') {
      // Only a real pick answers a question; any other words the owner sends leave every question live.
      // A pick is the option line a click put in the box (for any question still drawn and unanswered,
      // newest first, so an older question stays live after a newer one appears), or, for the newest
      // question only, a reply that is just one of its letters.
      const hit = await findPick($, String((e as any).text ?? ''), Array.from(known.values()), answered, latestQuestion)
      if (hit !== undefined) {
        answered.add(hit.text)
        await savePick($, hit.text, hit.letter)
        sent.add(hit.text)
        $.ui.invalidate('ui.render')
      }
    }
    return next(e)
  })
  // Every option of every question is live until that question is answered. A press lights
  // its letter and sends at once; the save comes after. A second press on the same question
  // does nothing: `answered` holds it from the first press, the stored pick holds it after a reload.
  const known = new Map<string, string>()
  const pending = new Map<string, string>()
  // The owner took an edit back (chat:undo): the newest question goes back to unpicked
  // and live again, as if never clicked. (The one undo the mod API reports.)
  on('prompt.change', { origin: { kind: 'undo' } }, async ($, e, next) => {
    dropMessages()
    if (latestQuestion !== '') {
      answered.delete(latestQuestion)
      pending.delete(latestQuestion)
      await clearPick($, latestQuestion)
      $.ui.invalidate('ui.render')
    }
    return next(e)
  })
  on('ui.message', { component: 'AssistantMessage' }, async ($, e, next) => {
    const d = e.data as { pick?: string; q?: string } | undefined
    if (/(^|\/)choice\.tsx$/.test(e.module) && d !== undefined && typeof d.pick === 'string' && /^[A-Z]$/.test(d.pick)) {
      // the card carries its own question text (bounded), so a click works after a reload or an older card
      const sentText = typeof (d as { t?: string }).t === 'string' ? (d as { t?: string }).t : undefined
      const named =
        typeof d.q === 'string'
          ? (known.get(d.q) ?? (sentText !== undefined && hashText(sentText) === d.q ? sentText : undefined))
          : latestQuestion
      // the card may have been drawn while the message was still streaming: use the finished question
      const text = named === undefined || named === "" ? named : fullestText(named, known.values())
      if (text === undefined || text === '') {
        $.ui.toast('That click could not be matched to its question. Type the answer instead.')
      } else if (answered.has(text) || (await pickedOn($, text)) !== undefined) {
        $.ui.toast('That question is already answered.')
      } else {
        // a click only puts the option's full text in the owner's chat box; the owner presses Enter to
        // send it. Nothing is submitted here, and another click just replaces the draft.
        const name = await pickName($)
        const said = answerLine(text, d.pick, name)
        void $.prompt.fill({ text: said, mode: 'replace' }).then(
          r => {
            if (r !== undefined && (r as { isFilled?: boolean }).isFilled === false) $.ui.toast('The chat box could not take it. Type the answer instead.')
            else $.ui.toast('In the chat box. Press Enter to send.')
          },
          () => { $.ui.toast('The chat box could not take it. Type the answer instead.') },
        )
      }
      return {}
    }
    return next(e)
  })
  const cuts: Record<string, Cut | null> = {}

  // Opening a chat does the look's work after the chat is up: nothing here waits for a read. The first draw
  // waits only on the one batch of saved values (warmUp); the background, the old-plugin copy, the command and
  // the app's font follow beside it, and the font redraws the chips once it is in.
  on('session.start', async ($, e, next) => {
    resetCaches()
    resetScene()
    void warmUp($)
    // the app font is asked for at once and beside everything else
    void (async () => {
      try {
        const { base64 } = (await $.fs.read(APP_FONT, { as: 'bytes' })) as { base64: string }
        fontBytes = fromBase64(base64)
        $.ui.invalidate('ui.render')
      } catch {
        fontBytes = null
      }
    })()
    void (async () => {
      try {
        // the background goes first of the follow-ups
        if (await glassOn($)) await applyGlass($, true)
      } catch { /* no theme here */ }
      await Promise.all([
        // the one-time copy from the old plugin runs beside the first draw: when it copied anything, what the
        // draw read (and the background) is read again and the cards redraw
        migrateLook($).then(async () => {
          if (wrote.n === 0) return
          wrote.n = 0
          dropSaved(); resetScene(); void warmUp($)
          try { if (await glassOn($)) await applyGlass($, true) } catch { /* no theme here */ }
          $.ui.invalidate('ui.render')
        }, () => undefined),
        registerLook($).catch(() => undefined),
      ])
    })()
    return next(e)
  })
  on('ui.render', { component: 'AssistantMessage' }, async ($, e, next) => {
    const parsed = parse(e.props.text)
    if (parsed === null) return next(e)
    // this group's own look; a group with none gets the defaults (one batch of reads, shared by every card)
    await warmUp($)
    const opts = await loadGroup($)
    let picked = parsed.isQuestion ? (pending.get(e.props.text) ?? await pickedOn($, e.props.text)) : undefined
    let typed = parsed.isQuestion ? await typedOn($, e.props.text) : undefined
    // the saved answer is drawn at once; whether the chat still holds it (the rewind button) is checked after the
    // draw, off the drawing path, and a rewound answer goes back to unpicked and live again
    const mark = picked ?? (typed !== undefined ? '=' + typed : undefined)
    if (mark !== undefined) {
      const q = e.props.text
      void (async () => {
        try {
          if (await answerStands($, q, mark)) return
          answered.delete(q)
          pending.delete(q)
          await clearPick($, q)
          $.ui.invalidate('ui.render')
        } catch { /* the saved answer stays drawn */ }
      })()
    }
    const QUESTION = pillOf('question', opts)
    const CARD = pillOf('card', opts)
    const CHOICE = pillOf('choice', opts)
    const TOP = colourOr(opts.lineTopColor, YELLOW.text)
    const BOTTOM = colourOr(opts.lineBottomColor, '#7c4dff')
    const FONT = fontList(opts.chipFont)
    const useAppFont = FONT === FONT_TAIL

    const ui = $.ui.resolve(e) as any
    if (parsed.isQuestion) latestQuestion = e.props.text
    if (parsed.isQuestion) known.set(hashText(e.props.text), e.props.text)
    const live = parsed.isQuestion && !answered.has(e.props.text) && picked === undefined && typed === undefined
    const liveNewest = live && e.props.text === latestQuestion
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
        parsed.pieces.map(p => (p.kind === 'title' ? `${p.word} · ${p.job}` : p.kind === 'choice' ? p.letter : p.kind === 'status' ? p.badge : '')).join(''),
      ))).sort().join('')
      if (!(letters in cuts)) cuts[letters] = cutFont(fontBytes, letters)
      cut = cuts[letters] ?? null
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
      p.kind === 'title' ? 1 : p.kind === 'status' ? (p.rest === '' ? 1 : 2) : p.kind === 'choice' ? Math.max(1, Math.ceil((p.text.length + 5) / 70)) : p.text.split('\n').reduce((n, l) => n + Math.max(1, Math.ceil(l.length / 70)), 0)

    // Every choice chip is as wide as the widest letter, so all the choice text
    // starts at one x; each gets 4px of air above and below inside its own
    // picture, so the rows are even and a little looser. Sizes are unchanged.
    const letterTw = Math.max(0, ...parsed.pieces.map(p => (p.kind === 'choice' ? Math.ceil(labelWidth(p.letter, 14) ?? 9) : 0)))
    // Lines the press region draws for a choice: a generous count (a narrow window wraps at about 40
    // columns, +1 for the padding); the extra is clipped by the row, a short count would leave dead lines.
    const pressRows = (t: string) => Math.max(2, Math.ceil((t.length + 5) / 40) + 1)
    const rows = parsed.pieces.map((p, i) => {
      const inQ = parsed.isQuestion && i >= parsed.startsAt && i <= lastChoice
      if (p.kind === 'md') return <Markdown key={`m${i}`} text={p.text} />
      if (p.kind === 'status') {
        // laid out as a card's title badge is: the badge on its own line, clear air above it after text,
        // and the rest of the line below it as card text, in the card colour
        const gapAbove = parsed.pieces[i - 1]?.kind === 'md'
        return (
          <Box key={`s${i}`} flexDirection="column">
            {gapAbove && (isTerminal ? <Text key="sgap"> </Text> : spacer(14))}
            {chip(p.badge, CARD)}
            {p.rest !== '' && <Markdown key={`sm${i}`} text={p.rest} />}
          </Box>
        )
      }
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
      // The picked row's highlight is in the flow, never laid over the words: a strip with two rounded
      // corners above, the words on the filled body, a strip below. The chip's own 4px of air above and
      // below is given up (pad 0) for the strips' 4px, so the row keeps the height it had.
      const lit = p.letter === picked && !isTerminal
      const HL = '#23262e'
      const HR = 4
      const corner = (d: string, k: string) => (
        <Svg key={k} alt="" width={HR} height={HR} source={`<svg xmlns="http://www.w3.org/2000/svg" width="${HR}" height="${HR}"><path d="${d}" fill="${HL}"/></svg>`} />
      )
      const strip = (top: boolean) => (
        <Box key={top ? 'hs-top' : 'hs-bottom'} flexDirection="row">
          {corner(top ? `M${HR} ${HR}L0 ${HR}A${HR} ${HR} 0 0 1 ${HR} 0Z` : `M${HR} 0L${HR} ${HR}A${HR} ${HR} 0 0 1 0 0Z`, 'l')}
          <Box flexGrow={1} backgroundColor={HL}>{spacer(HR)}</Box>
          {corner(top ? `M0 ${HR}L0 0A${HR} ${HR} 0 0 1 ${HR} ${HR}Z` : `M0 0L${HR} 0A${HR} ${HR} 0 0 1 0 ${HR}Z`, 'r')}
        </Box>
      )
      const parts = [
          live && !isTerminal ? (
            <Box key="chipw" position="relative" flexShrink={0}>
              {chip(p.letter, CHOICE, letterTw, 4)}
              <Box position="absolute" top={0} left={0} display="none" hover={{ display: 'flex' }}>
                {chip(p.letter, CHOICE, letterTw, 4, true)}
              </Box>
            </Box>
          ) : <Box key="chipw" flexShrink={0}>{chip(p.letter, CHOICE, letterTw, lit ? 0 : 4, p.letter === picked)}</Box>,
          <Box key={`cb${i}`} flexShrink={1} flexGrow={1}><Markdown key={`cm${i}`} text={p.text} /></Box>,
          live && !isTerminal && Client !== undefined && (
            <Box key="pickw" position="absolute" top={0} left={0} right={0} bottom={0} width="100%" height="100%" overflow="hidden">
              <Client key={`pick${p.letter}`} module="./choice.tsx" props={{ letter: p.letter, rows: pressRows(p.text), q: hashText(e.props.text), t: e.props.text.length <= 4000 ? e.props.text : '' }} width="100%" height="100%" />
            </Box>
          ),
      ]
      const row = lit ? (
        <Box key={`c${i}`} flexDirection="column">
          {strip(true)}
          <Box gap={2} alignItems="center" backgroundColor={HL}>{parts}</Box>
          {strip(false)}
        </Box>
      ) : (
        <Box key={`c${i}`} gap={2} alignItems="center" position="relative" hover={live && !isTerminal && Client !== undefined ? { backgroundColor: '#23262e' } : undefined}>
          {parts}
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

    // Apps: the yellow heading chip sits flush left; under it one thin line, and the intro and choices
    // sit to the right of it. The line is not drawn at a guessed height: it is a column that stretches
    // to the height of what it sits beside, made of equal slices that share that height, each one pixel
    // wide and one step further from yellow towards purple, so it ends exactly where the last choice
    // ends at any window width. 5px stay clear at its top and bottom. Slices start at zero height and only share
    // what is left over, so a short card never grows to fit them.
    const SLICES = 48
    const hexMix = (a: string, b: string, k: number) => {
      const c = (h: string, i: number) => parseInt(h.slice(i, i + 2), 16)
      return '#' + [1, 3, 5].map(i => Math.round(c(a, i) * (1 - k) + c(b, i) * k).toString(16).padStart(2, '0')).join('')
    }
    const appLine = (
      <Box flexShrink={0} flexDirection="row">
        {spacerW(12)}
        <Box flexDirection="column">
          {spacer(5)}
          {Array.from({ length: SLICES }, (_, n) => (
            <Box key={`ln${n}`} height={0} flexGrow={1} flexShrink={1} overflow="hidden" backgroundColor={hexMix(TOP, BOTTOM, (n + 0.5) / SLICES)} />
          ))}
          {spacer(5)}
        </Box>
        {spacerW(2)}
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
        {parsed.isQuestion && liveNewest && Input !== undefined && (
          <Box key="own" flexDirection="column" paddingLeft={1}>
            {isTerminal ? null : spacer(6)}
            <Input
              key="own-answer"
              placeholder="Or type your own answer"
              submitLabel="send"
              onSubmit={(t: string) => {
                const words = String(t).trim()
                if (words === '' || e.props.text !== latestQuestion || answered.has(e.props.text)) return
                answered.add(e.props.text)
                sent.add(e.props.text)
                void savePick($, e.props.text, '=' + words.slice(0, 300)).then(() => $.ui.invalidate('ui.render'))
                void $.prompt.submit({ text: answerLine(e.props.text, words) })
              }}
            />
          </Box>
        )}
        {parsed.isQuestion && typed !== undefined && (
          // his own answer, sent from the box under the choices: the box fills yellow (the question's own
          // colour) and shows his words; it, the lock and the words stay wherever this question is drawn
          <Box key="typed" paddingLeft={1} flexDirection="column">
            {isTerminal ? null : spacer(6)}
            <Box key="typed-box" flexGrow={1} backgroundColor={isTerminal ? undefined : QUESTION.fill} paddingLeft={1} paddingRight={1}>
              <Text color={QUESTION.text}>{typed}</Text>
            </Box>
          </Box>
        )}
        {after.length > 0 && parsed.pieces[lastChoice + 1]?.kind === 'title' && (isTerminal ? <Text key="gap"> </Text> : spacer(14))}
        {after}
      </Box>
    )
  })
}
