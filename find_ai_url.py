import zipfile, re

apk = 'C:/Users/Admin/Downloads/app-debug.apk'
with zipfile.ZipFile(apk) as z:
    bundle = z.read('assets/index.android.bundle').decode('utf-8', errors='ignore')

# Find all URLs related to AI/Ollama
patterns = [
    r'https?://[^\s"\']{5,}ollama[^\s"\']*',
    r'https?://[^\s"\']{5,}/api/chat[^\s"\']*',
    r'https?://[^\s"\']{5,}/api/generate[^\s"\']*',
    r'trycloudflare\.com[^\s"\']*',
    r'11434[^\s"\']{0,50}',
]
print('=== AI/OLLAMA URL PATTERNS ===')
for p in patterns:
    matches = re.findall(p, bundle)
    if matches:
        for m in set(matches):
            print('  FOUND:', m[:120])
    else:
        print('  NONE for pattern:', p)

print()
print('=== CHATBOT CONTEXT SNIPPETS ===')
keywords = ['chatbot', 'ollama', '/api/chat', '/api/generate', 'AI_URL', 'OLLAMA_URL', 'aiUrl', 'AiChat', 'ChatScreen']
for kw in keywords:
    idx = bundle.find(kw)
    if idx != -1:
        start = max(0, idx - 80)
        end = min(len(bundle), idx + 120)
        snippet = bundle[start:end].replace('\n', ' ')
        print(f'  [{kw}]')
        print(f'  ...{snippet}...')
        print()
