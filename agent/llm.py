import os
from dotenv import load_dotenv
from groq import Groq, BadRequestError

load_dotenv()
client = Groq(api_key=os.environ["GROQ_API_KEY"])
MODEL = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")

def chat(messages):
    r = client.chat.completions.create(model=MODEL, messages=messages)
    return r.choices[0].message.content

def chat_with_tools(messages, tools, retries=2):
    for i in range(retries + 1):
        try:
            r = client.chat.completions.create(
                model=MODEL, messages=messages, tools=tools, tool_choice="auto")
            return r.choices[0].message
        except BadRequestError as e:
            # Malformed tool call from the model: sampling again usually fixes it
            if "tool_use_failed" not in str(e) or i == retries:
                raise


if __name__ == "__main__":
    print(chat([{"role":"user", "content": "create a short story about cats in 100 words."}]))
