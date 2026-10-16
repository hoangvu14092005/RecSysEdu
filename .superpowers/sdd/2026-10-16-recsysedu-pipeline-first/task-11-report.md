# Task 11 — Real pilot and P0 freeze

Status: DONE — real BPR search, five-alpha/four-model validation, independent audit and P0 config freeze complete. Test remains unopened.

Evidence commit: `ae8958107820cb0c25a56d1cf09f4c62982952e7`.
Only five small files committed: final_experiments config, dataset report,
validation report, public-safe core manifest and current todo. Worktree clean.

Worktree: `C:\Users\Vu\.codex\worktrees\pipeline-first\RecSysEdu`.
Base: `e7663cdcc45cdb02344d5fc54ae37de608b504fb`.
Python: `D:\VuLapTrinh2\RecSysEdu\.venv\Scripts\python.exe`.
Every CLI subprocess has explicit worktree `src` PYTHONPATH. Raw is read from
the primary checkout, not copied, changed or committed. No subagents spawned.

## Scope correction and review fix

The prior adapter called `Trainer.fit(valid_data=None)`, which disables
validation early stopping. Parent explicitly required the approved Task 11
behavior rather than a fixed-budget-only deviation.

- `f8ca95b` adds optional `validation_early_stopping` and positive `stopping_step`.
  A minimal RecBole Trainer subclass receives the exact loaded validation
  Dataset and calculates warm NDCG@10 using shared project rank/metric functions,
  train candidate universe, source-ID tie break and train-only seen mask.
  Cold valid targets are excluded; test targets never enter that calculation.
  It preserves upstream train-only negative sampler and exact split checks.
- Best tensor state is cloned at every upstream >= best-score update and restored
  before tensor-only checkpoint publication. Manifest records requested/completed
  epochs, last best epoch, best valid NDCG and the complete epoch score history.
  Upstream stopping_step=2 means stop after three strict worsening evaluations;
  exact ties reset its counter. Existing fixed-budget behavior remains available.
- TDD: two missing-symbol failures observed before implementation. Controlled
  real Trainer regression proves early stop and bit-exact restoration of first
  best epoch; another test compares validator NDCG to independently accumulated
  shared ranking results. Runner integration compares saved checkpoint metric
  with best epoch NDCG. Full suite 248 passed, Ruff passed.
- Independent review found omitted default flags were not bound into effective
  config/artifact checks. `e101b67` always normalizes/hashes defaults False/3 and
  verifies them; missing legacy manifest fields are interpreted False/3.
  Regression first failed DID NOT RAISE, then passed. Full suite **249 passed,
  64 upstream warnings, 36.92 seconds**; Ruff and git diff --check passed.
  Explicit pilot True/2 settings remained unchanged during this correction.

## Data evidence already verified

- Both original hashes match recorded raw manifest and official download links.
  Upstream repository HEAD: `ff6fb71304b4eaadde51956b7977d49c72a3ac1e`.
  GitHub source lists GPL-3.0 for repo; a separate dataset license was not
  established, so no learner-level artifacts are being published.
- Full 3,330,294 users scanned; 680,131 eligible; exact seed-selected 10,000 users,
  126,827 interactions. 35 boundary-tie users removed, 9,965 temporal users,
  106,717 train rows, 9,909 warm valid users, 2,586 train candidate courses.
- Valid cold=56; test cold=107. Test counts/hashes/split membership are necessary
  data integrity checks, not test metric evaluation; no test scoring command run.
- Independent pandas disjoint-pair, strict train<valid<test time, and exact
  train universe checks passed for all 9,965 users.
- Prepare 35.66 s; independent repeat 37.90 s produced identical complete
  dataset manifest and all output hashes. Repeat sampled process-tree RSS peak
  640,491,520 bytes; split 1.30 s / 250,871,808 bytes.
  Initial prepare measured launcher only; its RAM reading is discarded.
- Public-safe counts, sizes, hashes, timezone assumption and commands are in
  `results/pilot/dataset_report.md`; full manifests stay ignored/local.

## Completed bounded model search

Predeclared 3 configs (maximum allowed 6), seed17, CPU, batch2048, at most
10 epochs, validation stopping_step2: (embedding32, lr.001),
(embedding64, lr.001), (embedding32, lr.01). All attempts/failures are persisted
in ignored `results/local/bpr-search.json` and individual logs/measurements.
No model selection uses test. OMP_NUM_THREADS, MKL_NUM_THREADS and
OPENBLAS_NUM_THREADS are 2 for measured CLI subprocesses.

Standalone valid baseline runs:

| Model | NDCG@10 | HitRate/Recall@10 | Precision@10 | Coverage@10 | CLI seconds |
| --- | ---: | ---: | ---: | ---: | ---: |
| MostPopular | 0.0532997424 | 0.0896155011 | 0.0089615501 | 0.0123743233 | 19.72 |
| Content | 0.0823037349 | 0.1347260067 | 0.0134726007 | 0.9226604795 | 206.31 |

