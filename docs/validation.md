# Validation record

Updated 2026-09-15. This file separates verified behavior from pending integration checks.

## Passed

- Isolated Linux Python 3.11 policy environment installed; `pip check` reports no broken requirements. Tested versions are frozen in `requirements-policy.lock.txt`. The initial seven CPU tests also passed in this server environment.
- Real OpenWAM GPU inference: model load 68.17 s, two proposals 1.222 s and 0.561 s, peak PyTorch reserved memory 23.60 GiB. Both proposals have raw shape 32×20 and native shape 32×16; the observed-pose coordinate round trip passes. The tested GPU reports 48,500 MiB total usable memory, so this is not evidence for a stock 24 GB 4090. See [offline policy evidence](evidence/offline-policy.json).

- All 60 frozen scene cases and support-trajectory hashes match the earlier π0.5 panel; native simulator source files are identical. Only policy-seed metadata and panel identity differ.
- Codex 0.153.4 native command preflight passed inside the isolated container with zero model turns.

- Native Isaac simulation: one EEF16 command requested a 5 mm lift and produced 4.474 mm measured motion; one subsequent bounded DLS/joint14 command executed. All three cameras were 640×480 RGB, control dt 0.04 s. Base calibration and current FK passed; see [native smoke evidence](evidence/native-smoke.json). This check made zero model calls and is not a task-success result.

- Released checkpoint downloaded at the pinned Hugging Face revision; all nine files passed size and SHA-256 verification, including the 24,813,767,464-byte weight file.
- GitHub Actions CPU contracts passed on Python 3.11.

- Eight CPU regression tests: unchanged gate/correction implementation; 5 cm correction and 15-step prefix limits; EEF16 native command keys; measured-base calibration mismatch rejection; fresh policy identity/sequence validation and raw EEF20/observation recording; exactly-once simulator stepping and native termination with a test environment; lossless observation recording at ZIP levels 1 and 6; mixed EEF16/joint14 video-timeline attribution and gripper indexing; OpenWAM decision-receipt method/H32 metadata.
- Runtime patch applies to the exact pinned GPT-as-Policy revision. Both source dependencies are required to be clean and at their pinned commits. Generated runtime content is hashed and checked on reuse.
- Adapter Python compilation and launch-script shell syntax checks.

CPU tests use protocol/environment test doubles where hardware is unnecessary. They do not prove model loading, native Isaac IK, task success or GPU capacity.

## End-to-end smoke

A real `gpt-6-astra` / `xhigh` + OpenWAM + native RoboDojo run completed its two-decision budget: two fresh proposals, 30 student control steps, 31 original observations and 31 video frames. Artifact verification passed and owned processes/ports were released. Controller time was 113.09 s; total startup-through-finalization time was 212.32 s. One-second whole-GPU samples peaked at 33,716 MiB (32.93 GiB). See [integration evidence](evidence/astra-openwam-smoke.json).

The native outcome is `budget_censored`, with `valid_for_success_rate=false`. Astra accepted both prefixes, so this smoke did not exercise an Astra-requested correction; the separate native smoke validates one bounded DLS correction. The immutable smoke snapshot also exposed a legacy π0.5 default label in decision receipt logs; run/batch/policy identities were correct. The final source fixes only that receipt label and H32 prefix metadata, with a regression test; the GPU smoke was not repeated for that recording-only change.

## Not yet measured

Full native episodes, full-panel success rate, and multi-episode OpenWAM concurrency have not been evaluated. No full-panel score or task-success claim is made. The existing Astra + π0.5 measurement is a different experiment and is not OpenWAM validation.

## Infrastructure fixes during validation

DeepSpeed metadata needs the CUDA compiler even with training extensions disabled; setup reuses the existing container toolkit. Its newer glibc initially selected a host-incompatible cryptography wheel; setup now selects the same version’s compatible wheel on the host. The first end-to-end launch stopped before model startup because persistent Codex trust metadata referred to the baseline container root. The launcher now preserves that in-container path while mounting the separate new runtime directory. The terminal, zero-action failed launch is retained under `diagnostics/pre-runtime-path-fix/`; its obsolete path metadata is not scanned as a benchmark attempt. A subsequent preflight stopped on that obsolete ledger entry before launching a model.
