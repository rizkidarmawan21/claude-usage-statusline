#!/usr/bin/env python3
"""Claude Code status line: plan limits, context, cost and session state.

Line 1: Session bar % pace reset | Weekly bar % pace reset | Context bar % |
        $cost | +added -removed | model | Effort | branch
Line 2: fast mode, thinking, caveman badge (only what is on)

Reads only the JSON Claude Code pipes to the status line on stdin, plus
`git branch --show-current` in the session's folder. No network, no credential
access. The last seen rate limits are cached so a fresh session (which gets no
rate_limits until its first reply) still shows them.
"""
import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

CFG = Path(os.environ.get("CLAUDE_CONFIG_DIR") or Path.home() / ".claude")
CACHE = CFG / "usage-statusline-cache.json"
CAVEMAN_MODES = {"off", "lite", "full", "ultra", "wenyan-lite", "wenyan", "wenyan-full",
                 "wenyan-ultra", "commit", "review", "compress"}
WINDOW_SECS = {"five_hour": 5 * 3600, "seven_day": 7 * 86400}
BAR_CELLS = 12

# Teal below 50 %, gold from 50 %, red from 80 %.
RESET, DIM, TEXT = "\033[0m", "\033[2m", ""
TEAL, GOLD, RED = "\033[38;5;36m", "\033[38;5;179m", "\033[38;5;167m"
GREEN, YELLOW = "\033[32m", "\033[33m"
BRIGHT_GREEN, BRIGHT_RED, BRIGHT_YELLOW = "\033[92m", "\033[91m", "\033[93m"
EFFORT_FULL = {"low": "Low", "medium": "Medium", "high": "High", "xhigh": "XHigh", "max": "Max"}
EFFORT_COLOURS = {"low": DIM, "xhigh": YELLOW, "max": BRIGHT_RED}
SEP = " | "


def num(v):
    try:
        f = float(v)
        return f if f == f and abs(f) != float("inf") else None
    except (TypeError, ValueError):
        return None


def clean(s, n=40):
    return re.sub(r"[\x00-\x1f\x7f]", "", str(s))[:n]


def level_color(pct):
    return RED if pct >= 80 else GOLD if pct >= 50 else TEAL


def bar(pct):
    # Filled ━ in the level colour, then the ─ track dimmed in the same colour.
    filled = max(0, min(BAR_CELLS, round(pct / 100 * BAR_CELLS)))
    return f"{level_color(pct)}{'━' * filled}{DIM}{'─' * (BAR_CELLS - filled)}{RESET}"


def pace(pct, resets_at, window, now):
    """Arrow comparing usage with time elapsed in the window.

    Within 5 points is on track (→), past 5 is ↑/↓, past 20 is ⇈ (red) /
    ⇊ (green).
    """
    end = num(resets_at)
    if end is None or not window:
        return ""
    elapsed = 100 * (window - (end - now)) / window
    if elapsed <= 0:
        return ""
    diff = pct - min(100.0, elapsed)
    if diff > 20:
        return f"{BRIGHT_RED}⇈{RESET}"
    if diff > 5:
        return f"{YELLOW}↑{RESET}"
    if diff < -20:
        return f"{BRIGHT_GREEN}⇊{RESET}"
    if diff < -5:
        return f"{GREEN}↓{RESET}"
    return f"{DIM}→{RESET}"


