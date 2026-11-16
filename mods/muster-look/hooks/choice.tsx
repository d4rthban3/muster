// A transparent region laid over one choice row on desktop. A press inside it
// posts the row's letter to the plugin, which submits it as the user's reply.
export default function Choice(props: any, s: any) {
  const { Text } = s.elements
  if (s.state === undefined) {
    s.setState({ ready: true })
    s.onPointer((e: any) => {
      if (e.type === 'down') s.post({ pick: String(props.letter), q: String(props.q), t: String(props.t ?? '') })
    })
  }
  return <Text> </Text>
}
