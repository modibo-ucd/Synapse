export interface ExampleQuestion {
  id: string
  text: string
}

export const EXAMPLE_QUESTIONS: ExampleQuestion[] = [
  { id: 'ex1', text: 'What are the main contraindications for warfarin?' },
  {
    id: 'ex2',
    text: 'Compare the contraindications of warfarin and apixaban. What conditions are shared and which are unique to each drug?',
  },
  {
    id: 'ex3',
    text: 'A patient currently on warfarin is prescribed sertraline. What is the risk of bleeding and what monitoring is recommended?',
  },
  {
    id: 'ex4',
    text: 'A patient with an eGFR of 25 mL/min is being considered for metformin. Is metformin contraindicated at this level of renal function, and what is the threshold?',
  },
]
