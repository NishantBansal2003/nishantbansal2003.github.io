---
title: "IMPL: Short Bug Name"
date: DATE 10:30:00 +0530
# Categories: [Lightning, Security] for vulnerability writeups.
categories: [Lightning, Security]
# Tags, in this order:
#   implementation: lnd | cln | ldk | eclair  (several for cross-implementation bugs)
#   impact:         dos | theft | griefing
#   protocol:       bolt2 | bolt7 | ...
#   method:         fuzzing (+ smite when smite found it)
tags: [impl, dos, bolt2, fuzzing]
description: Technical analysis of a ... vulnerability in IMPL.
image:
  path: /assets/img/SLUG.png  # 1200x630
  alt: One-line description of the cover image
disclosure:
  affected: "vX through vY"
  fixed: vZ
  fixed_url: https://github.com/.../releases/tag/vZ
  impact: Remote node crash
---

_TODO: 3-4 sentences: what is vulnerable, what the attacker sends, what happens, what it costs the attacker._

## Background

_TODO: Just enough protocol and implementation context to follow the bug. Link the BOLTs at a pinned commit._

## The vulnerability

_TODO: The faulty code path, linked at a pinned commit, with trimmed code excerpts._

## The attack

_TODO: Step-by-step attacker actions, then the attack cost._

### Observed impact

_TODO: What actually happened on a regtest/test node: crash, lost funds, persistence across restarts._

## The fix

_TODO: PR, merge date, release, and a trimmed excerpt of the fix._

## Discovery

_TODO: How it was found: fuzz target, smite, manual review._

### Timeline

- **YYYY-MM-DD:** Reported privately to IMPL.
- **YYYY-MM-DD:** IMPL acknowledged the report.
- **YYYY-MM-DD:** Fix merged as [PR #N](https://github.com/...).
- **YYYY-MM-DD:** [IMPL vZ](https://github.com/...) released with the fix.
- **YYYY-MM-DD:** IMPL approved public disclosure.
- **YYYY-MM-DD:** Public disclosure.

## Takeaways

- **Upgrade to the latest IMPL release, currently vN.**
  One-line reason.
- **General lesson for implementers.**
  One-line explanation.
