import { EXAMPLE_QUESTIONS } from '../../lib/examples'

interface ExampleQuestionsProps {
  onSelect: (question: string) => void
}

export function ExampleQuestions({ onSelect }: ExampleQuestionsProps) {
  return (
    <div data-testid="example-questions" className="mt-8">
      <h2 className="text-sm font-medium text-slate-600">Try an example question</h2>
      <ul className="mt-3 space-y-2">
        {EXAMPLE_QUESTIONS.map((example) => (
          <li key={example.id}>
            <button
              type="button"
              data-testid={`example-${example.id}`}
              onClick={() => onSelect(example.text)}
              className="w-full rounded-md border border-slate-200 bg-white px-3 py-2 text-left text-sm text-slate-700 hover:border-brand-300 hover:bg-brand-50 focus:outline-none focus:ring-2 focus:ring-brand-500/40"
            >
              {example.text}
            </button>
          </li>
        ))}
      </ul>
    </div>
  )
}
