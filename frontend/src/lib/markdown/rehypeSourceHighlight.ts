import { SKIP, visit } from 'unist-util-visit'
import type { Element, Root } from 'hast'

export interface HighlightRange {
  start: number
  end: number
  level: 'primary' | 'secondary'
}

/** Block-level elements that may carry a whole-block highlight. */
const BLOCKS = new Set(['p', 'li', 'tr', 'pre', 'blockquote', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6'])

/**
 * Marks the smallest block elements whose mdast source offsets overlap any of
 * `ranges`. A nested `<li>` that contains its own list is skipped so the inner
 * items are marked individually. Highlight granularity is a whole block by
 * design — it is robust against Markdown normalization.
 */
export function rehypeSourceHighlight(options: { ranges: HighlightRange[] }) {
  return (tree: Root): void => {
    visit(tree, 'element', (node: Element) => {
      if (!BLOCKS.has(node.tagName) || !node.position) return
      const start = node.position.start.offset
      const end = node.position.end.offset
      if (start == null || end == null) return
      if (
        node.tagName === 'li' &&
        node.children.some(
          (child) => child.type === 'element' && (child.tagName === 'ul' || child.tagName === 'ol'),
        )
      ) {
        return
      }
      const hits = options.ranges.filter((range) => start < range.end && end > range.start)
      if (hits.length === 0) return
      node.properties.dataHighlight = hits.some((range) => range.level === 'primary')
        ? 'primary'
        : 'secondary'
      return SKIP // do not double-mark descendants
    })
  }
}
