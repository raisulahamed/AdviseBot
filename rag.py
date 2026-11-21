from dotenv import load_dotenv
load_dotenv()
from fastembed import TextEmbedding
from qdrant_client import QdrantClient
from langchain.chat_models import init_chat_model
from langchain_core.messages import HumanMessage, SystemMessage

COLLECTION = "cse_regs"
emb = TextEmbedding("BAAI/bge-small-en-v1.5", cache_dir="E:/AdviseBot/models")
client = QdrantClient(path="qdrant_data")

main = init_chat_model("google_genai:gemini-3.8-flash", timeout=25, max_retries=0)
backup = init_chat_model("groq:openai/gpt-oss-20b", timeout=30)
model = main.with_fallbacks([backup])

SYSTEM = (
    "You are AdviseBot, a help desk assistant for CSE students. "
    "Answer ONLY from the numbered sources below. After every rule you state, cite it like [4.2, p.5], "
    "using the section number and page given with the source. "
    "If the sources do not answer the question, reply exactly: "
    "\"I don't have a source for that. Please ask the department office.\" "
    "Do not use outside knowledge. Keep the answer short."
)


def retrieve(question, k=4):
    vec = next(iter(emb.query_embed(question)))
    hits = client.query_points(COLLECTION, query=vec.tolist(), limit=k).points
    return [(h.payload, h.score) for h in hits]


def answer(question):
    hits = retrieve(question)
    sources = "\n\n".join(f"SOURCE [{p['section']}, p.{p['page']}] {p['text']}" for p, _ in hits)
    ai = model.invoke([SystemMessage(SYSTEM + "\n\n" + sources), HumanMessage(question)])
    return ai.content, hits


if __name__ == "__main__":
    for q in ["What happens if I get a D in a course, can I retake it?",
              "How many credits can I register for in a semester?",
              "What is the capital of France?"]:
        print("USER:", q, flush=True)
        text, hits = answer(q)
        print("BOT :", text)
        print("   retrieved:", [(p["section"], p["page"], round(s, 2)) for p, s in hits], "\n", flush=True)
    client.close()
