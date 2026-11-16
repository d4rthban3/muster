// Reads a TrueType font that is already on the machine (the Claude app's own
// Anthropic Sans) and cuts out only the letters a chip needs, so the chip's
// drawing can carry them and be sized from their real widths. Nothing of the
// font is kept in this mod: the bytes are read at run time and the cut-down
// copy only lives inside the drawing. Plain ECMAScript, no Node.

export type Cut = {
  /** data: address of the cut-down font, for an @font-face in a drawing */
  dataUri: string
  /** width of each cut letter, as a fraction of the font size */
  advance: Record<string, number>
}

const u16 = (d: DataView, o: number) => d.getUint16(o)
const u32 = (d: DataView, o: number) => d.getUint32(o)
const B64 = ['ABCDEFGHIJKLM', 'NOPQRSTUVWXYZ', 'abcdefghijklm', 'nopqrstuvwxyz', '0123456789', '+/'].join('')

export function toBase64(b: Uint8Array): string {
  let out = ''
  for (let i = 0; i < b.length; i += 3) {
    const n = (b[i] << 16) | ((b[i + 1] ?? 0) << 8) | (b[i + 2] ?? 0)
    out += B64[(n >> 18) & 63] + B64[(n >> 12) & 63]
    out += i + 1 < b.length ? B64[(n >> 6) & 63] : '='
    out += i + 2 < b.length ? B64[n & 63] : '='
  }
  return out
}

export function fromBase64(s: string): Uint8Array {
  const clean = s.replace(/[^A-Za-z0-9+/]/g, '')
  const out = new Uint8Array(Math.floor((clean.length * 3) / 4))
  let o = 0
  for (let i = 0; i < clean.length; i += 4) {
    const a = B64.indexOf(clean[i])
    const b = B64.indexOf(clean[i + 1])
    const c = i + 2 < clean.length ? B64.indexOf(clean[i + 2]) : -1
    const d = i + 3 < clean.length ? B64.indexOf(clean[i + 3]) : -1
    out[o++] = (a << 2) | (b >> 4)
    if (c >= 0) out[o++] = ((b & 15) << 4) | (c >> 2)
    if (d >= 0) out[o++] = ((c & 3) << 6) | d
  }
  return out.subarray(0, o)
}

function checksum(b: Uint8Array): number {
  let sum = 0
  for (let i = 0; i < b.length; i += 4) {
    sum = (sum + (((b[i] << 24) | ((b[i + 1] ?? 0) << 16) | ((b[i + 2] ?? 0) << 8) | (b[i + 3] ?? 0)) >>> 0)) >>> 0
  }
  return sum
}

export function cutFont(bytes: Uint8Array, text: string): Cut | null {
  try {
    return cut(bytes, text)
  } catch {
    return null
  }
}

