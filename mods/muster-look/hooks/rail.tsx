// The left line of a question on desktop: one thin glyph per row of the region
// it stands in, so it is exactly as tall as the rows it sits beside (the region's
// own laid-out height, never a line-count guess), fading from the top colour to
// the bottom colour.
const mix = (a: string, b: string, k: number) => {
  const p = (hex: string, i: number) => parseInt(hex.slice(i, i + 2), 16)
  return '#' + [1, 3, 5].map(i => Math.round(p(a, i) * (1 - k) + p(b, i) * k).toString(16).padStart(2, '0')).join('')
}

export default function Rail(props: any, s: any) {
  const { Box, Text } = s.elements
  const n = Math.max(1, s.rows)
  const top = String(props.top)
  const bottom = String(props.bottom)
  const cells = []
  for (let i = 0; i < n; i++) cells.push(<Text key={`r${i}`} color={mix(top, bottom, n === 1 ? 0 : i / (n - 1))}>{'▕'}</Text>)
  return <Box flexDirection="column">{cells}</Box>
}
