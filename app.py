from groq import APIError, RateLimitError

from agent.research import ResearchAgent


def print_result(result):
    print("AI:", result["text"])

    if result["queries"]:
        print("\nSearched:")
        for query in result["queries"]:
            print(f"- {query}")

    if result["sources"]:
        print("\nSources:")
        for index, source in enumerate(result["sources"], start=1):
            kind = source.get("source", "web")
            print(f"{index}. [{kind}] {source['title']}")
            print(f"   {source['url']}")


def print_api_error(exc):
    message = getattr(exc, "message", None) or str(exc)
    if "invalid_api_key" in message or "401" in message:
        print(
            "Groq rejected the API key (401). Open https://console.groq.com/keys "
            "create a new key, paste it into .env as GROQ_API_KEY=gsk_..., "
            "save the file, and run app.py again. Do not wrap the key in quotes."
        )
        return
    if "model_not_found" in message or "does not exist" in message:
        print(
            "Groq model is not available on this key. "
            "The app now uses openai/gpt-oss-20b and groq/compound. "
            "Restart app.py."
        )
        return
    if "request_too_large" in message or "413" in message:
        print(
            "The prompt was too large for Groq. "
            "Restart app.py; evidence size is now capped."
        )
        return
    print(f"Groq API error: {message}")


def main():
    print("Multi-source RAG agent (Groq). Empty line to quit.")
    print("Add files to data/ then run: python -m rag.ingest")
    print("Supported: pdf, txt, md, csv, xlsx, sqlite .db")
    agent = ResearchAgent()
    while True:
        question = input("You: ").strip()
        if not question:
            break
        try:
            result = agent.ask(question)
        except RuntimeError as exc:
            print(exc)
            print()
            continue
        except (APIError, RateLimitError) as exc:
            print_api_error(exc)
            print()
            continue
        print_result(result)
        print()


if __name__ == "__main__":
    main()