Content: 400,950 char n-grams, 859,171 sparse nonzeros, no empty train item
vectors; none of the 9,909 users needed fallback. Baselines share split,
cohort, universe, seen/profile/tie policy; final compatible four-model batch
will be the freeze authority.

## Local artifacts and commands

Ignored helpers:
- `results/local/task11_measure.py`: CLI subprocess wrapper, elapsed wall time,
  process-tree RSS samples every0.2s, complete stdout/stderr log.
- `results/local/task11_search.py`: declared 3-config sequential valid search.
- `results/local/task11_audit.py`: final hash/compatibility/seen/ranking/alpha
  endpoint/metric/checkpoint reload/freeze independent audit.

Current local roots:
- `data/processed/mooccubex-pilot-v1/` (authoritative dataset).
- `data/processed/mooccubex-pilot-v1-repeat/` (repeat evidence).
- `data/splits/mooccubex-pilot-v1-split-v1/`.
- `results/local/pilot-search/`.

At integration, preserve/copy these ignored artifacts into the primary
checkout matching relative paths before archiving this worktree. Raw is already
in primary `data/raw/`. Frozen manifests may retain their original absolute
output_root; do not rewrite immutable manifests, as actual-location protection
already handles copied/moved batches.

## Final validation and freeze

All three BPR trials completed (no failed/omitted trial). Valid NDCG@10:
32/.001=0.057457486599153645;64/.001=0.06134094543097583;
32/.01=0.0774493614401512. All best epochs10/10; early stopping enabled
but none triggered before the declared10-epoch budget. Selected bpr-3 is
the exact checkpoint `c4dbd2d88e71689b1d447f314fe6b9dc1a90af95499d2cafdba5eec03b36720a`.

Final valid batch published atomically at:
`C:\Users\Vu\.codex\worktrees\pipeline-first\RecSysEdu\results\local\pilot-final\valid\valid-2e93583494064297adaa556b9bc21d64`.
No partial batch promoted. All five alpha trials measured:
0=0.08230373486780361;
.25=0.10850833307518327;
.5=0.10405136569235414;
.75=0.09288478060726162;
1=0.0774493614401512.
Winner alpha=.25. Four final compatible runs:

| Model | NDCG@10 | HitRate/Recall@10 | Precision@10 | Coverage@10 |
| --- | ---: | ---: | ---: | ---: |
| MostPopular | .053299742395911856 | .08961550105964275 | .008961550105964198 | .01237432327919567 |
| Content | .08230373486780361 | .13472600666061157 | .013472600666060824 | .922660479505027 |
| BPR | .0774493614401512 | .13957008779897062 | .013957008779896703 | .6774941995359629 |
| Hybrid .25 | .10850833307518327 | .17822181854879401 | .017822181854878823 | .8364269141531323 |

Complete CLI elapsed1526.8460488s, sampled process-tree RSS403980288 bytes.
This is development-machine wall time with other tasks/tests running, not an
isolated hardware performance benchmark. Exact measurements/logs persisted.

Freeze config sets frozen:true and validation_dir to this batch, with:
- Dataset: `215b235068a4282a49b02ab0c0ac65608f096828d1fc97ac6c1a30b0a936720c`.
- Split: `7285739e66981088817fd2c11419caaf36f2cf4f197798403468cd989f263617`.
- Effective config: `7e895cc5d88e203cf20c597c6ff349d16b5266910d148108ca4a3f1c22f603cc`.
- Exact validation experiment manifest SHA256:
  `379b3ae18de0b2a3859f705be5ce3727284d29fa4a8ddab1326982ba597d3baf`.

Independent final audit PASSED:
- All experiment output hashes and each run output hash checked.
- Four models and all alpha reports share dataset/split/protocol/config/seed,
  cohort9909/universe2586, k10, candidate/profile/seen/tie/history policies
  and split-manifest hash.
- All eight distinct persisted ranking runs cover9909 users, exactly10 unique
  courses, finite scores, continuous ranks, correct score/id tie ordering,
  zero train-seen violations, no candidate outside train universe.
- Recomputed each user's NDCG/hit/recall/precision independently from targets
  and ordered recommendations; compared every Parquet row and aggregate,
  tolerance absolute1e-12. Coverage recomputed by union, not mean of per-user
  coverage. Final Hybrid aliases alpha.25, so audit names include that alias.
- Alpha0 exact ranking match Content; alpha1 exact ranking match BPR, all9909 users.
- Best saved BPR checkpoint NDCG matches best validation epoch; two reloads
  create identical NumPy score arrays for5 full-candidate user cases.
- Entire user/item embedding arrays match independently restored RecBole
  tensors bit-exact. Five full-candidate cases match upstream predict and
  float64 oracle within documented float32 tolerance; see recovery notes.
- Effective config hash and exact freeze dict verified; `_frozen_validation`
  guard succeeds with distinct planned test root, without test scoring.
- Test output root does not exist. Test not evaluated in Task11.

