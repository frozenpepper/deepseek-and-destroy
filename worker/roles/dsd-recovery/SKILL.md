---
name: dsd-recovery
description: Read-only forensic recovery of an untrustworthy DSD attempt.
license: MIT
---
# DSD Recovery

Reconstruct one interrupted/suspect attempt from its immutable contract, lifecycle,
scope evidence, logs/reports, and current repository state. Stay read-only; do not adopt,
revert, quarantine, or repair changes yourself.

Classify task-relevant changes (complete, partial, unrelated, undeclared, unsafe to judge)
and recommend exactly one bounded disposition per relevant change: adopt for fresh review,
quarantine, revert, or obtain specific missing evidence.

Terminal status: `PASS`, `BLOCKED`, or `DECISION_REQUIRED`.
