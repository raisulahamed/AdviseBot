from dotenv import load_dotenv
load_dotenv()
import os, requests
r = requests.get("https://api.groq.com/openai/v1/models",
                 headers={"Authorization": "Bearer " + os.environ["GROQ_API_KEY"]}, timeout=20)
for m in sorted(x["id"] for x in r.json()["data"]):
    print(m)
