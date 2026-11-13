// Augment `hast` so the cross-highlight and citation plugins can carry the
// `data-highlight` / `data-citation-id` attributes without casts. These are
// rendered as `data-*` HTML attributes by hast-util-to-jsx-runtime.
import 'hast'

declare module 'hast' {
  interface Properties {
    dataHighlight?: 'primary' | 'secondary'
    dataCitationId?: string
  }
}
