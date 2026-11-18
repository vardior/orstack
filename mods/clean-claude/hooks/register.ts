import type { EngineInterface, Register, SessionContextBreakdown } from 'claude-code'

const PURPOSES: Record<string, string> = {
  Artifact: 'publishes a page on claude.ai, private until shared; use it when the user asks for an artifact, or when a page would be clearer than plain text',
  ScheduleWakeup: 'schedules when this session resumes work, 60 to 3600 seconds from now',
  ReadNotifications: 'reads the notifications a system notice says are pending',
}
const DEFERRED_TOOLS = ['Artifact', 'ArtifactCheck', 'ArtifactComments', 'ArtifactData', 'ScheduleWakeup', 'SearchPlugins', 'SuggestPluginInstall', 'SuggestSkills', 'ListAgents', 'ReportFindings', 'ShareOnboardingGuide', 'ReadNotifications', 'mcp__ccd_session__dismiss_task', 'mcp__ccd_session__hand_off_to_session', 'mcp__ccd_session__read_widget_context']
const DEFERRED_PREFIXES = ['mcp__Claude_Browser__', 'mcp__remote-devices__Claude_Browser__', 'mcp__visualize__']

const isDeferredHere = (tool: string) => DEFERRED_TOOLS.includes(tool) || DEFERRED_PREFIXES.some(prefix => tool.startsWith(prefix))

const named = DEFERRED_TOOLS.map(tool => (PURPOSES[tool] ? `${tool} (${PURPOSES[tool]})` : tool))
const LOAD_HINT = `Also behind ToolSearch where the session has them, though the deferred tools list may not name them: ${named.join(', ')}, and every tool of the built-in browser and of visualize (${DEFERRED_PREFIXES.map(p => `${p}*`).join(', ')}). Load one with query "select:<name>" before calling it; a prefix loads all its tools.`

type DescribedTool = { name: string, chars: number, provider: string, isDeferred: boolean }
type Row = { name: string, tokens: number }

const AUDIT_COMMAND = 'context-audit'
const AUDIT_FILE = '.claude/clean-claude-audit.json'
const byTokens = (rows: Row[]) => [...rows].sort((a, b) => b.tokens - a.tokens)
const sumTokens = (rows: Row[]) => rows.reduce((sum, item) => sum + item.tokens, 0)
const table = (title: string, rows: Row[]) => rows.length === 0 ? [] : [[`### ${title}: ~${sumTokens(rows)} tokens`, '| name | tokens |', '| --- | --- |', ...byTokens(rows).map(item => `| ${item.name} | ${item.tokens} |`)].join('\n')]

export const register: Register = on => {
  const tools = new Map<string, DescribedTool>()

  on('session.start', async ($, e, next) => {
    await $.command.register({ name: AUDIT_COMMAND, description: 'Itemizes what this session sends the model before your messages: system prompt, tools in front and behind ToolSearch, MCP, skills, agents, memory files' })
    return next(e)
  })

  on('tool.describe', async (_$, e, next) => {
    const described = await next(e)
    const placed = e.tool === 'ToolSearch'
      ? { ...described, description: `${described.description}\n\n${LOAD_HINT}` }
      : isDeferredHere(e.tool) ? { ...described, isDeferred: true } : described
    tools.set(e.tool, { name: e.tool, chars: placed.description.length, provider: e.provider.plugin, isDeferred: placed.isDeferred ?? e.isDeferred === true })
    return placed
  })

  on('command.run', { command: AUDIT_COMMAND }, async $ => {
    const breakdown = (await $.session.usage({ breakdown: 'full' })).context.breakdown
    if (!breakdown) return { text: 'No context breakdown yet: send one message first, then run /context-audit.' }
    return { text: await writeAudit($, breakdown, [...tools.values()]) }
  }).catch((_$, e, next) => (next.called ? next(e) : { text: 'The audit failed; run claude --debug to see why.' }))
}

const writeAudit = async ($: EngineInterface, breakdown: SessionContextBreakdown, tools: DescribedTool[]) => {
  const mcpSchemaTokens = new Map(breakdown.mcpTools.map(tool => [tool.name, tool.tokens]))
  const inFront = tools.filter(tool => !tool.isDeferred).map(tool => ({ name: `${tool.name} (${tool.provider})`, tokens: mcpSchemaTokens.get(tool.name) ?? Math.ceil(tool.chars / 4) }))
  const deferredNames = tools.filter(tool => tool.isDeferred).map(tool => ({ name: tool.name, tokens: Math.ceil(tool.name.length / 3) }))
  const report = [
    `## Context before your first message (${breakdown.model})`,
    ...table('Categories', breakdown.categories.filter(category => category.kind === 'used').map(category => ({ name: category.name, tokens: category.tokens }))),
    ...table('Tools in front (MCP: full schema; others: description only)', inFront),
    `### Behind ToolSearch: ${deferredNames.length} tools, their names listed for ~${sumTokens(deferredNames)} tokens`,
    ...table('Memory files', breakdown.memoryFiles.map(file => ({ name: file.path, tokens: file.tokens }))),
    ...table('Agent types the Agent tool lists', breakdown.agents.map(agent => ({ name: `${agent.agentType} (${agent.source})`, tokens: agent.tokens }))),
    ...(breakdown.skills ? table(`Skill listing (${breakdown.skills.includedSkills} of ${breakdown.skills.totalSkills} skills)`, breakdown.skills.skillFrontmatter.map(skill => ({ name: `${skill.name} (${skill.source})`, tokens: skill.tokens }))) : []),
  ].join('\n\n')
  const path = `${await $.env.get('HOME')}/${AUDIT_FILE}`
  await $.fs.write(path, `${JSON.stringify({ breakdown: { ...breakdown, gridRows: undefined }, tools }, null, 2)}\n`)
  return `${report}\n\nFull report: ${path}`
}
