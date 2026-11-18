import { test, expect } from 'claude-code/testing'

const engine = { plugin: 'engine', tier: 'core' } as const

test('moves the listed tools and every built-in browser and visualize tool behind ToolSearch', async ($, on) => {
  on('tool.describe', (_$, e) => ({ description: e.description }))
  for (const tool of ['Artifact', 'ScheduleWakeup', 'ReadNotifications', 'mcp__ccd_session__hand_off_to_session', 'mcp__Claude_Browser__navigate', 'mcp__remote-devices__Claude_Browser__computer', 'mcp__visualize__show_widget']) {
    expect(await $.tool.describe({ tool, description: 'd', provider: engine })).toEqual({ description: 'd', isDeferred: true })
  }
})

test('leaves other tools where the engine placed them', async ($, on) => {
  on('tool.describe', (_$, e) => ({ description: e.description }))
  expect(await $.tool.describe({ tool: 'Bash', description: 'd', provider: engine })).toEqual({ description: 'd' })
})

test('tells ToolSearch about the tools the deferred list leaves out on the first turn', async ($, on) => {
  on('tool.describe', (_$, e) => ({ description: e.description }))
  const { description, isDeferred } = await $.tool.describe({ tool: 'ToolSearch', description: 'Search tools.', provider: engine })
  expect(isDeferred).toBeUndefined()
  expect(description).toStartWith('Search tools.')
  expect(description).toContain('Artifact (publishes a page on claude.ai')
  expect(description).toContain('mcp__Claude_Browser__*')
})
