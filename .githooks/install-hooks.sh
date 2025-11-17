#!/bin/sh
# Install git hooks from .githooks directory

HOOKS_DIR="$(git rev-parse --show-toplevel)/.githooks"
GIT_HOOKS_DIR="$(git rev-parse --git-dir)/hooks"

echo "Installing git hooks..."

# Copy hooks
cp "$HOOKS_DIR/prepare-commit-msg" "$GIT_HOOKS_DIR/prepare-commit-msg"
cp "$HOOKS_DIR/prepare-commit-msg.ps1" "$GIT_HOOKS_DIR/prepare-commit-msg.ps1"

# Make them executable
chmod +x "$GIT_HOOKS_DIR/prepare-commit-msg"
chmod +x "$GIT_HOOKS_DIR/prepare-commit-msg.ps1"

echo "Git hooks installed successfully!"
echo "Commits will now automatically include 'Authored by: <your-github-username>'"
