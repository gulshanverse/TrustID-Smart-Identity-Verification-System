# External dataset gate

## Labeled Faces in the Wild (LFW)

- **Original source:** University of Massachusetts Amherst LFW project and technical reports.
- **Protocol source:** Gary B. Huang and Erik Learned-Miller, *Labeled Faces in the Wild: Updates and New Reporting Procedures*, UM-CS-2014-003.
- **Usage decision:** **BLOCKED for this Phase 2.2 run.** The user explicitly instructed that real-face public datasets must not be used.
- **Downloaded version:** None.
- **Checksum:** Not applicable; no files downloaded.
- **Expected structure if later authorized:** official LFW image directories plus the official/standard pair-definition files used by the selected protocol.
- **Repository status:** this README is committed; any future dataset files must remain outside Git and require a separate explicit authorization and license review.

## Phase 2.3 inventory

| Dataset | Official source | Terms status | Processing status | Reason |
| --- | --- | --- | --- | --- |
| LFW | UMass Amherst LFW project | Research/evaluation use described; dataset redistribution and commercial rights unresolved | **Processed locally** | Official 10-fold verification protocol was available and local research evaluation was authorized |
| VGGFace2 | Oxford VGG | Dataset-specific license unclear; official downloads unavailable | **Blocked** | No lawful official copy was available |
| CelebA | CUHK MMLab | Non-commercial research only; no official verification-pair protocol | **Blocked** | Official identity-annotation access was not available during this run |
| IJB-C | NIST | Per-item license variants; official distribution discontinued | **Not validated** | No lawful copy was available |

The LFW run processed 6,000 official pairs: 3,000 genuine and 3,000 impostor. Raw LFW data was downloaded only to `/tmp/trustid-lfw`, used for the benchmark, and removed after processing. The repository contains aggregate results, protocol metadata, and plots only. It contains no raw images, crops, embeddings, or pair-level biometric caches.

The LFW benchmark is for internal research evaluation. Its sources do not establish unrestricted redistribution or commercial-use rights. Any operational or commercial use requires separate legal review.
