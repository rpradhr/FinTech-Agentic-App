import { createFileRoute } from "@tanstack/react-router";
import { useMutation } from "@tanstack/react-query";
import { useState, useRef, useEffect } from "react";
import { ApiError, endpoints, type ChatCard, type ChatQueryResponse } from "@/lib/api";
import { Surface, PageHeader, M3Button, Chip } from "@/components/m3";
import { Send, Bot, User } from "lucide-react";

export const Route = createFileRoute("/chat")({
  head: () => ({
    meta: [
      { title: "Assistant — FinTech Agentic" },
      { name: "description", content: "Natural-language interface to all banking agents." },
    ],
  }),
  component: ChatPage,
});

interface Msg {
  role: "user" | "assistant";
  content: string;
  cards?: ChatCard[];
  agent?: string;
}

function ChatPage() {
  const [messages, setMessages] = useState<Msg[]>([
    {
      role: "assistant",
      content:
        "Hi — I route your question to the right agent (fraud, loans, advisory, branches, sentiment). Try: 'Show me high-risk fraud alerts'.",
    },
  ]);
  const [input, setInput] = useState("");
  const scrollRef = useRef<HTMLDivElement>(null);

  const send = useMutation({
    mutationFn: (msg: string) =>
      endpoints.chatQuery(
        msg,
        messages.map((m) => ({ role: m.role, content: m.content })),
      ),
    onSuccess: (resp: ChatQueryResponse) => {
      setMessages((m) => [
        ...m,
        { role: "assistant", content: resp.content, cards: resp.cards, agent: resp.agent_type },
      ]);
    },
    onError: (e: ApiError) => {
      setMessages((m) => [...m, { role: "assistant", content: `⚠️ ${e.message}` }]);
    },
  });

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [messages, send.isPending]);

  const submit = (e: React.FormEvent) => {
    e.preventDefault();
    const text = input.trim();
    if (!text || send.isPending) return;
    setMessages((m) => [...m, { role: "user", content: text }]);
    setInput("");
    send.mutate(text);
  };

  return (
    <div>
      <PageHeader
        eyebrow="Assistant"
        title="Ask any agent"
        subtitle="Natural-language access to every workbench. The router classifies your intent and dispatches it."
      />

      <Surface tone="container" className="flex h-[70vh] flex-col p-0">
        <div ref={scrollRef} className="flex-1 space-y-4 overflow-auto p-6">
          {messages.map((m, i) => (
            <div key={i} className={`flex gap-3 ${m.role === "user" ? "flex-row-reverse" : ""}`}>
              <div
                className={`grid h-9 w-9 shrink-0 place-items-center rounded-full ${
                  m.role === "user" ? "bg-primary text-primary-foreground" : "bg-secondary text-secondary-foreground"
                }`}
              >
                {m.role === "user" ? <User className="h-4 w-4" /> : <Bot className="h-4 w-4" />}
              </div>
              <div className={`max-w-[80%] ${m.role === "user" ? "text-right" : ""}`}>
                {m.agent && (
                  <div className="mb-1">
                    <Chip tone="primary">{m.agent}</Chip>
                  </div>
                )}
                <div
                  className={`inline-block whitespace-pre-wrap rounded-2xl px-4 py-2.5 text-sm ${
                    m.role === "user"
                      ? "bg-primary text-primary-foreground"
                      : "bg-surface text-on-surface border border-outline-variant"
                  }`}
                >
                  {m.content}
                </div>
                {m.cards && m.cards.length > 0 && (
                  <div className="mt-3 grid gap-2 sm:grid-cols-2">
                    {m.cards.map((c, j) => (
                      <div
                        key={j}
                        className="rounded-2xl border border-outline-variant bg-surface p-3 text-left"
                      >
                        <div className="flex items-center justify-between">
                          <div className="text-xs font-semibold uppercase tracking-wider text-on-surface-variant">
                            {c.type}
                          </div>
                          {c.status && <Chip tone="info">{c.status}</Chip>}
                        </div>
                        <div className="mt-1 font-semibold text-on-surface">{c.title}</div>
                        {c.value && <div className="text-xl font-bold text-primary">{c.value}</div>}
                        {c.subtitle && (
                          <div className="text-xs text-on-surface-variant">{c.subtitle}</div>
                        )}
                        {c.items && c.items.length > 0 && (
                          <ul className="mt-2 list-inside list-disc text-xs text-on-surface-variant">
                            {c.items.map((it, k) => (
                              <li key={k}>{it}</li>
                            ))}
                          </ul>
                        )}
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          ))}
          {send.isPending && (
            <div className="flex gap-3">
              <div className="grid h-9 w-9 place-items-center rounded-full bg-secondary text-secondary-foreground">
                <Bot className="h-4 w-4" />
              </div>
              <div className="rounded-2xl border border-outline-variant bg-surface px-4 py-2.5">
                <span className="inline-flex gap-1">
                  <span className="h-2 w-2 animate-bounce rounded-full bg-on-surface-variant [animation-delay:-0.3s]" />
                  <span className="h-2 w-2 animate-bounce rounded-full bg-on-surface-variant [animation-delay:-0.15s]" />
                  <span className="h-2 w-2 animate-bounce rounded-full bg-on-surface-variant" />
                </span>
              </div>
            </div>
          )}
        </div>

        <form onSubmit={submit} className="border-t border-outline-variant p-3">
          <div className="flex items-center gap-2 rounded-full border border-outline bg-surface px-4 py-1">
            <input
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Ask the agents anything…"
              className="h-11 flex-1 bg-transparent text-sm outline-none placeholder:text-on-surface-variant"
            />
            <M3Button type="submit" size="sm" disabled={send.isPending || !input.trim()}>
              <Send className="h-4 w-4" />
              Send
            </M3Button>
          </div>
        </form>
      </Surface>
    </div>
  );
}
