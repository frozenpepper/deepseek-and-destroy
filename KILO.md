# DSD — Kilo Code Parent Adapter

Load this only when the **premium parent** runs in Kilo Code. The default technical-worker backend remains external OpenCode/DeepSeek; parent harness and worker backend are independent.

## Parent continuity

Install the project-local adapter:

```bash
python3 <skill>/scripts/install_harness_adapter.py \
  --harness kilo --project-root <project> --skill-root <skill>
```

It installs `.kilo/plugin/dsd-compaction.ts` plus DSD checkpoint helpers. Reload Kilo after installation. The plugin prepares durable DSD state before native compaction; `context_checkpoint.py verify-resume` remains authority before new project work. If plugin loading is uncertain, use the manual/fresh-session path in `COMPACTION.md`.

## Normal DSD workers

Unless configuration explicitly selects Kilo-native workers, use the ordinary high-level external path from `SKILL.md`:

```text
dsd_attempt.py launch → quiescent wait when detached → dsd_attempt.py gate
```

Do not reimplement OpenCode launch mechanics in Kilo parent context.

## Optional Kilo-native workers

If the run explicitly selects Kilo-native subagents, load **only then**:

`adapters/kilo/README.md`

That cold document owns subagent installation, mutating/read-only wrappers, and native reserve/finalize lifecycle. Native workers must still enter the same immutable DSD scope/evidence gate; they do not bypass it.

Role changes are fresh contexts. Evidence Clerk is always project-read-only. Verification gets the mutating wrapper only when the exact task contract authorizes generated/project writes.
