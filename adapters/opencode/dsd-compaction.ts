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
        "--harness", "opencode",
        "--reason", "opencode-native-precompact",
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
      if (rehydrate.exitCode !== 0) {
        const stderr = new TextDecoder().decode(rehydrate.stderr).trim()
        output.context.push(`\n## DeepSeek and Destroy checkpoint warning\nResume-instruction generation failed: ${stderr}\nDo not assume continuity is safe.\n`)
        return
      }
      const text = new TextDecoder().decode(rehydrate.stdout).trim()
      output.context.push(`\n## DeepSeek and Destroy durable continuation\n${text}\n`)
    },
  }
}
