# GTM Agent Questions

This directory contains the source question fixtures for the GTM Agent benchmark.

The full workload is:

- 350 core questions: seven phase banks with 50 questions each.
- 140 variation questions: seven phase variation banks with 20 questions each.
- 490 total questions.

Use `tools/import_gtm_question_banks.py` to import the source fixtures from a local ANIP checkout:

```bash
./tools/import_gtm_question_banks.py --anip-root /path/to/anip
```

Generated files:

- `core-350/phaseN-question-bank.json`: copied source phase banks.
- `variation-140-v3/phaseN-variation-bank-20.json`: copied source variation banks.
- `question-bank-manifest.json`: source provenance and counts.
- `gtm-490-question-bank.json`: normalized benchmark input across all 490 questions.

The normalized file is the stable input for benchmark runners. Historical run outputs do not belong here; they belong under `reports/`.
