import { createAgentSession } from "@mariozechner/pi-coding-agent";

process.env.OPENAI_API_KEY = "ollama-local-test";

const model = {
  id: "qwen2.5:3b",
  name: "Qwen 2.5 3B (Ollama)",
  api: "openai-completions",
  provider: "openai",
  baseUrl: "http://localhost:11434/v1",
  reasoning: false,
  input: ["text"],
  cost: {
    input: 0,
    output: 0,
    cacheRead: 0,
    cacheWrite: 0
  },
  contextWindow: 8192,
  maxTokens: 2048
};

const { session } = await createAgentSession({
  model,
  tools: [],
  sessionManager: undefined
});

let responseText = "";

const unsubscribe = session.subscribe((event) => {
  if (event.type === "message_end" && event.message.role === "assistant") {
    const content = event.message.content;
    if (Array.isArray(content)) {
      responseText = content
        .filter((item) => item.type === "text")
        .map((item) => item.text)
        .join("");
    }
  }
});

try {
  await session.prompt("Reply with exactly: Pi connected to local Ollama.");
  console.log("\n--- PI RESPONSE ---\n");
  console.log(responseText || "(No text response captured. We will inspect the events next.)");
} catch (error) {
  console.error("Pi + Ollama test failed:", error);
  process.exitCode = 1;
} finally {
  unsubscribe();
  session.dispose();
}


