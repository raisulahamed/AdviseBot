from dotenv import load_dotenv
load_dotenv()
from langchain.chat_models import init_chat_model

for name in ["groq:llama-3.3-70b-versatile", "google_genai:gemini-3.8-flash", "google_genai:gemini-2.5-flash"]:
    print("Trying", name, flush=True)
    try:
        m = init_chat_model(name, timeout=20, max_retries=0)
        print("OK  ", name, "->", m.invoke("Say hi in 3 words").content, flush=True)
    except Exception as e:
        print("FAIL", name, "->", str(e)[:400], flush=True)
