# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

A collection of browser-based games, each implemented as a single self-contained HTML file with inline CSS and JavaScript. No build tools, bundlers, or package managers are used.

## Running Games

Open any `.html` file directly in a browser:
```bash
start <game>.html
```

## Architecture

Each game is a standalone HTML file following this pattern:
- `<style>` block for all CSS (dark/neon aesthetic for canvas games, gradient themes for DOM games)
- HTML markup for UI elements (HUD, overlays, game-over screens)
- `<script>` block containing all game logic
- Canvas-based games use `requestAnimationFrame` game loops with separate `update()` and `draw()` functions
- DOM-based games use event-driven updates

No shared code, frameworks, or external dependencies exist between games.

## Git Workflow

- Remote: `origin` at `https://github.com/markrodman-stack/Claudecodetest.git`
- Branch: `main`
- `gh` CLI is installed at `/c/Users/mrodman/ghcli/bin/gh.exe`
- The `.claude/` directory is gitignored

**You must commit and push regularly as you work.** After completing any meaningful unit of work (new feature, bug fix, refactor, config change), stage the relevant files, commit with a clear descriptive message, and push to `origin main`. Do not wait until the end of a session — commit incrementally so that no work is ever lost. If a session ends unexpectedly, the latest state should already be on GitHub.

## Memory System

A persistent memory system lives in `memory/`. Read these files at session start for user context:
- `memory/user.md` - User profile (nickname: Shooter McGavin)
- `memory/preferences.md` - Working preferences
- `memory/decisions.md` - Key decisions made
- `memory/people.md` - Team members

Update memory files when learning new user info, preferences, or decisions.
