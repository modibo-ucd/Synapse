import { SKIP, visit } from 'unist-util-visit'
import type { Element, Root, Text } from 'hast'

const HAS_CITATION = /\[S\d+\]/
const SKIP_TAGS = new Set(['code', 'pre', 'a', 'cite-chip'])

function splitMarkers(value: string): Array<Text | Element> {
  const marker = /\[S(\d+)\]/g
  const nodes: Array<Text | Element> = []
  let last = 0
  let match: RegExpExecArray | null
  while ((match = marker.exec(value)) !== null) {
    if (match.index > last) {
      nodes.push({ type: 'text', value: value.slice(last, match.index) })
    }
    nodes.push({
      type: 'element',
      tagName: 'cite-chip',
      properties: { dataCitationId: `S${match[1]}` },
      children: [{ type: 'text', value: match[0] }],
    })
    last = match.index + match[0].length
  }
  if (last < value.length) {
    nodes.push({ type: 'text', value: value.slice(last) })
  }
  return nodes
}

/**
 * Replaces `[S1]`-style citation markers in text nodes with controlled
 * `cite-chip` elements. Runs after sanitization; skips `code`, `pre`, `a` and
 * the chips it creates so they are never re-scanned.
 */
export function rehypeCitations(): (tree: Root) => void {
  return (tree: Root): void => {
    const rewrite = (parent: Element | Root): void => {
      let changed = false
      const next: Array<Text | Element> = []
      for (const child of parent.children) {
        if (child.type === 'text' && HAS_CITATION.test(child.value)) {
          changed = true
          next.push(...splitMarkers(child.value))
        } else {
          next.push(child as Text | Element)
        }
      }
      if (changed) (parent as Element).children = next
    }

    rewrite(tree)
    visit(tree, 'element', (node: Element) => {
      if (SKIP_TAGS.has(node.tagName)) return SKIP
      rewrite(node)
    })
  }
}
