from dotenv import load_dotenv
load_dotenv()
from langchain.chat_models import init_chat_model

main = init_chat_model("google_genai:gemini-3.8-flash", timeout=25, max_retries=0)
backup = init_chat_model("groq:openai/gpt-oss-20b", timeout=30)
model = main.with_fallbacks([backup])

print("Waiting...", flush=True)
print(model.invoke("Say hi in one short sentence.").content)
