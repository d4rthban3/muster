// A colour field with a hue bar, drawn as a grid of coloured cells. Click or
// drag in the field for saturation and brightness, in the bar for hue; the
// colour is posted to the panel when the button is let go.
import { hexToHsv, hsvToHex } from './color'

const COLS = 24
const ROWS = 3

export default function Field(props: any, s: any) {
  const { Box, Text } = s.elements
  if (s.state === undefined) {
    const ref = { ...hexToHsv(String(props.hex)), area: '' as '' | 'field' | 'hue' }
    s.setState({ ref, n: 0 })
    const apply = (e: any) => {
      const fx = Math.min(1, Math.max(0, e.x / (COLS - 1)))
      const fy = Math.min(1, Math.max(0, e.y / (ROWS - 1)))
      if (ref.area === 'field') { ref.s = fx; ref.v = 1 - fy } else if (ref.area === 'hue') ref.h = fx * 359.9
    }
    s.onPointer((e: any) => {
      if (e.type === 'down') { ref.area = e.y < ROWS ? 'field' : 'hue'; apply(e) }
      else if (e.type === 'move' && e.button !== undefined && ref.area !== '') apply(e)
      else if (e.type === 'up' && ref.area !== '') {
        apply(e)
        ref.area = ''
        s.post({ id: String(props.id), hex: hsvToHex(ref.h, ref.s, ref.v) })
      } else return
      s.setState({ ref, n: Math.random() })
    })
    return <Text> </Text>
  }
  const ref = s.state.ref
  const cx = Math.round(ref.s * (COLS - 1))
  const cy = Math.round((1 - ref.v) * (ROWS - 1))
  const hx = Math.round((ref.h / 359.9) * (COLS - 1))
  const rows = []
  for (let y = 0; y < ROWS; y++) {
    const cells = []
    for (let x = 0; x < COLS; x++) {
      const bg = hsvToHex(ref.h, x / (COLS - 1), 1 - y / (ROWS - 1))
      cells.push(<Text key={`f${x}`} backgroundColor={bg} color={ref.v > 0.5 ? '#000000' : '#ffffff'}>{x === cx && y === cy ? '+' : ' '}</Text>)
    }
    rows.push(<Box key={`r${y}`} flexDirection="row">{cells}</Box>)
  }
  const bar = []
  for (let x = 0; x < COLS; x++) {
    bar.push(<Text key={`h${x}`} backgroundColor={hsvToHex((x / (COLS - 1)) * 359.9, 1, 1)} color="#000000">{x === hx ? '|' : ' '}</Text>)
  }
  return (
    <Box flexDirection="column">
      {rows}
      <Box key="bar" flexDirection="row">{bar}</Box>
    </Box>
  )
}
