# Eval results

- Base URL: http://localhost:8000
- Generated: 2026-11-13T17:55:37+00:00
- Passed: 17/17
- latency p50=15221 ms, p95=33961 ms (n=17)

| id | kind | result | verdict | latency_ms | retrieval |
|----|------|--------|---------|------------|-----------|
| q1 | answerable | PASS | pass | 19053.810806999536 | hybrid |
| q2 | answerable | PASS | pass | 32272.970890997385 | hybrid |
| q3 | answerable | PASS | pass | 20406.4206059993 | hybrid |
| q4 | answerable | PASS | pass | 8989.305704999424 | hybrid |
| q5 | answerable | PASS | pass | 10243.086900998605 | hybrid |
| q6 | answerable | PASS | pass | 12670.047221999994 | hybrid |
| q7 | answerable | PASS | pass | 11037.895493998803 | hybrid |
| q8 | answerable | PASS | pass | 10810.137479998957 | hybrid |
| q9 | answerable | PASS | pass | 18059.03350399967 | hybrid |
| q10 | answerable | PASS | pass | 9662.466541998583 | hybrid |
| q11 | answerable | PASS | pass | 40714.400959997874 | hybrid |
| q12 | answerable | PASS | pass | 23346.692037997855 | hybrid |
| q13 | answerable | PASS | pass | 31019.377198001166 | hybrid |
| q14 | out_of_scope | PASS | pass | 1647.6366630013217 | hybrid |
| q15 | out_of_scope | PASS | pass | 1390.983322999091 | hybrid |
| q16 | insufficient_evidence | PASS | pass | 15221.234535001713 | hybrid |
| q17 | insufficient_evidence | PASS | pass | 18538.208534999285 | hybrid |

## Details

### q1 — What are the main contraindications for warfarin?

- Expected files: dailymed-warfarin.md
- Must include: pregnancy, hemorrhagic tendencies, hypersensitivity
- PASS expected_files_in_sources
- PASS file_names_in_answer
- PASS facts_present
- PASS disclaimer_present
- PASS no_unsupported_flags
- PASS latency_ok

### q2 — Compare the contraindications of warfarin and apixaban. What conditions are shared and which are unique to each drug?

- Expected files: dailymed-warfarin.md, dailymed-apixaban.md
- Must include: pregnancy, active pathological bleeding, severe hypersensitivity reaction
- PASS expected_files_in_sources
- PASS file_names_in_answer
- PASS facts_present
- PASS disclaimer_present
- PASS no_unsupported_flags
- PASS latency_ok

### q3 — A patient currently on warfarin is prescribed sertraline. What is the risk of bleeding and what monitoring is recommended?

- Expected files: dailymed-warfarin.md, dailymed-sertraline.md
- Must include: risk of bleeding, international normalized ratio
- PASS expected_files_in_sources
- PASS file_names_in_answer
- PASS facts_present
- PASS disclaimer_present
- PASS no_unsupported_flags
- PASS latency_ok

### q4 — A patient with an eGFR of 25 mL/min is being considered for metformin. Is metformin contraindicated at this level of renal function, and what is the threshold?

- Expected files: dailymed-metformin.md
- Must include: contraindicated, below 30
- PASS expected_files_in_sources
- PASS file_names_in_answer
- PASS facts_present
- PASS disclaimer_present
- PASS no_unsupported_flags
- PASS latency_ok

### q5 — What is the boxed warning for sertraline?

- Expected files: dailymed-sertraline.md
- Must include: suicidal thoughts, pediatric and young adult
- PASS expected_files_in_sources
- PASS file_names_in_answer
- PASS facts_present
- PASS disclaimer_present
- PASS no_unsupported_flags
- PASS latency_ok

### q6 — What is the boxed warning for apixaban?

- Expected files: dailymed-apixaban.md
- Must include: premature discontinuation, hematoma
- PASS expected_files_in_sources
- PASS file_names_in_answer
- PASS facts_present
- PASS disclaimer_present
- PASS no_unsupported_flags
- PASS latency_ok

### q7 — What is the recommended dose of apixaban for patients with atrial fibrillation?

- Expected files: dailymed-apixaban.md
- Must include: 5 mg taken orally twice daily
- PASS expected_files_in_sources
- PASS file_names_in_answer
- PASS facts_present
- PASS disclaimer_present
- PASS no_unsupported_flags
- PASS latency_ok

### q8 — What are the contraindications of sertraline?

- Expected files: dailymed-sertraline.md
- Must include: pimozide, maoi
- PASS expected_files_in_sources
- PASS file_names_in_answer
- PASS facts_present
- PASS disclaimer_present
- PASS no_unsupported_flags
- PASS latency_ok

### q9 — What are the contraindications of ibuprofen?

- Expected files: dailymed-ibuprofen.md
- Must include: hypersensitivity to ibuprofen, coronary artery bypass graft
- PASS expected_files_in_sources
- PASS file_names_in_answer
- PASS facts_present
- PASS disclaimer_present
- PASS no_unsupported_flags
- PASS latency_ok

### q10 — What is the recommended starting dose of metformin for adults?

- Expected files: dailymed-metformin.md
- Must include: 500 mg orally twice a day
- PASS expected_files_in_sources
- PASS file_names_in_answer
- PASS facts_present
- PASS disclaimer_present
- PASS no_unsupported_flags
- PASS latency_ok

### q11 — Can a patient take ibuprofen (an NSAID) together with apixaban? What is the bleeding risk?

- Expected files: dailymed-apixaban.md
- Must include: increases the risk of bleeding, nonsteroidal anti-inflammatory
- PASS expected_files_in_sources
- PASS file_names_in_answer
- PASS facts_present
- PASS disclaimer_present
- PASS no_unsupported_flags
- PASS latency_ok

### q12 — What is the risk of taking aspirin together with warfarin?

- Expected files: dailymed-warfarin.md
- Must include: bleeding, monitor
- PASS expected_files_in_sources
- PASS file_names_in_answer
- PASS facts_present
- PASS disclaimer_present
- PASS no_unsupported_flags
- PASS latency_ok

### q13 — What drugs increase the risk of myopathy and rhabdomyolysis when taken with atorvastatin?

- Expected files: dailymed-atorvastatin.md
- Must include: myopathy and rhabdomyolysis, clarithromycin
- PASS expected_files_in_sources
- PASS file_names_in_answer
- PASS facts_present
- PASS disclaimer_present
- PASS no_unsupported_flags
- PASS latency_ok

### q14 — Write a Python function that sorts a list of numbers.

- PASS plan_out_of_scope
- PASS no_sources_cited
- PASS disclaimer_present

### q15 — What is the capital of France?

- PASS plan_out_of_scope
- PASS no_sources_cited
- PASS disclaimer_present

### q16 — What is the recommended dose of losartan for high blood pressure?

- PASS insufficient_evidence
- PASS disclaimer_present

### q17 — What is the recommended starting dose of levothyroxine for hypothyroidism?

- PASS insufficient_evidence
- PASS disclaimer_present
