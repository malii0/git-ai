#!/usr/bin/env python3
import subprocess
import sys
import os
import re
import urllib.request
import urllib.error
import json

def run_cmd(cmd):
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    return result.stdout.strip(), result.stderr.strip(), result.returncode

# 1. Değişiklikleri ekle
run_cmd("git add .")

# 2. Diff kontrolü
diff_output, _, _ = run_cmd("git diff --cached")
if not diff_output:
    print("❌ Gönderilecek herhangi bir değişiklik yok.")
    sys.exit(0)

# 3. API Anahtarı kontrolü
api_key = os.getenv("GROQ_API_KEY")
if not api_key:
    print("❌ Hata: GROQ_API_KEY bulunamadı.")
    print("Terminalde şu komutla tanımlayabilirsin: export GROQ_API_KEY=\"gsk_...\"")
    sys.exit(1)

headers = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {api_key.strip()}",
    "User-Agent": "GitAutoCommit/1.0"
}

# 4. Modelleri listele ve en uygun doğrudan chat modelini seç
print("⏳ Model ve değişiklikler analiz ediliyor...", end="", flush=True)

selected_model = None
try:
    models_req = urllib.request.Request("https://api.groq.com/openai/v1/models", headers=headers)
    with urllib.request.urlopen(models_req) as resp:
        all_models = [m["id"] for m in json.loads(resp.read().decode()).get("data", [])]
        
        # Filtreleme
        valid_chat_models = [
            m for m in all_models 
            if not any(x in m.lower() for x in ["guard", "whisper", "vision", "embed", "safeguard", "r1", "reason"])
        ]
        
        # Standart instruct/versatile modeller
        for pref in ["llama-3.3-70b-versatile", "llama-3.1-8b-instant", "llama3", "gemma2", "mixtral", "qwen"]:
            for m in valid_chat_models:
                if pref in m.lower():
                    selected_model = m
                    break
            if selected_model:
                break
                
        if not selected_model and valid_chat_models:
            selected_model = valid_chat_models[0]
except Exception:
    pass

if not selected_model:
    selected_model = "llama-3.3-70b-versatile"

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

try:
    with urllib.request.urlopen(req) as response:
        res_data = json.loads(response.read().decode())
        raw_msg = res_data["choices"][0]["message"]["content"]
        
        # <think>...</think> etiketlerini ve gereksiz boşlukları temizle
        clean_msg = re.sub(r'<think>.*?</think>', '', raw_msg, flags=re.DOTALL).strip()
        # Varsa birden fazla satırı tek satıra indir
        commit_msg = clean_msg.split('\n')[-1].strip('`"\' ')
except urllib.error.HTTPError as e:
    err_body = e.read().decode()
    print(f"\n❌ API Hatası ({e.code}): {err_body}")
    sys.exit(1)
except Exception as e:
    print(f"\n❌ Beklenmeyen Hata: {e}")
    sys.exit(1)

print("\r" + " " * 45 + "\r", end="")

# 5. Onay
print(f"📌 Önerilen Mesaj (\033[0;33m{selected_model}\033[0m): \033[1;32m{commit_msg}\033[0m\n")
choice = input("Commit atılıp pushlansın mı? [E: Evet / d: Düzenle / h: İptal] (Varsayılan: E): ").strip().lower()

final_msg = commit_msg
if choice in ["d", "edit"]:
    final_msg = input("Kendi commit mesajını yaz: ").strip()
    if not final_msg:
        print("İptal edildi.")
        sys.exit(0)
elif choice not in ["", "e", "evet", "y"]:
    print("❌ İşlem iptal edildi.")
    sys.exit(0)

# 6. Commit ve Push
print("\n🚀 Kaydediliyor ve pushlanıyor...")
_, err, code = run_cmd(f'git commit -m "{final_msg}"')
if code != 0:
    print(f"Commit hatası: {err}")
    sys.exit(1)

_, err, code = run_cmd("git push")
if code != 0:
    print(f"Push hatası: {err}")
    sys.exit(1)

print("✅ Başarıyla GitHub'a gönderildi!")
