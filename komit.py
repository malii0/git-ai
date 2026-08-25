#!/usr/bin/env python3

import subprocess
import sys
import os
import re
import urllib.request
import urllib.error
import json

API_TIMEOUT = 20  # seconds


def run_cmd(cmd):
    """Run a shell command (used only for read-only / fixed commands)."""
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    return result.stdout.strip(), result.stderr.strip(), result.returncode


def run_cmd_argv(argv):
    """Run a command as an argument list (no shell) — safe for user-controlled input."""
    result = subprocess.run(argv, capture_output=True, text=True)
    return result.stdout.strip(), result.stderr.strip(), result.returncode


# 1. Stage all changes
run_cmd("git add .")

# 2. Inspect diff
diff_output, _, _ = run_cmd("git diff --cached")
if not diff_output:
    print("❌ No staged changes to commit.")
    sys.exit(0)

# 3. Check API key
api_key = os.getenv("GROQ_API_KEY")
if not api_key:
    print("❌ Error: GROQ_API_KEY environment variable not found.")
    print("Export it in your shell config: export GROQ_API_KEY=\"gsk_...\"")
    sys.exit(1)

headers = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {api_key.strip()}",
    "User-Agent": "Komit/1.0"
}

# 4. Model selection
selected_model = "qwen/qwen3.6-27b"

prompt = f"""Generate a concise, single-line Git commit message (Conventional Commits format) for this diff.

Rules:
- Return ONLY the commit message text on a single line.
- Do not output thinking tags, explanations, quotes, or markdown.

Diff:
{diff_output[:3000]}"""

data = {
    "model": selected_model,
    "messages": [{"role": "user", "content": prompt}],
    "temperature": 0.1
}

req = urllib.request.Request(
    "https://api.groq.com/openai/v1/chat/completions",
    data=json.dumps(data).encode("utf-8"),
    headers=headers
)

print("⏳ Analyzing changes...", end="", flush=True)

try:
    with urllib.request.urlopen(req, timeout=API_TIMEOUT) as response:
        res_data = json.loads(response.read().decode())
    raw_msg = res_data["choices"][0]["message"]["content"]

    # Strip reasoning tags and quotes; take the FIRST non-empty line,
    # since the model may prepend an explanation despite instructions.
    clean_msg = re.sub(r'<think>.*?</think>', '', raw_msg, flags=re.DOTALL).strip()
    lines = [l.strip('`"\' ') for l in clean_msg.split('\n') if l.strip()]
    commit_msg = lines[0] if lines else ""

    if not commit_msg:
        print("\n❌ Model returned an empty commit message.")
        sys.exit(1)

except urllib.error.HTTPError as e:
    err_body = e.read().decode()
    print(f"\n❌ API Error ({e.code}): {err_body}")
    sys.exit(1)
except urllib.error.URLError as e:
    print(f"\n❌ Network error contacting Groq API: {e.reason}")
    sys.exit(1)
except (KeyError, IndexError, json.JSONDecodeError):
    print("\n❌ Unexpected response format from Groq API.")
    sys.exit(1)
except Exception as e:
    print(f"\n❌ Unexpected Error: {e}")
    sys.exit(1)

print("\r" + " " * 45 + "\r", end="")

# 5. Confirmation prompt
print(f"📌 Suggested Commit (\033[0;33m{selected_model}\033[0m): \033[1;32m{commit_msg}\033[0m\n")
choice = input("Commit and push? [Y: Yes / e: Edit / c: Cancel] (Default: Y): ").strip().lower()

final_msg = commit_msg
if choice in ["e", "edit"]:
    final_msg = input("Enter custom commit message: ").strip()
    if not final_msg:
        print("Cancelled.")
        sys.exit(0)
elif choice not in ["", "y", "yes"]:
    print("❌ Operation cancelled.")
    sys.exit(0)

# 6. Commit and Push
print("\n🚀 Committing and pushing to remote...")
_, err, code = run_cmd_argv(["git", "commit", "-m", final_msg])
if code != 0:
    print(f"Commit error: {err}")
    sys.exit(1)

_, err, code = run_cmd_argv(["git", "push"])
if code != 0:
    print(f"Push error: {err}")
    if "upstream" in err.lower() or "no configured push destination" in err.lower():
        print("Hint: this branch may have no upstream set. Try: git push -u origin <branch>")
    sys.exit(1)

print("✅ Successfully committed and pushed to remote!")