Local audit results:
`results/local/final-validation-audit.{json,log}`;
`results/local/data-audit-resume.json`;
`results/local/checkpoint-reload.log`.
Local core summary: `artifacts/core_manifest.json`; public-safe exact summary
copy committed at `results/pilot/core_manifest.json` (2838 bytes, no learner
IDs or local paths). Other committed reports6324 and~9800 bytes. Scanned all
five staged files for learner IDs, absolute local paths and secret assignments;
no matches. Complete batch46 files/141072182 bytes remains ignored.

Latest full suite, including Task12:262 passed,64 upstream warnings,38.98s;
Ruff and git diff --check passed. Log `results/local/task11-final-pytest.log`.
No production fixes in this evidence commit; early stopping fixes were separately
committed/reviewed as f8ca95b/e101b67. Batch records e101b67 revision and git_dirty
true because config/reports were drafts; no uncommitted P0 source at launch.

## Exact local handoff inventory

Preserve/copy from worktree to the primary checkout with SAME relative paths
before archiving the managed worktree. Do not rewrite immutable manifests or
their recorded absolute output_root fields; the code guards actual moved batch
locations as well as recorded output roots.

Required for frozen test/snapshot:
- `data/processed/mooccubex-pilot-v1/` (dataset manifest and all4 Parquet outputs).
- `data/splits/mooccubex-pilot-v1-split-v1/` (manifest and all6 Parquet outputs).
- `results/local/pilot-final/valid/valid-2e93583494064297adaa556b9bc21d64/`
  ENTIRE directory,46 files/141072182 bytes; includes content features,
  checkpoint/ID maps, all alpha/component rankings, snapshot_inputs and manifests.

Required to repeat retained selected-BPR validation from committed config:
- `results/local/pilot-search/bpr-3/valid-cbcf720e67144f10a735e06b0a717763/`
  (at least artifacts/bpr subtree; preserving entire batch is preferable).

Preserve research/reproducibility evidence:
- `data/processed/mooccubex-pilot-v1-repeat/`.
- Entire `results/local/pilot-search/` (all3 trials and standalone baselines).
- `results/local/bpr-search.json`, `bpr-[1-3].{yaml,log,measurement.json}`,
  `content.{log,measurement.json}`, `popularity.{log,measurement.json}`,
  `prepare*`, `split.{log,measurement.json}`.
- `results/local/final-valid-resume.{log,measurement.json}`;
  `task11_measure.py`, `task11_search.py`, `task11_audit.py`, `task11_reload.py`,
  `task11_data_audit.py` and audit/test result files named above.
- `artifacts/core_manifest.json` (also has public-safe committed copy).
- Original abandoned stage may be retained as interrupted-run evidence; it is
  NOT required for test/snapshot and must never be consumed as complete.
Raw already lives in primary `D:\VuLapTrinh2\RecSysEdu\data\raw\`.

## Remaining work and limitations

Task11 complete. Only validation-only P0 freeze achieved: not whole-product
acceptance. Task13 still must run frozen test, export real snapshot, inspect in
browser, clean-environment reproduction and final handoff. One pilot/seed and
3-config/10-epoch search do not prove convergence, general improvement or learning
benefit. P1 real graph remains not run/insufficient sources (Task12).

## Historical recovery checkpoint (12:06 local; now completed)

Prior process ended without publishing an experiment manifest. Abandoned stage
`results/local/pilot-final/valid/.experiments-evvrly4a/valid-07ce1313212c40ad8ebc8342880d5708/`
contains all three components but only an incomplete alpha0 run; it is preserved
as interrupted evidence and must not be used as a complete validation batch.

All three BPR trials completed successfully. Winner is bpr-3, embedding32,
learning_rate0.01, best epoch10/10, valid NDCG@10 0.0774493614401512.
Its checkpoint is reused for resumed final validation without retraining.

Resumed command (worktree cwd):
`python results/local/task11_measure.py final-valid-resume experiments --split valid --config configs/final_experiments.yaml`.
Wrapper process30096/43616; child24020/42608. New stage:
`results/local/pilot-final/valid/.experiments-_4b93c9t/valid-2e93583494064297adaa556b9bc21d64/`.
Component runs completed, alpha0 began12:05:18; no test scoring.
Log and measurement: `results/local/final-valid-resume.{log,measurement.json}`.

Fresh independent `task11_data_audit.py` passed raw hashes, prepare repeat
manifest/all output exactness, split hashes, disjoint pairs, strict temporal
order for9965 users and exact train universe. Local output:
`results/local/data-audit-resume.json`.
Checkpoint audit `task11_reload.py` compares5 users×2586 candidates with
restored upstream BPR.predict and independent float64 sum. NumPy/Torch float32
max difference9.536743e-7, float64 oracle max error7.018903e-7; all full rankings
equal at rtol1e-6/atol2e-6. Initial overly tight atol1e-7 failed near zero;
diagnosis is different float32 reduction trees, no production source change.
`results/local/checkpoint-reload.log` records success. Two NumPy reloads must
also match bit-exact in final audit.

Fresh full suite249 passed,64 upstream warnings,38.78s; Ruff and diff --check
passed. Saved `results/local/task11-pytest.log`.
