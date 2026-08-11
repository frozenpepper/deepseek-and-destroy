import type { Plugin } from "@kilocode/plugin"

const server: Plugin = async (ctx) => ({
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

    const instruction = Bun.spawnSync([
      "python3", script,
      "--project-root", root,
      "instruction",
    ], { stdout: "pipe", stderr: "pipe" })
    if (instruction.exitCode !== 0) {
      const stderr = new TextDecoder().decode(instruction.stderr).trim()
      output.context.push(`\n## DeepSeek and Destroy checkpoint warning\nResume-instruction generation failed: ${stderr}\nDo not assume continuity is safe.\n`)
      return
    }
    const text = new TextDecoder().decode(instruction.stdout).trim()
    output.context.push(`\n## DeepSeek and Destroy durable continuation\n${text}\n`)
  },
})

export default { id: "deepseek-and-destroy-compaction", server }
