#!/usr/bin/env python3
import subprocess
import sys
import os
import re
import argparse
import urllib.request
import urllib.error
import json

API_TIMEOUT = 20  # seconds
MAX_DIFF_CHARS = 3000
MAX_COMPLETION_TOKENS = 200  # commit message is short; keeps latency/cost predictable

# Filename patterns that commonly hold secrets. If any of these end up
# staged, we warn before sending the diff off to a third-party API and
# before committing — `git add .` doesn't know the difference between
# a source file and a leaked credential.
RISKY_PATTERNS = [
    r'(^|/)\.env(\..+)?$',
    r'\.pem$',
    r'\.key$',
    r'(^|/)id_rsa$',
    r'(^|/)id_ed25519$',
    r'credentials\.json$',
    r'secrets?\.(ya?ml|json|toml)$',
    r'(^|/)\.npmrc$',
    r'(^|/)\.pgpass$',
]
RISKY_RE = re.compile('|'.join(RISKY_PATTERNS), re.IGNORECASE)


def run_cmd_argv(argv):
    """Run a command as an argument list (no shell) — used for every git call."""
    result = subprocess.run(argv, capture_output=True, text=True)
    return result.stdout.strip(), result.stderr.strip(), result.returncode


def parse_args():
    parser = argparse.ArgumentParser(prog="komit", description="Stage, generate a commit message, commit and push.")
    parser.add_argument("--no-push", action="store_true", help="Commit locally but skip pushing.")
    parser.add_argument("--dry-run", action="store_true", help="Only generate and show the commit message; commit nothing, push nothing.")
    parser.add_argument("--model", default=None, help="Override the Groq model (defaults to $KOMIT_MODEL or the built-in default).")
    return parser.parse_args()


def staged_risky_files():
    names, _, _ = run_cmd_argv(["git", "diff", "--cached", "--name-only"])
    if not names:
        return []
    return [f for f in names.split("\n") if f and RISKY_RE.search(f)]


def build_request(api_key, model, prompt):
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key.strip()}",
        "User-Agent": "Komit/1.0"
    }
    data = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.1,
        "max_completion_tokens": MAX_COMPLETION_TOKENS,
        # Qwen3 reasoning models otherwise embed their reasoning as raw
        # <think>...</think> text inside `content`. If the response gets
        # cut off mid-thought (e.g. hits the token limit before closing
        # the tag), that unclosed <think> leaks through as the "commit
        # message". `hidden` makes Groq strip reasoning entirely and
        # return only the final answer, and `none` skips thinking mode
        # altogether (unnecessary for a one-line commit message).
        "reasoning_format": "hidden",
        "reasoning_effort": "none",
    }
    return urllib.request.Request(
        "https://api.groq.com/openai/v1/chat/completions",
        data=json.dumps(data).encode("utf-8"),
        headers=headers
    )


def extract_commit_message(raw_msg):
    """Strip any leftover reasoning tags/quotes/markdown and return the first real line."""
    clean_msg = re.sub(r'<think>.*?</think>', '', raw_msg, flags=re.DOTALL).strip()
    lines = [l.strip('`"\' ') for l in clean_msg.split('\n') if l.strip()]
    return lines[0] if lines else ""


def call_groq(api_key, model, prompt):
    req = build_request(api_key, model, prompt)
    with urllib.request.urlopen(req, timeout=API_TIMEOUT) as response:
        res_data = json.loads(response.read().decode())
        raw_msg = res_data["choices"][0]["message"]["content"]
        return extract_commit_message(raw_msg)


def main():
    args = parse_args()

    # 1. Stage all changes
    run_cmd_argv(["git", "add", "."])

    # 1b. Warn about anything that looks like a secret before it goes
    # anywhere (API call or commit).
    risky = staged_risky_files()
    if risky:
        print("⚠️  These staged files look like they might contain secrets:")
        for f in risky:
            print(f"   - {f}")
        proceed = input("Continue anyway? [y/N]: ").strip().lower()
        if proceed not in ["y", "yes"]:
            print("❌ Cancelled. Consider adding these to .gitignore or unstaging them.")
            sys.exit(0)

    # 2. Inspect diff
    diff_output, _, _ = run_cmd_argv(["git", "diff", "--cached"])
    if not diff_output:
        print("❌ No staged changes to commit.")
        sys.exit(0)

    truncated = len(diff_output) > MAX_DIFF_CHARS

    # 3. Check API key
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        print("❌ Error: GROQ_API_KEY environment variable not found.")
        print("Export it in your shell config: export GROQ_API_KEY=\"gsk_...\"")
        sys.exit(1)

    # 4. Model selection: --model > $KOMIT_MODEL > built-in default
    selected_model = args.model or os.getenv("KOMIT_MODEL", "qwen/qwen3.6-27b")

    prompt = f"""Generate a concise, single-line Git commit message (Conventional Commits format) for this diff.

Rules:
- Return ONLY the commit message text on a single line.
- Do not output thinking tags, explanations, quotes, or markdown.

Diff:
{diff_output[:MAX_DIFF_CHARS]}"""

    print("⏳ Analyzing changes...", end="", flush=True)

    commit_msg = ""
    try:
        commit_msg = call_groq(api_key, selected_model, prompt)
        if not commit_msg:
            # One automatic retry — covers the odd empty/garbage response
            # instead of forcing the user to rerun the whole command.
            commit_msg = call_groq(api_key, selected_model, prompt)
        if not commit_msg:
            print("\n❌ Model returned an empty commit message. Try again.")
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

    if truncated:
        print(f"⚠️  Diff was truncated to {MAX_DIFF_CHARS} chars — message may be less accurate.")
    print(f"📌 Suggested Commit (\033[0;33m{selected_model}\033[0m): \033[1;32m{commit_msg}\033[0m\n")

    if args.dry_run:
        print("(dry run — nothing committed or pushed)")
        sys.exit(0)

    # 5. Confirmation prompt
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

    # 6. Commit and (optionally) push
    print("\n🚀 Committing" + ("..." if args.no_push else " and pushing to remote..."))
    _, err, code = run_cmd_argv(["git", "commit", "-m", final_msg])
    if code != 0:
        print(f"Commit error: {err}")
        sys.exit(1)

    if args.no_push:
        print("✅ Successfully committed (push skipped, --no-push).")
        sys.exit(0)

    _, err, code = run_cmd_argv(["git", "push"])
    if code != 0:
        print(f"Push error: {err}")
        if "upstream" in err.lower() or "no configured push destination" in err.lower():
            print("Hint: this branch may have no upstream set. Try: git push -u origin <branch>")
        sys.exit(1)

    print("✅ Successfully committed and pushed to remote!")


if __name__ == "__main__":
    main()
