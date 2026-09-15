# Validation record

Updated 2026-09-15. This file separates verified behavior from pending integration checks.

## Passed

- Six CPU regression tests: unchanged gate/correction implementation; 5 cm correction and 15-step prefix limits; EEF16 native command keys; measured-base calibration mismatch rejection; fresh policy identity/sequence validation and raw EEF20/observation recording; exactly-once simulator stepping and native termination with a test environment; lossless observation recording at ZIP levels 1 and 6.
- Runtime patch applies to the exact pinned GPT-as-Policy revision. Both source dependencies are required to be clean and at their pinned commits. Generated runtime content is hashed and checked on reuse.
- Adapter Python compilation and launch-script shell syntax checks.

CPU tests use protocol/environment test doubles where hardware is unnecessary. They do not prove model loading, native Isaac IK, task success or GPU capacity.

## Pending on the deployment server

- Finish isolated Python 3.11 / PyTorch 2.7.1 CUDA 12.8 installation and `pip check`.
- Finish downloading and SHA-256 verifying the released 24.8 GB checkpoint.
- Native simulator EEF execution and calibration check.
- Two real GPU policy proposals, coordinate round trip, latency and memory measurement.
- Short Astra + OpenWAM + RoboDojo smoke episode and artifact verification.

No full-panel score or end-to-end success claim is made until corresponding evidence is recorded here. The existing Astra + π0.5 measurement is a different experiment and is not OpenWAM validation.
