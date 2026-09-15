# Third-party notices

- **GPT-as-Policy**, copyright (c) 2026 Yu-Mool Shu and Lipxin Zheng, MIT. The patch in `patches/openwam-runtime.patch` modifies this source; generated runtime code preserves its original module notices. Full license: `licenses/GPT-as-Policy-MIT.txt`. Source and revision: `configs/pins.json`.
- **OpenWAM**, OpenWAM Contributors, Apache-2.0. Used as a separately fetched dependency. This integration imports its canonical frame, pose, representation, preprocessing and inference helpers. Full license: `licenses/OpenWAM-Apache-2.0.txt`. No checkpoint weights are redistributed.
- **XPolicyLab OpenWAM adapter** was consulted as an interface reference. The adapter here uses the pinned official single-sample `engine.generate` API; it does not copy the newer vendored batched engine.
- **RoboDojo / Isaac Sim** are external simulation dependencies. Their assets, binary packages, native controllers and licenses remain in the separately provisioned runtime. No simulator assets or binaries are redistributed by this repository.

Public source/checkpoint revisions are pinned in `configs/pins.json`. Login files, private observations, experiment outputs and machine-specific configuration are excluded from Git.
