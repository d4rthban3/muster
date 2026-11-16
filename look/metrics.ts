// How wide each character of the app's body text is, as a fraction of the font
// size (regular weight, as the chat draws it). Plain numbers measured once; used
// only to size a chip so its label takes the same room as the same words in the
// body. No font data.
export const WIDTH: Record<string, number> = {"0":0.604,"1":0.371,"2":0.581,"3":0.557,"4":0.612,"5":0.563,"6":0.569,"7":0.533,"8":0.561,"9":0.569,"!":0.236,"\"":0.408,"#":0.64,"$":0.521,"%":0.992,"&":0.684,"'":0.237,"(":0.404,")":0.404,"*":0.489,"+":0.64,",":0.236,"-":0.36,".":0.236,"/":0.335,":":0.236,";":0.236,"<":0.64,"=":0.64,">":0.64,"?":0.543,"@":0.873,"A":0.737,"B":0.688,"C":0.762,"D":0.742,"E":0.64,"F":0.596,"G":0.795,"H":0.741,"I":0.273,"J":0.54,"K":0.686,"L":0.578,"M":0.939,"N":0.787,"O":0.816,"P":0.611,"Q":0.816,"R":0.683,"S":0.589,"T":0.578,"U":0.726,"V":0.737,"W":1.013,"X":0.671,"Y":0.68,"Z":0.662,"[":0.404,"\\":0.335,"]":0.404,"^":0.64,"_":0.5,"`":0.5,"a":0.533,"b":0.62,"c":0.552,"d":0.62,"e":0.579,"f":0.419,"g":0.62,"h":0.597,"i":0.252,"j":0.252,"k":0.567,"l":0.252,"m":0.871,"n":0.597,"o":0.582,"p":0.62,"q":0.62,"r":0.403,"s":0.514,"t":0.419,"u":0.591,"v":0.563,"w":0.823,"x":0.571,"y":0.571,"z":0.505,"{":0.404,"|":0.304,"}":0.404,"~":0.64,"\u00b7":0.236,"\u2014":1,"\u2013":0.5,"\u2019":0.237," ":0.212}

/** Width of a label in pixels at a font size; null when a character is not in the table. */
export function labelWidth(label: string, size: number): number | null {
  let sum = 0
  for (const ch of Array.from(label)) {
    const w = WIDTH[ch]
    if (w === undefined) return null
    sum += w
  }
  return sum * size
}
