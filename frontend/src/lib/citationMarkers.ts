import { visit } from 'unist-util-visit'
import type { PhrasingContent, Root, Text } from 'mdast'

// A remark plugin (factory) that rewrites inline `[S1]`-style citation markers
// into link nodes (`#cite-S1`) so the renderer can replace them with citation
// chips. The marker text is a plain string in the source markdown, so this is
// purely a syntax-tree transform; it never touches HTML or executes anything.
export function citationMarkers() {
  return (tree: Root): void => {
    visit(tree, 'text', (node: Text, index, parent) => {
      if (parent === undefined || index === undefined) {
        return
      }
      const re = /\[S(\d+)\]/g
      if (!re.test(node.value)) {
        return
      }
      const replacement = splitMarkers(node.value)
      parent.children.splice(index, 1, ...replacement)
      return index + replacement.length
    })
  }
}

function splitMarkers(value: string): PhrasingContent[] {
  const nodes: PhrasingContent[] = []
  const re = /\[S(\d+)\]/g
  let lastIndex = 0
  let match: RegExpExecArray | null
  while ((match = re.exec(value)) !== null) {
    if (match.index > lastIndex) {
      nodes.push({ type: 'text', value: value.slice(lastIndex, match.index) })
    }
    nodes.push({
      type: 'link',
      url: `#cite-S${match[1]}`,
      children: [{ type: 'text', value: match[0] }],
    })
    lastIndex = match.index + match[0].length
  }
  if (lastIndex < value.length) {
    nodes.push({ type: 'text', value: value.slice(lastIndex) })
  }
  return nodes
}


