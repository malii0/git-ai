# komit

A command-line tool that stages your changes, asks a Groq-hosted LLM to write a Conventional Commits message for the diff, then commits and pushes. One keystroke instead of typing `git add`, `git commit -m "..."`, and `git push` separately.

## Features

- Stages everything with `git add .` before generating a message.
- Sends the staged diff to a fast Groq model (`qwen/qwen3.6-27b` by default) and asks for a single-line Conventional Commits message.
- Checks staged files against common secret patterns (`.env`, `.pem`, `id_rsa`, credential files) and asks for confirmation before sending anything or committing.
- Lets you edit the suggested message, skip the push, or preview the message without committing.
- Model is overridable per run with `--model`, or globally with the `KOMIT_MODEL` environment variable.
- Written in standard Python (`urllib`, `subprocess`, `json`, `re`, `argparse`). Nothing to install beyond Python itself.

Note: komit still runs `git add .` before you get a say in it. The secret check only catches common filename patterns, not everything, so keep your `.gitignore` in order regardless.

## Prerequisites

- Python 3.8+
- Git
- A free [Groq API key](https://console.groq.com)

## Installation

Copy `komit.py` to your local binary directory as `komit` (no extension, so it runs as a plain command):

```
mkdir -p ~/.local/bin
cp komit.py ~/.local/bin/komit
chmod +x ~/.local/bin/komit
```

Add `~/.local/bin` to your `PATH` if it isn't already, in `~/.bashrc` or `~/.zshrc`:

```
export PATH="$HOME/.local/bin:$PATH"
```

Export your Groq API key the same way:

```
export GROQ_API_KEY="gsk_your_api_key_here"
```

## Usage

Run inside any Git repository:

```
komit
```

Flags:

```
komit --dry-run          # generate and show the message, commit nothing
komit --no-push          # commit locally, skip the push
komit --model <name>     # use a specific Groq model for this run
```

Set `KOMIT_MODEL` in your shell config to change the default model without passing `--model` every time.

## Security

Commit messages reach Git through an argument list (`subprocess.run([...])`), not a shell string, so text from the model can't be interpreted as a shell command.

Before the diff is sent to Groq, komit checks the staged file names against a list of common secret patterns and asks before continuing if it finds a match. This catches obvious cases like a stray `.env` or `id_rsa`, not a full secret scanner. Your `.gitignore` is still the first line of defense.
