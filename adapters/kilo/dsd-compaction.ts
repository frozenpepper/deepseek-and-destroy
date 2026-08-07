// EXPERIMENTAL -- package, export shape, hook signature, and ctx fields are
// confirmed against @kilocode/plugin 7.4.20 and a live Kilo server. NOT yet
// confirmed: this hook firing during a real mid-session compaction event
// (only load-at-session-start was tested). See KILOCODE.md and HARNESS.md's
// capability matrix before relying on this for a run you can't afford to lose.
import type { Plugin } from "@kilocode/plugin"

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
