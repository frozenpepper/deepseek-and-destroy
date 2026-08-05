// EXPERIMENTAL -- unverified against a live Kilo session. See KILOCODE.md
// and HARNESS.md's capability matrix before relying on this.
//
// Kilo's bundled CLI runtime references the same "session.compacting" hook
// name OpenCode's plugin interface uses, which is why this is worth shipping
// at all -- but no live Kilo run has confirmed the hook actually fires, what
// shape `output` has, or where Kilo expects a local (non-npm-published)
// plugin file to live. Verify empirically before trusting this for a run you
// can't afford to lose continuity on; until then, treat Kilo as
// manual/fresh-session mode per HARNESS.md.
import type { Plugin } from "@opencode-ai/plugin"

export const DeepSeekAndDestroyCompaction: Plugin = async (ctx) => {
  return {
    "experimental.session.compacting": async (_input, output) => {
      const root = process.env.DSD_PROJECT_ROOT || ctx.worktree || ctx.directory
      const script = `${root}/DeepSeekAndDestroy/tools/context_checkpoint.py`
      const prepare = Bun.spawnSync([
        "python3", script,
        "--project-root", root,
        "prepare",
        "--harness", "kilo",
        "--reason", "kilo-native-precompact",
      ], { stdout: "pipe", stderr: "pipe" })

      if (prepare.exitCode === 4) return
      if (prepare.exitCode !== 0) {
        const stderr = new TextDecoder().decode(prepare.stderr).trim()
        output.context.push(`\n## DeepSeek and Destroy checkpoint warning\nCheckpoint preparation failed: ${stderr}\nDo not assume continuity is safe. Persist the active run manually before continuing.\n`)
        return
      }

      const rehydrate = Bun.spawnSync([
        "python3", script,
        "--project-root", root,
        "instruction",
      ], { stdout: "pipe", stderr: "pipe" })
      const text = new TextDecoder().decode(rehydrate.stdout).trim()
      output.context.push(`\n## DeepSeek and Destroy durable continuation\n${text}\n`)
    },
  }
}
