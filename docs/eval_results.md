# Eval results

- Base URL: http://localhost:8000
- Generated: 2026-11-12T23:02:52+00:00
- Passed: 16/17
- latency p50=13089 ms, p95=30629 ms (n=17)

| id | kind | result | verdict | latency_ms | retrieval |
|----|------|--------|---------|------------|-----------|
| q1 | answerable | PASS | pass | 13505.603694000456 | hybrid |
| q2 | answerable | PASS | pass | 22957.146838998597 | hybrid |
| q3 | answerable | PASS | pass | 23368.637755000236 | hybrid |
| q4 | answerable | PASS | pass | 8661.312569000074 | hybrid |
| q5 | answerable | PASS | pass | 9398.875834000137 | hybrid |
| q6 | answerable | PASS | pass | 12042.09352900034 | hybrid |
| q7 | answerable | PASS | pass | 12435.690604999763 | hybrid |
| q8 | answerable | PASS | pass | 13088.753202999214 | hybrid |
| q9 | answerable | PASS | pass | 13644.737188998988 | hybrid |
| q10 | answerable | PASS | pass | 7378.698717999214 | hybrid |
| q11 | answerable | PASS | pass | 32104.258966999623 | hybrid |
| q12 | answerable | FAIL | pass | 30259.85679600126 | hybrid |
| q13 | answerable | PASS | pass | 19458.374015999652 | hybrid |
| q14 | out_of_scope | PASS | pass | 1099.0578639994055 | hybrid |
| q15 | out_of_scope | PASS | pass | 1358.5519730004307 | hybrid |
| q16 | insufficient_evidence | PASS | pass | 11265.393398000015 | hybrid |
| q17 | insufficient_evidence | PASS | pass | 22602.23532499913 | hybrid |

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
- FAIL facts_present
- PASS disclaimer_present
- PASS no_unsupported_flags
- PASS latency_ok
- Missing (missing_facts): bleeding

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