def countdown(resets_at, now):
    end = num(resets_at)
    if end is None or end <= now:
        return ""
    m = int((end - now) // 60)
    h, m = divmod(m, 60)
    return f"{h}h {m:02d}m" if h else f"{m}m"


def reset_day(resets_at, now):
    """'R:Fri 3pm', or a countdown ('R:14h 22m') in the last 24 hours."""
    end = num(resets_at)
    if end is None or end <= now:
        return ""
    if end - now < 86400:
        return f"R:{countdown(resets_at, now)}"
    t = datetime.fromtimestamp(end)
    mins = f":{t.minute:02d}" if t.minute else ""
    return f"R:{t.strftime('%a')} {t.hour % 12 or 12}{mins}{'am' if t.hour < 12 else 'pm'}"


def caveman_badge():
    flag = CFG / ".caveman-active"
    try:
        if flag.is_symlink() or not flag.is_file():
            return ""
        mode = re.sub(r"[^a-z0-9-]", "", flag.read_bytes()[:64].decode("utf-8", "ignore").lower())
    except OSError:
        return ""
    if mode not in CAVEMAN_MODES and mode != "":
        return ""
    label = "CAVEMAN" if mode in ("", "full") else f"CAVEMAN:{mode.upper()}"
    return f"\033[38;5;172m[{label}]{RESET}"


def rate_limits(data, now):
    rl = data.get("rate_limits")
    if isinstance(rl, dict) and rl:
        try:
            tmp = CACHE.with_suffix(".tmp")
            tmp.write_text(json.dumps(rl))
            tmp.replace(CACHE)
        except OSError:
            pass
        return rl
    try:
        rl = json.loads(CACHE.read_text())
    except (OSError, ValueError):
        return {}
    if not isinstance(rl, dict):
        return {}
    # Drop windows that already reset: their percentage is stale.
    return {k: v for k, v in rl.items()
            if isinstance(v, dict) and (num(v.get("resets_at")) or 0) > now}


def limit_segment(label, key, rl, now, when):
    w = rl.get(key)
    if not isinstance(w, dict):
        return None
    pct = num(w.get("used_percentage"))
    if pct is None:
        return None
    seg = f"{TEXT}{label}{RESET} {bar(pct)} {TEXT}{pct:.0f}%{RESET}"
    arrow = pace(pct, w.get("resets_at"), WINDOW_SECS.get(key), now)
    if arrow:
        seg += f" {arrow}"
    tail = when(w.get("resets_at"), now)
    if tail:
        seg += f" {TEXT}{tail}{RESET}"
    return seg


def git_branch(cwd):
    if not cwd or not os.path.isdir(cwd):
        return ""
    try:
        out = subprocess.run(["git", "-C", cwd, "branch", "--show-current"],
                             capture_output=True, text=True, timeout=1)
        return clean(out.stdout.strip(), 40) if out.returncode == 0 else ""
    except (OSError, subprocess.SubprocessError):
        return ""


def main():
    try:
        data = json.loads(sys.stdin.read() or "{}")
    except ValueError:
        data = {}
    if not isinstance(data, dict):
        data = {}
    now = time.time()
    line1, line2 = [], []

    rl = rate_limits(data, now)
    for seg in (limit_segment("Session", "five_hour", rl, now, countdown),
                limit_segment("Weekly", "seven_day", rl, now, reset_day)):
        if seg:
            line1.append(seg)

    ctx = data.get("context_window")
    pct = num(ctx.get("used_percentage")) if isinstance(ctx, dict) else None
    if pct is not None:
        line1.append(f"{TEXT}Context{RESET} {bar(pct)} {TEXT}{pct:.0f}%{RESET}")

    cost = data.get("cost") if isinstance(data.get("cost"), dict) else {}
    usd = num(cost.get("total_cost_usd"))
    if usd is not None:
        line1.append(f"{TEXT}${usd:.2f}{RESET}")
    added, removed = num(cost.get("total_lines_added")), num(cost.get("total_lines_removed"))
    if added or removed:
        line1.append(f"{BRIGHT_GREEN}+{int(added or 0)}{RESET} {BRIGHT_RED}-{int(removed or 0)}{RESET}")

    model = data.get("model")
    if isinstance(model, dict):
        # Family name only ("Opus"); fall back to display_name.
        fam = re.search(r"(opus|sonnet|haiku|fable|mythos)", str(model.get("id") or ""), re.I)
        name = fam.group(1).title() if fam else clean(model.get("display_name") or "")
        name = re.sub(r"\s*\([^)]*context[^)]*\)", "", name).strip()
        if name:
            line1.append(name)

    effort = data.get("effort")
    level = clean(effort.get("level") or "", 20) if isinstance(effort, dict) else ""
    if level and level != "unset":
        label = EFFORT_FULL.get(level, level.title())
        colour = EFFORT_COLOURS.get(level, "")
        line1.append(f"{colour}Effort: {label}{RESET}" if colour else f"Effort: {label}")

    ws = data.get("workspace") if isinstance(data.get("workspace"), dict) else {}
    branch = git_branch(ws.get("current_dir") or data.get("cwd"))
    if branch:
        line1.append(f"{TEXT}{branch}{RESET}")

    if data.get("fast_mode") is True:
        line2.append(f"{BRIGHT_YELLOW}⚡fast{RESET}")
    thinking = data.get("thinking")
    if isinstance(thinking, dict) and thinking.get("enabled"):
        line2.append(f"{DIM}think{RESET}")
    badge = caveman_badge()
    if badge:
        line2.append(badge)

    out = SEP.join(line1)
    if line2:
        out += ("\n" if out else "") + SEP.join(line2)
    sys.stdout.write(out)


if __name__ == "__main__":
    main()
