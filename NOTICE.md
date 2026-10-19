# NOTICE

This repository contains task text and derived DAG decompositions from **CRMArena-Pro**
(Huang et al., 2025; Salesforce AI Research), released under the Creative Commons Attribution-NonCommercial 4.0
International licence (CC BY-NC 4.0) for research purposes.

- Attribution: CRMArena-Pro, Huang et al. (2025), Salesforce AI Research.
- Source: CRMArena-Pro benchmark (Salesforce AI Research), https://github.com/SalesforceAIResearch/CRMArena
- Licence of the source material: CC BY-NC 4.0, https://creativecommons.org/licenses/by-nc/4.0/
- What is included here: the model was fitted on a subset of 22 CRMArena-Pro B2C tasks plus 2 author-designed custom
  tasks. The repository contains the task description and stored DAG of 3 CRMArena-Pro tasks (89, 2056, 722) and of
  custom task 900002 (`data/v1_examples.json`); the task ids and categories of all 24 tasks (`data/bucket_evidence.json`);
  and aggregate per-architecture quality and cost results (`data/bucket_model.json`).
- Changes made: a subset of 22 CRMArena-Pro tasks was selected and 2 custom tasks were added; DAG decompositions were
  added for all of them (stored in `data/`); the tasks were benchmarked with three agent
  architectures, and summarised into a width-only Bayesian model. Additional, non-benchmark example requests and their
  LLM-generated decompositions are in `data/v2_recorded_examples.json`.
- Use: **non-commercial academic use only**, consistent with CC BY-NC 4.0. This repository is not affiliated with or
  endorsed by Salesforce.
