import ollama
from config import OLLAMA_MODEL

class ZeroBrain:
    def __init__(self):
        self.model = OLLAMA_MODEL
        self.history = []

    def generate_streaming_response(self, prompt: str):
        self.history.append({'role': 'user', 'content': prompt})
        
        try:
            # Trigger the native stream flag
            response_stream = ollama.chat(
                model=self.model,
                messages=self.history,
                stream=True,
                options={"num_gpu": 99, "num_ctx": 2048}
            )   
            
            full_reply = ""
            for chunk in response_stream:
                token = chunk['message']['content']
                full_reply += token
                yield token  # Hand the token over to the terminal instantly
                
            # Lock the full completed sentence into memory context
            self.history.append({'role': 'assistant', 'content': full_reply})
            
        except Exception as e:
            yield f"\nCognitive stream exception: {str(e)}"