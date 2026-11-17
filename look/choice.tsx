// A transparent region laid over one whole choice row on desktop: the letter and its text are one
// click target. A press lights the row at once, drawn here with no round trip to the plugin, and
// posts the row's letter, which the plugin submits as the user's reply. The row stays lit only while
// held; the plugin's own picked light takes over as it redraws.
export default function Choice(props: any, s: any) {
  const { Box, Text } = s.elements
  if (s.state === undefined) {
    s.setState({ down: false })
    s.onPointer((e: any) => {
      if (e.type === 'down') {
        s.setState({ down: true })
        s.post({ pick: String(props.letter), q: String(props.q), t: String(props.t ?? '') })
      } else if (e.type === 'up' || e.type === 'leave') {
        s.setState({ down: false })
      }
    })
  }
  return (
    <Box width="100%" height="100%" backgroundColor={s.state?.down === true ? '#ffffff26' : '#00000001'}>
      <Text> </Text>
    </Box>
  )
}
