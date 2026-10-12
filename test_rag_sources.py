from backend.rag import retrieve_passages

passages = retrieve_passages("How can startups find product-market fit?")

print("Unique sources:", len(passages))

for item in passages:
    print("[{}] {} - {}".format(
        item["citation_id"],
        item["guest"],
        item["title"]
    ))
