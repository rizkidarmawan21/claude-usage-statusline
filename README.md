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

## Install

**Requirements:** Python 3.8+ on your `PATH` as `python3`, Claude Code, and `git` (optional, for the branch). Plan limits need a Claude.ai Pro or Max login; with an API key the limit bars are simply hidden.

1. Clone the repo:

   ```bash
   git clone https://github.com/rizkidarmawan21/claude-usage-statusline.git ~/.claude-usage-statusline
   ```

2. Add a `statusLine` entry to your Claude Code settings. The file is `~/.claude/settings.json`, or `$CLAUDE_CONFIG_DIR/settings.json` if you set `CLAUDE_CONFIG_DIR`. Keep the other keys in the file as they are:

   ```json
   {
     "statusLine": {
       "type": "command",
       "command": "python3 \"$HOME/.claude-usage-statusline/usage-statusline.py\"",
       "padding": 0
     }
   }
   ```

   If you already have a `statusLine`, this replaces it (only one status line command runs).

3. Send a message in Claude Code. The bar appears on the next repaint; the limit bars appear after the session's first reply (see [How the limits get there](#how-the-limits-get-there)).

Windows has not been tested. If `python3` is not found there, use `python` and a full path to the script.

## Usage

There is nothing to run by hand. Claude Code calls the script on every repaint, pipes the session JSON to it and shows what it prints. Parts with no data are left out, so a short line usually just means that data has not arrived yet.

### How the limits get there

Claude Code sends `rate_limits` only on Pro/Max logins and only after the session's first reply. The script saves the last values it saw to `$CLAUDE_CONFIG_DIR/usage-statusline-cache.json` (default `~/.claude/usage-statusline-cache.json`), so a new session shows them straight away. A window is dropped from the cache once its reset time passes.

### Try it without Claude Code

```bash
now=$(date +%s)
echo "{\"model\":{\"id\":\"claude-opus-5-5\"},\"context_window\":{\"used_percentage\":35},
\"rate_limits\":{\"five_hour\":{\"used_percentage\":27,\"resets_at\":$((now+10000))},
\"seven_day\":{\"used_percentage\":73,\"resets_at\":$((now+200000))}}}" \
  | CLAUDE_CONFIG_DIR=$(mktemp -d) python3 ~/.claude-usage-statusline/usage-statusline.py
```

The temporary `CLAUDE_CONFIG_DIR` keeps these test numbers out of your real cache.

## Customize

Edit the constants at the top of `usage-statusline.py`:

| Constant | Default | What it changes |
|---|---|---|
| `BAR_CELLS` | `12` | bar width in characters |
| `TEAL`, `GOLD`, `RED` | 256-colour codes | bar colours; thresholds (50 / 80) are in `level_color()` |
| `SEP` | `" \| "` | separator between parts |
| `EFFORT_COLOURS` | yellow for XHigh, red for Max | colour per effort level |

To hide a part, delete its `line1.append(...)` / `line2.append(...)` block in `main()`.

## Update

```bash
git -C ~/.claude-usage-statusline pull
```

No restart needed; the next repaint uses the new version.

## Uninstall

1. Remove the `statusLine` entry from your settings file (or put your old one back).
2. Delete the files:

   ```bash
   rm -rf ~/.claude-usage-statusline
   rm -f "${CLAUDE_CONFIG_DIR:-$HOME/.claude}/usage-statusline-cache.json"
   ```

## Troubleshooting

| Symptom | Likely cause |
|---|---|
| Status line is blank | Wrong path in `command`, or `python3` not on `PATH`. Run the command from the settings by hand with `echo '{}' \|` in front of it. |
| No `Session` / `Weekly` bars | API-key login (no plan limits), or the session has not had its first reply yet and there is no cache. |
| Numbers look old | They come from the cache until the current session's first reply; they refresh on the next reply. |
| No branch | The session folder is not a git repo, or `git` is not installed. |
| Garbled bars or arrows | Your terminal font lacks the box-drawing or arrow glyphs; switch to a font that has them. |

## Privacy

The script reads stdin, its own cache file, and the output of `git branch --show-current`. It makes no network requests and does not read credentials, the keychain, or your transcripts.

## Credits

The look is inspired by [usage-pulse](https://github.com/NoobyGains/usage-pulse), which does much more (other providers, themes, setup wizard). This is an independent, much smaller implementation and contains no code from it.

## License

MIT
