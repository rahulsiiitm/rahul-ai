import requests

url = "http://localhost:8000/api/chat"
payload = {
    "messages": [
        {"role": "user", "content": "Tell me about your experience."}
    ]
}
with requests.post(url, json=payload, stream=True) as r:
    for chunk in r.iter_content(chunk_size=None, decode_unicode=True):
        print(chunk, end="", flush=True)
