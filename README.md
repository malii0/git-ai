# git-ai

A fast, lightweight CLI utility that automates Git staging, generates **Conventional Commits** messages using Groq-hosted LLMs, and pushes to your remote repository with one keystroke.

## Features

- **Automated Staging:** Runs `git add .` to capture all workspace modifications.
-​ **Smart Diff Analysis:** Truncates and analyzes `git diff --cached` using high-speed LLMs (`qwen/qwen3.6-27b`).
-​ **Interactive CLI:** Accept the generated message with `Enter`, edit inline with `e`, or abort with `c`.
- **Zero Heavy Dependencies:** Written entirely in standard Python (`urllib`, `subprocess`, `json`, `re`).

## Prerequisites

- Python 3.8+
- Git
- Free [Groq API Key](https://console.groq.com)

## Installation

- Copy `git-ai.py` to your local binary directory:
  ```bash
  mkdir -p ~/.local/bin
  cp git-ai.py ~/.local/bin/git-ai.py
  chmod +x ~/.local/bin/git-ai.py
  ```

- Register the Git alias:
  ```bash
  git config --global alias.ai '!python3 ~/.local/bin/git-ai.py'
  ```

- Export your Groq API key in your ~/.bashrc or ~/.zshrc:
  ```bash
  export GROQ_API_KEY="gsk_your_api_key_here"
  ```

## Usage

Simply run inside any Git repository:

```bash
git ai
```