# Evaluation records

The authoritative five-question experiment and its separate Q3 HYBRID follow-up are recorded in `notebooks/06_evaluation.py` and the existing `qa_evaluation` table. Its conclusions are historical: the refactored shared prompt has not been rerun.

The separate, older AI-generated eight-question experiment is preserved unchanged in [historical/agent-eight-question-run/EVALUATION.md](historical/agent-eight-question-run/EVALUATION.md), alongside its original cases, responses and assisted review. Those results use a different question set and the legacy `rag_runs` log; they must not be combined with the five-question experiment.

The current workflow appends to `qa_log` and `qa_evaluation` without changing their schemas. Full prompts and unique run/evaluation IDs distinguish future experiments. Citation diagnostics check formatting and page membership, not factual entailment.

Final narrative and deployment evidence will be updated after the approved CI/CD run.
