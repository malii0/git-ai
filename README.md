# git-ekle

CLI utility that generates Conventional Commits messages using Groq's fast LLM APIs and pushes to GitHub with one click.

## Features

- Automatically stages modified files (`git add .`)
- Extracts `git diff` and generates clean, single-line commit messages
- Uses Groq API (`qwen/qwen3.6-27b`) for sub-second inference
- Prompts for confirmation or custom editing before pushing

## Requirements

- Python 3.8+
- Git
- Free [Groq API Key](https://console.groq.com)

## Installation

1. Copy the script to your local bin directory:
   cp gitek.py ~/.local/bin/gitek.py
   chmod +x ~/.local/bin/gitek.py

2. Register the Git alias:
   git config --global alias.ekle '!python3 ~/.local/bin/gitek.py'

3. Add your Groq API key to your shell config (~/.bashrc or ~/.zshrc):
   export GROQ_API_KEY="gsk_your_api_key_here"

## Usage

Run the command inside any Git repository:
git ekle

