# Git Hooks for yt-dlp Changelog Attribution

This directory contains git hooks that automatically add proper attribution to commit messages for yt-dlp's changelog generation.

## What it does

Automatically adds `Authored by: <your-github-username>` to every commit message, ensuring proper credit in release changelogs.

## Installation

After cloning the repository, run ONE of the following commands from the repository root:

### On Linux/macOS/Git Bash:
```bash
.githooks/install-hooks.sh
```

### On Windows PowerShell:
```powershell
.githooks/install-hooks.ps1
```

### Alternative (works everywhere):
```bash
git config core.hooksPath .githooks
```

## How it works

The hook automatically:
1. Checks for `git config user.github` for your GitHub username
2. Falls back to parsing your username from the `origin` remote URL
3. Appends `Authored by: <username>` to your commit messages

## Manual Configuration (Optional)

If your GitHub username differs from what's in the remote URL, set it manually:
```bash
git config user.github your-github-username
```

## Why this is needed

The yt-dlp changelog generation script (devscripts/make_changelog.py) defaults to crediting commits to 'pukkandan' unless an explicit "Authored by:" line is present in the commit message. This hook ensures you get proper attribution.
