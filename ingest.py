from fastembed import TextEmbedding
from qdrant_client import QdrantClient
from qdrant_client.models import VectorParams, Distance, PointStruct
from chunking import load_chunks

COLLECTION = "cse_regs"
emb = TextEmbedding("BAAI/bge-small-en-v1.5", cache_dir="E:/AdviseBot/models")
chunks = load_chunks("docs/cse_regulations.pdf")
print(len(chunks), "chunks; embedding...", flush=True)
vecs = list(emb.embed([c["text"] for c in chunks]))

client = QdrantClient(path="qdrant_data")
if client.collection_exists(COLLECTION):
    client.delete_collection(COLLECTION)
client.create_collection(COLLECTION, vectors_config=VectorParams(size=len(vecs[0]), distance=Distance.COSINE))
client.upsert(COLLECTION, points=[PointStruct(id=i, vector=v.tolist(), payload=c) for i, (v, c) in enumerate(zip(vecs, chunks))])
print("stored", client.count(COLLECTION).count, "chunks in", COLLECTION)
client.close()
