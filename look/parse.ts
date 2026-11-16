// Splits an assistant message into plain markdown and the few Muster shapes.
// Pure text in, plain data out: the same words stay the real structure.
export type Piece =
  | { kind: 'md'; text: string }
  | { kind: 'title'; word: string; job: string }
  | { kind: 'choice'; letter: string; text: string }

export type Parsed = { pieces: Piece[]; isQuestion: boolean; startsAt: number }

const TITLE = /^\*\*([A-Za-z][A-Za-z_ ]{1,24}) · (.{1,80}?)\*\*\s*$/
const CHOICE = /^\*\*\*([A-Z])\.\*\*\*\s*(.*)$/

const MARK = /(?:^|\s)\*\*\*([A-Z])\.\*\*\*\s*/g

// A waiting question sent on one line: ***A.*** one or ***B.*** two. Two or more markers on a line
// become separate choices, the words before the first one stay plain text, and the joining
// "or" / comma between choices is dropped.
function inline(line: string): { lead: string; items: { letter: string; text: string }[] } | null {
  const marks = [...line.matchAll(MARK)]
  if (marks.length < 2) return null
  const items = marks.map((m, i) => {
    const from = (m.index ?? 0) + m[0].length
    const to = i + 1 < marks.length ? (marks[i + 1].index ?? line.length) : line.length
    const text = line.slice(from, to).trim().replace(/[\s,;]*(?:\bor\b)?[\s,;]*$/i, '').trim()
    return { letter: m[1], text }
  })
  return { lead: line.slice(0, marks[0].index ?? 0).trim(), items }
}

export function parse(text: string): Parsed | null {
  const pieces: Piece[] = []
  let buf: string[] = []
  const flush = () => {
    const t = buf.join('\n').replace(/^\n+|\n+$/g, '')
    if (t) pieces.push({ kind: 'md', text: t })
    buf = []
  }
  for (const line of text.split('\n')) {
    const t = TITLE.exec(line)
    const c = CHOICE.exec(line)
    const many = t ? null : inline(line)
    if (many) {
      if (many.lead !== '') buf.push(many.lead)
      flush()
      for (const it of many.items) pieces.push({ kind: 'choice', letter: it.letter, text: it.text })
    } else if (t) { flush(); pieces.push({ kind: 'title', word: t[1], job: t[2] }) }
    else if (c) { flush(); pieces.push({ kind: 'choice', letter: c[1], text: c[2] }) }
    else buf.push(line)
  }
  flush()
  if (!pieces.some(p => p.kind !== 'md')) return null
  const isQuestion = pieces.some(p => p.kind === 'choice')
  // the question block starts at the title just before the first choice, else the first paragraph before it
  const firstChoice = pieces.findIndex(p => p.kind === 'choice')
  let startsAt = -1
  if (isQuestion) {
    startsAt = firstChoice
    for (let i = firstChoice - 1; i >= 0; i--) {
      startsAt = i
      if (pieces[i].kind === 'title') break
      if (pieces[i].kind === 'md' && i < firstChoice - 1) break
    }
  }
  return { pieces, isQuestion, startsAt }
}
