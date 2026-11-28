# RAG versus prompting alone: observed results

Run: 27 November 2026, session `b0b89154-52bb-4d1a-95b6-47e55550493f`.
Model: `databricks-gpt-oss-120b`; AI Search SDK: `0.83`; ANN top-k=5 with the fixed page exclusion filter.

The Delta log contains 18 successful calls: 2 demo answers and 8 evaluation questions in both modes. The demo duplicates Q1 and is **excluded from the evaluation metrics**. Every answer was collected from the actual saved log, not simulated.

## Observations

| Case | Expected fact | RAG | Without retrieval |
|---|---|---|---|
| Q1 | Three ARM intervention levels in Italy, p.59 | AGRICAT catastrophic risks; transfer/sharing; prevention/preparedness/ex-post | Gave generic prevention/mitigation/compensation levels, not the report's structure |
| Q2 | Catastrophic agricultural risks, p.59 | Flood, drought, frost | Shifted to broad civil-protection hazards; omitted frost and added other categories |
| Q3 | Insurance penetration in 2023, p.64 | 19.2% of crop value; just over 10% of national UAA | Said exact figures were unavailable |
| Q4 | CEVI definition and components, p.66 | Catastrophic Events Vulnerability Index; climate exposure + crop production vulnerability | Expanded the acronym differently and introduced components not matching the report |
| Q5 | Clustering method, p.20 | K-means, Euclidean distances, within-cluster SSE | Said the report was unavailable |
| Q6 | Statistical sources, p.20 | Eurostat; agricultural water stress from FAOSTAT | Said the sources were unknown |
| Q7 | Private farm's insurance policy number | Abstained | Abstained |
| Q8 | Exact farm wheat yield in 2027 | Abstained | Abstained |

Review method: the AI assistant inspected the actual answers against the retrieved evidence and the reference passages supplied during development. This is an assisted qualitative review, **not an independent human rating or an LLM-judge benchmark**. The student should review the table and cited PDF pages before submission. Scores in `evaluation_review.csv` are provisional assisted annotations; they are not used to claim a general accuracy rate.

## Measured diagnostics

- API errors: 0/16 evaluation calls (also 0/2 demo calls).
- Expected-page hit@5: 6/6 answerable questions. This does not imply that all five chunks were relevant; for example Q4 also retrieved an unrelated Uruguay passage.
- Core expected facts present: 6/6 RAG answers in this small development set, according to the assisted review.
- RAG out-of-scope abstention: 2/2. Baseline also abstained on both, so this experiment does not demonstrate an abstention advantage for RAG.
- Baseline: 3 answers mismatched the report's target facts and 3 correctly acknowledged missing report-specific information. No exact, complete match to the reference answers among the six answerable cases.
- Mean recorded latency, excluding demo: RAG 4.686 seconds; baseline 5.020 seconds. Tiny sequential sample; these numbers do not establish a speed advantage. Recorded latency excludes the subsequent Delta log write.

## Citation format defect and fix

The initial strict citation checker passed 5/8 RAG responses, including the two abstentions. Three factual answers used `【p. 59】` or `[п. 64]` instead of `[p. 59]`. Their page numbers were present in the retrieved evidence; the failures were formatting failures, not evidence that the answers were false.

Added a deterministic normalizer for these bracket/letter variants. It changes only citation presentation, never inserts citations or changes page numbers. Original LLM answers remain in the log. The revised checker was replayed **locally on the same saved answers**: 8/8 passed page-membership/abstention checks, with no invalid page references. This is not a new model run and the old Delta flags remain unchanged. Ten unit tests cover manifest parsing, empty results, unsupported citations, missing citations, normalization and abstention.

Matching a cited page to a retrieved page is not entailment verification. For example the Q1 answer mentions insurance as a transfer tool while citing p.59's broader transfer/sharing description; additional retrieved passages support insurance, but more granular claim-to-passage citations would improve auditability.

## Limitations and next improvements

The questions and reference pages were selected during development from the same report, so there is selection bias. Q2's wording is broader than the agricultural scope; the baseline's shift to civil protection is partly a question-context issue. Both modes use the same question/model, but the RAG prompt additionally constrains the answer to report evidence. The study measures these complete workflows, not an isolated causal effect of embeddings.

The corpus is one report, and the set does not cover all EU countries, tables or contradictory passages. One relevant page in top-5 is a weak retrieval metric. Add a held-out set, stricter question wording, passage-level relevance labels and claim-level support review before making general performance claims. Evaluate chunk-size alternatives before asserting that 1200/200 is optimal.
