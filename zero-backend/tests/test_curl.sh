export OPENROUTER_API_KEY="<YOUR_OPENROUTER_API_KEY>"
.venv/bin/uvicorn main:app --port 8000 &
SERVER_PID=$!
sleep 2
curl -N -X POST "http://localhost:8000/api/chat" -H "Content-Type: application/json" -d '{"messages": [{"role": "user", "content": "Write a poem about robots"}]}'
kill $SERVER_PID
