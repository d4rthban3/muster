// Splits an assistant message into plain markdown and the few Muster shapes.
// Pure text in, plain data out: the same words stay the real structure.
export type Piece =
  | { kind: 'md'; text: string }
  | { kind: 'title'; word: string; job: string }
  | { kind: 'choice'; letter: string; text: string }

export type Parsed = { pieces: Piece[]; isQuestion: boolean; startsAt: number }

const TITLE = /^\*\*([A-Z][A-Z_ ]{1,24}) · (.{1,80}?)\*\*\s*$/
const CHOICE = /^\*\*\*([A-Z])\.\*\*\*\s*(.*)$/

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
    if (t) { flush(); pieces.push({ kind: 'title', word: t[1], job: t[2] }) }
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