function cut(bytes: Uint8Array, text: string): Cut | null {
  const d = new DataView(bytes.buffer, bytes.byteOffset, bytes.byteLength)
  if (u32(d, 0) !== 0x00010000) return null
  const tables: Record<string, [number, number]> = {}
  const count = u16(d, 4)
  for (let i = 0; i < count; i++) {
    const r = 12 + 16 * i
    const tag = String.fromCharCode(bytes[r], bytes[r + 1], bytes[r + 2], bytes[r + 3])
    tables[tag] = [u32(d, r + 8), u32(d, r + 12)]
  }
  for (const t of ['head', 'hhea', 'maxp', 'hmtx', 'cmap', 'glyf', 'loca', 'OS/2']) if (!tables[t]) return null

  const head = tables['head'][0]
  const upem = u16(d, head + 18)
  const longLoca = u16(d, head + 50) === 1
  const numGlyphs = u16(d, tables['maxp'][0] + 4)
  const hMetrics = u16(d, tables['hhea'][0] + 34)

  // cmap: a Unicode format 12 or format 4 table
  const cm = tables['cmap'][0]
  let sub = -1
  let fmt = 0
  for (let i = 0; i < u16(d, cm + 2); i++) {
    const p = u16(d, cm + 4 + 8 * i)
    const e = u16(d, cm + 6 + 8 * i)
    const off = cm + u32(d, cm + 8 + 8 * i)
    const f = u16(d, off)
    if (p === 3 && e === 10 && f === 12) { sub = off; fmt = 12; break }
    if (((p === 3 && e === 1) || p === 0) && f === 4 && fmt !== 12) { sub = off; fmt = 4 }
  }
  if (sub < 0) return null
  const lookup = (cp: number): number => {
    if (fmt === 12) {
      const n = u32(d, sub + 12)
      for (let g = 0; g < n; g++) {
        const s = u32(d, sub + 16 + 12 * g)
        const en = u32(d, sub + 20 + 12 * g)
        if (cp >= s && cp <= en) return u32(d, sub + 24 + 12 * g) + (cp - s)
      }
      return 0
    }
    const segX2 = u16(d, sub + 6)
    const endO = sub + 14
    const startO = endO + segX2 + 2
    const deltaO = startO + segX2
    const rangeO = deltaO + segX2
    for (let s = 0; s < segX2; s += 2) {
      if (cp > u16(d, endO + s)) continue
      if (cp < u16(d, startO + s)) return 0
      const ro = u16(d, rangeO + s)
      if (ro === 0) return (cp + u16(d, deltaO + s)) & 0xffff
      const g = u16(d, rangeO + s + ro + 2 * (cp - u16(d, startO + s)))
      return g === 0 ? 0 : (g + u16(d, deltaO + s)) & 0xffff
    }
    return 0
  }

  const chars = Array.from(new Set(Array.from(text)))
  const gidOf: Record<string, number> = {}
  const keep = new Set<number>([0])
  for (const ch of chars) {
    const g = lookup(ch.codePointAt(0) as number)
    gidOf[ch] = g
    keep.add(g)
  }

  const glyf = tables['glyf'][0]
  const loca = tables['loca'][0]
  const range = (g: number): [number, number] =>
    longLoca
      ? [u32(d, loca + 4 * g), u32(d, loca + 4 * g + 4)]
      : [u16(d, loca + 2 * g) * 2, u16(d, loca + 2 * g + 2) * 2]

  // a glyph built from other glyphs needs those too
  const queue = Array.from(keep)
  while (queue.length > 0) {
    const g = queue.pop() as number
    if (g >= numGlyphs) continue
    const [a, b] = range(g)
    if (b - a < 10 || (d.getInt16(glyf + a) as number) >= 0) continue
    let p = glyf + a + 10
    for (;;) {
      const flags = u16(d, p)
      const comp = u16(d, p + 2)
      if (!keep.has(comp)) { keep.add(comp); queue.push(comp) }
      p += 4 + (flags & 1 ? 4 : 2)
      if (flags & 8) p += 2
      else if (flags & 0x40) p += 4
      else if (flags & 0x80) p += 8
      if (!(flags & 0x20)) break
    }
  }
  const n = Math.max(...Array.from(keep)) + 1
  if (n > numGlyphs) return null

  const advOf = (g: number) => u16(d, tables['hmtx'][0] + 4 * Math.min(g, hMetrics - 1))
  const lsbOf = (g: number) =>
    g < hMetrics
      ? d.getInt16(tables['hmtx'][0] + 4 * g + 2)
      : d.getInt16(tables['hmtx'][0] + 4 * hMetrics + 2 * (g - hMetrics))

  // new glyf and loca (long form)
  const parts: Uint8Array[] = []
  const newLoca = new Uint8Array(4 * (n + 1))
  const lv = new DataView(newLoca.buffer)
  let at = 0
  for (let g = 0; g < n; g++) {
    lv.setUint32(4 * g, at)
    if (keep.has(g)) {
      const [a, b] = range(g)
      if (b > a) {
        const len = b - a
        const padded = new Uint8Array((len + 3) & ~3)
        padded.set(bytes.subarray(glyf + a, glyf + b))
        parts.push(padded)
        at += padded.length
      }
    }
  }
  lv.setUint32(4 * n, at)
  const newGlyf = new Uint8Array(at)
  let w = 0
  for (const p of parts) { newGlyf.set(p, w); w += p.length }

  const newHmtx = new Uint8Array(4 * n)
  const hv = new DataView(newHmtx.buffer)
  for (let g = 0; g < n; g++) { hv.setUint16(4 * g, advOf(g)); hv.setInt16(4 * g + 2, lsbOf(g)) }

  // new cmap: one format 4 table, one single-letter segment per letter
  const cps = chars
    .map(ch => ch.codePointAt(0) as number)
    .filter(cp => cp < 0xffff)
    .sort((a, b) => a - b)
  const segs = cps.length + 1
  const cmapLen = 12 + 16 + 8 * segs
  const newCmap = new Uint8Array(cmapLen)
  const cv = new DataView(newCmap.buffer)
  cv.setUint16(0, 0); cv.setUint16(2, 1)
  cv.setUint16(4, 3); cv.setUint16(6, 1); cv.setUint32(8, 12)
  const t4 = 12
  cv.setUint16(t4, 4); cv.setUint16(t4 + 2, 16 + 8 * segs); cv.setUint16(t4 + 4, 0)
  cv.setUint16(t4 + 6, segs * 2)
  let sr = 1; let es = 0
  while (sr * 2 <= segs) { sr *= 2; es++ }
  cv.setUint16(t4 + 8, sr * 2); cv.setUint16(t4 + 10, es); cv.setUint16(t4 + 12, segs * 2 - sr * 2)
  const eo = t4 + 14
  const so = eo + segs * 2 + 2
  const dO = so + segs * 2
  const ro = dO + segs * 2
  cps.forEach((cp, i) => {
    const gid = gidOf[String.fromCodePoint(cp)]
    cv.setUint16(eo + 2 * i, cp)
    cv.setUint16(so + 2 * i, cp)
    cv.setUint16(dO + 2 * i, (gid - cp) & 0xffff)
    cv.setUint16(ro + 2 * i, 0)
  })
  cv.setUint16(eo + 2 * cps.length, 0xffff)
  cv.setUint16(so + 2 * cps.length, 0xffff)
  cv.setUint16(dO + 2 * cps.length, 1)
  cv.setUint16(ro + 2 * cps.length, 0)

  const slice = (tag: string) => bytes.slice(tables[tag][0], tables[tag][0] + tables[tag][1])
  const newHead = slice('head')
  new DataView(newHead.buffer).setUint32(8, 0)
  new DataView(newHead.buffer).setUint16(50, 1)
  const newHhea = slice('hhea')
  new DataView(newHhea.buffer).setUint16(34, n)
  const newMaxp = slice('maxp')
  new DataView(newMaxp.buffer).setUint16(4, n)
  const newPost = new Uint8Array(32)
  new DataView(newPost.buffer).setUint32(0, 0x00030000)
  const newName = new Uint8Array(6)
  new DataView(newName.buffer).setUint16(4, 6)

  const out: Record<string, Uint8Array> = {
    'OS/2': slice('OS/2'), cmap: newCmap, glyf: newGlyf, head: newHead, hhea: newHhea,
    hmtx: newHmtx, loca: newLoca, maxp: newMaxp, name: newName, post: newPost,
  }
  const tags = Object.keys(out).sort()
  let size = 12 + 16 * tags.length
  for (const t of tags) size += (out[t].length + 3) & ~3
  const file = new Uint8Array(size)
  const fv = new DataView(file.buffer)
  fv.setUint32(0, 0x00010000); fv.setUint16(4, tags.length)
  let tsr = 1; let tes = 0
  while (tsr * 2 <= tags.length) { tsr *= 2; tes++ }
  fv.setUint16(6, tsr * 16); fv.setUint16(8, tes); fv.setUint16(10, tags.length * 16 - tsr * 16)
  let pos = 12 + 16 * tags.length
  tags.forEach((t, i) => {
    const r = 12 + 16 * i
    for (let k = 0; k < 4; k++) file[r + k] = t.charCodeAt(k)
    fv.setUint32(r + 4, checksum(out[t]))
    fv.setUint32(r + 8, pos)
    fv.setUint32(r + 12, out[t].length)
    file.set(out[t], pos)
    pos += (out[t].length + 3) & ~3
  })

  const advance: Record<string, number> = {}
  for (const ch of chars) advance[ch] = advOf(gidOf[ch]) / upem
  return { dataUri: 'data:font/ttf;base64,' + toBase64(file), advance }
}
