import { MEDICAL_DISCLAIMER } from '../lib/disclaimer'

interface DisclaimerProps {
  text?: string
}

export function Disclaimer({ text = MEDICAL_DISCLAIMER }: DisclaimerProps) {
  return (
    <p data-testid="medical-disclaimer" className="text-xs leading-relaxed text-ink-muted">
      <span className="font-semibold text-ink">Medical disclaimer:</span> {text}
    </p>
  )
}
