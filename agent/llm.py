import os
from dotenv import load_dotenv
from groq import Groq

load_dotenv()
client = Groq(api_key=os.environ["GROQ_API_KEY"])
MODEL = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")

def chat(messages):
    r = client.chat.completions.create(model=MODEL, messages=messages)
    return r.choices[0].message.content

if __name__ == "__main__":
    print(chat([{"role":"user", "content": "create a short story about cats in 100 words."}]))
