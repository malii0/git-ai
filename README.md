# komit

A CLI tool that stages your changes, asks a Groq-hosted LLM to write a Conventional Commits message from the diff, and pushes. One command instead of add, commit, push.

## What it does

Runs `git add .`, then `git diff --cached`, sends the diff to Groq (`qwen/qwen3.6-27b`, currently a preview model there, so it may change or disappear), and shows you the suggested commit message. Press enter to accept it, `e` to write your own, or `c` to cancel. On accept, it commits and pushes.

No dependencies beyond the Python standard library: `urllib`, `subprocess`, `json`, `re`.

Note: `git add .` stages everything in the working tree, including `.env` files or anything else not already covered by `.gitignore`. Check your `.gitignore` before running this.

## Requirements

- Python 3.8+
- Git
- A free Groq API key: https://console.groq.com

## Install

Copy `komit.py` into your local bin as `komit` (no extension):

```
mkdir -p ~/.local/bin
cp komit.py ~/.local/bin/komit
chmod +x ~/.local/bin/komit
```

Add `~/.local/bin` to your `PATH` if it isn't already, in `~/.bashrc` or `~/.zshrc`:

```
export PATH="$HOME/.local/bin:$PATH"
```

Set your Groq API key the same way:

```
export GROQ_API_KEY="gsk_your_api_key_here"
```

## Usage

From inside any git repo:

```
komit
```

## Security note

Commit messages go to git as an argument list (`subprocess.run([...])`), not interpolated into a shell string. Text from the model or from your own edits can't be read as shell commands.
