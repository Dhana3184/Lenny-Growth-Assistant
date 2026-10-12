import { createAgentSession } from "@mariozechner/pi-coding-agent";

let input = "";
for await (const chunk of process.stdin) {
  input += chunk;
}

let session;

try {
  const request = JSON.parse(input);
  const provider = (request.provider || process.env.LLM_PROVIDER || "ollama").toLowerCase();

  let model;

  if (provider === "ollama") {
    process.env.OPENAI_API_KEY = "ollama-local-test";

    const baseUrl = (
      process.env.OLLAMA_BASE_URL || "http://localhost:11434"
    ).replace(/\/+$/, "");

    model = {
      id: process.env.OLLAMA_CHAT_MODEL || "qwen2.5:3b",
      name: "Qwen 2.5 3B (Ollama)",
      api: "openai-completions",
      provider: "openai",
      baseUrl: `${baseUrl}/v1`,
      reasoning: false,
      input: ["text"],
      cost: { input: 0, output: 0, cacheRead: 0, cacheWrite: 0 },
      contextWindow: 8192,
      maxTokens: 2048
    };
  } else if (provider === "openai") {
    if (!process.env.OPENAI_API_KEY) {
      throw new Error("OPENAI_API_KEY is required for the OpenAI provider.");
    }

    const { getModel } = await import("@mariozechner/pi-ai");
    model = getModel(
      "openai",
      process.env.OPENAI_MODEL || "gpt-4o-mini"
    );
  } else {
    throw new Error(`Unsupported LLM_PROVIDER: ${provider}`);
  }

  const { session: agentSession } = await createAgentSession({
    model,
    tools: []
  });
  session = agentSession;

  const prompt = [
    "You are Lenny Growth Assistant, a podcast-grounded product and growth assistant.",
    "Follow these instructions:",
    request.system_prompt || "",
    "",
    "USER QUESTION AND CONTEXT:",
    request.user_prompt || ""
  ].join("\n");

  let answer = "";

  session.subscribe((event) => {
    if (
      event.type === "message_end" &&
      event.message?.role === "assistant"
    ) {
      const content = event.message.content;
      if (Array.isArray(content)) {
        answer = content
          .filter((part) => part.type === "text")
          .map((part) => part.text)
          .join("\n");
      }
    }
  });

  await session.prompt(prompt);

  if (!answer.trim()) {
    throw new Error("Pi returned an empty response.");
  }

  process.stdout.write(JSON.stringify({ answer: answer.trim() }));
} catch (error) {
  console.error(error?.stack || String(error));
  process.exitCode = 1;
} finally {
  if (session) {
    await session.dispose();
  }
}
