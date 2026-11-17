# claude-usage-statusline

A small status line for [Claude Code](https://docs.claude.com/en/docs/claude-code) that shows your plan limits, context, cost and session state under the prompt.

```
Session ━━━───────── 27% ↓ 2h 51m | Weekly ━━━━━━━━━─── 73% ↑ R:Thu 6pm | Context ━━━━──────── 35% | $38.75 | +142 -37 | Opus | Effort: XHigh | main
⚡fast | think
```

One Python file, standard library only. It reads the JSON Claude Code already sends to the status line on stdin. It makes no network calls and never touches your login token or keychain.

## What it shows

**Line 1**

| Part | Source |
|---|---|
| `Session` bar, %, pace, time to reset | `rate_limits.five_hour` |
| `Weekly` bar, %, pace, reset day (`R:Thu 6pm`, or a countdown in the last 24h) | `rate_limits.seven_day` |
| `Context` bar and % | `context_window.used_percentage` |
| `$38.75` session cost (API-equivalent) | `cost.total_cost_usd` |
| `+142 -37` lines changed | `cost.total_lines_added` / `total_lines_removed` |
| Model family (`Opus`) | `model.id` |
| `Effort: XHigh` | `effort.level` |
| Git branch | `git branch --show-current` in the session folder |

**Line 2** (only what is on): `⚡fast` mode, `think`, and a `[CAVEMAN]` badge if you use the caveman plugin.

Bars are teal below 50 %, gold from 50 %, red from 80 %.

The pace arrow compares how much of a limit you have used with how much of its window has passed: `→` within 5 points, `↑`/`↓` past 5, `⇈`/`⇊` past 20.

The `rate_limits` block only reaches the status line on Claude.ai Pro/Max plans, and only after the session's first reply. The script keeps the last values it saw in `$CLAUDE_CONFIG_DIR/usage-statusline-cache.json` so a fresh session still shows them, and drops a window once its reset time has passed.

## Install

Python 3.8+.

```bash
git clone https://github.com/rizkidarmawan21/claude-usage-statusline.git ~/.claude-usage-statusline
```

Then add this to `~/.claude/settings.json` (or `$CLAUDE_CONFIG_DIR/settings.json`):

```json
{
  "statusLine": {
    "type": "command",
    "command": "python3 \"$HOME/.claude-usage-statusline/usage-statusline.py\"",
    "padding": 0
  }
}
```

The status line updates on the next repaint.

## Try it without Claude Code

```bash
now=$(date +%s)
echo "{\"model\":{\"id\":\"claude-opus-5-5\"},\"context_window\":{\"used_percentage\":35},
\"rate_limits\":{\"five_hour\":{\"used_percentage\":27,\"resets_at\":$((now+10000))},
\"seven_day\":{\"used_percentage\":73,\"resets_at\":$((now+200000))}}}" | python3 usage-statusline.py
```

## Credits

The look is inspired by [usage-pulse](https://github.com/NoobyGains/usage-pulse), which does much more (other providers, themes, setup wizard). This is an independent, much smaller implementation and contains no code from it.

## License

MIT
