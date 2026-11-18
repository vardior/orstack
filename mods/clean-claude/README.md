# Clean Claude

A Claude Code plugin that keeps the default context lean. Tools that most conversations never call
still cost their full schema on every request. Clean Claude moves the heavy, rarely used ones behind
ToolSearch, so they load only in the conversations that use them.

| Deferred | Why |
| --- | --- |
| `Artifact`, `ArtifactCheck`, `ArtifactComments`, `ArtifactData` | ~11k tokens of schema |
| The built-in browser (`mcp__Claude_Browser__*`, `mcp__remote-devices__Claude_Browser__*`) | ~8k tokens |
| Visualize (`mcp__visualize__*`) | ~1.5k tokens |
| `mcp__ccd_session__hand_off_to_session`, `mcp__ccd_session__dismiss_task`, `mcp__ccd_session__read_widget_context`, `ReadNotifications` | ~1.4k tokens, rarely called |
| `ScheduleWakeup`, `SearchPlugins`, `SuggestPluginInstall`, `SuggestSkills`, `ListAgents`, `ReportFindings`, `ShareOnboardingGuide` | rarely called |

A deferred tool still works. ToolSearch's description names each one, and the model loads it with
`select:<name>` before calling it.

## See what your sessions load

Send one message in a conversation, then run `/context-audit`. It lists every category of the
context window before your messages: system prompt, tools in front and the count behind ToolSearch,
MCP server instructions, memory files, agent types and the skill listing, largest first. It also
writes the full breakdown to `~/.claude/clean-claude-audit.json`.

## Install

```
/plugin marketplace add vardior/orstack
/plugin install clean-claude@orstack
```

## Limits

Claude Code's built-in security plugin (`cc-plugin-sec-default`) keeps user-installed plugins away
from the system prompt, the first message's context, reminders and skill bodies. Clean Claude
therefore changes tools only: where they sit, and ToolSearch's description.
