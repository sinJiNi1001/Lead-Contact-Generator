import urllib.request
import json

print("Pinging Ollama Server...")

url = "http://127.0.0.1:11434/api/generate"
data = json.dumps({
    "model": "llama3.1",
    "prompt": "Say the word 'Success!'",
    "stream": False
}).encode('utf-8')

req = urllib.request.Request(url, data=data, headers={'Content-Type': 'application/json'})

try:
    with urllib.request.urlopen(req, timeout=120) as response:
        result = json.loads(response.read().decode('utf-8'))
        print(f"✅ CONNECTION SUCCESSFUL! AI Says: {result.get('response')}")
except Exception as e:
    print(f"❌ CONNECTION FAILED: {e}")