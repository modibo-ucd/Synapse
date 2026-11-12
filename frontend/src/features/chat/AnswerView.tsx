import { ComparisonMatrix } from '../../components/ComparisonMatrix'
import { EgfrCalculator } from '../../components/EgfrCalculator'
import { Markdown } from '../../components/Markdown'
import { ReviewFlags } from '../../components/ReviewFlags'
import { SourcesList } from '../../components/SourcesList'
import type { AskResponse } from '../../types/api'

interface AnswerViewProps {
  answer: AskResponse
}

export function AnswerView({ answer }: AnswerViewProps) {
  return (
    <div
      data-testid="answer"
      aria-live="polite"
      className="mt-6 rounded-lg border border-slate-200 bg-white p-4 shadow-sm"
    >
      <h2 className="mb-2 text-base font-semibold text-slate-800">Answer</h2>
      <Markdown citations={answer.citations}>{answer.answer}</Markdown>
      {answer.comparison && (
        <ComparisonMatrix comparison={answer.comparison} citations={answer.citations} />
      )}
      {answer.widgets?.map((widget) => (
        <EgfrCalculator key={widget.type} widget={widget} citations={answer.citations} />
      ))}
      <ReviewFlags review={answer.review} />
      <SourcesList sources={answer.sources} citations={answer.citations} />
    </div>
  )
}
