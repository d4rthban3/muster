# The five-line starting note

The manager gives every new chat these five lines, nothing more. The chat then reads its own rules page (in
`muster/rules/`), not the whole decisions log.

```
Job:       <the worker's job in one line>
Owns:      <its folders or files>
Not yours: <what it must not touch; anything it is not sure is its own, it asks>
Open:      <items already waiting for it, by their exact job names>
First:     <read your worker definition and follow it; then your rules page, your last handover, and the first job by name>
```

Made-up example:
```
Job:       build the pieces of the shop site the manager orders
Owns:      the site's pages and code in your own copy of the project folder
Not yours: the payment settings; the inspector's notes; anything you are not sure is yours, ask
Open:      "filter button move"
First:     read <plugin folder>/agents/builder.md and follow it; then muster/rules/Builder_A.md, then muster/handovers/Builder_A_001.md if it exists, then "filter button move"
```
