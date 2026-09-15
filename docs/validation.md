# Validation record

Updated 2026-09-15. This file separates verified behavior from pending integration checks.

## Passed

- All 60 frozen scene cases and support-trajectory hashes match the earlier π0.5 panel; native simulator source files are identical. Only policy-seed metadata and panel identity differ.
- Codex 0.153.4 native command preflight passed inside the isolated container with zero model turns.

- Native Isaac simulation: one EEF16 command requested a 5 mm lift and produced 4.474 mm measured motion; one subsequent bounded DLS/joint14 command executed. All three cameras were 640×480 RGB, control dt 0.04 s. Base calibration and current FK passed; see [native smoke evidence](evidence/native-smoke.json). This check made zero model calls and is not a task-success result.

- Released checkpoint downloaded at the pinned Hugging Face revision; all nine files passed size and SHA-256 verification, including the 24,813,767,464-byte weight file.
- GitHub Actions CPU contracts passed on Python 3.11.

- Seven CPU regression tests: unchanged gate/correction implementation; 5 cm correction and 15-step prefix limits; EEF16 native command keys; measured-base calibration mismatch rejection; fresh policy identity/sequence validation and raw EEF20/observation recording; exactly-once simulator stepping and native termination with a test environment; lossless observation recording at ZIP levels 1 and 6; mixed EEF16/joint14 video-timeline attribution and gripper indexing.
- Runtime patch applies to the exact pinned GPT-as-Policy revision. Both source dependencies are required to be clean and at their pinned commits. Generated runtime content is hashed and checked on reuse.
- Adapter Python compilation and launch-script shell syntax checks.

CPU tests use protocol/environment test doubles where hardware is unnecessary. They do not prove model loading, native Isaac IK, task success or GPU capacity.

## Pending on the deployment server

- Finish isolated Python 3.11 / PyTorch 2.7.1 CUDA 12.8 installation and `pip check`.
- Two real GPU policy proposals, coordinate round trip, latency and memory measurement.
- Short Astra + OpenWAM + RoboDojo smoke episode and artifact verification.

No full-panel score or end-to-end success claim is made until corresponding evidence is recorded here. The existing Astra + π0.5 measurement is a different experiment and is not OpenWAM validation.
