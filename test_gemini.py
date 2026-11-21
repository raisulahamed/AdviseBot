from dotenv import load_dotenv
load_dotenv()
from langchain.chat_models import init_chat_model
m = init_chat_model("google_genai:gemini-3.8-flash", timeout=90, max_retries=1)
print("Waiting...", flush=True)
print(m.invoke("Say hi in 3 words").content)
