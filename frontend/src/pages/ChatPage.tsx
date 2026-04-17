import { useState, useRef, useEffect, useCallback } from "react";
import clsx from "clsx";
// Lightweight inline markdown renderer (bold + italic only)
function InlineMd({ children }: { children: string }) {
  // Split on **bold** and *italic* patterns
  const parts = children.split(/(\*\*[^*]+\*\*|\*[^*]+\*)/g);
  return (
    <>
      {parts.map((part, i) => {
        if (part.startsWith("**") && part.endsWith("**"))
          return <strong key={i} className="font-semibold text-[#202124]">{part.slice(2, -2)}</strong>;
        if (part.startsWith("*") && part.endsWith("*"))
          return <em key={i}>{part.slice(1, -1)}</em>;
        return <span key={i}>{part}</span>;
      })}
    </>
  );
}
import {
  SAMPLE_FLOWS,
  SUGGESTED_PROMPTS,
  type ChatMessage,
  type AgentCard,
} from "@/data/sampleChats";
import { sendChatQuery } from "@/services/api";

// ── Agent colour/icon map ────────────────────────────────────────────────────
const AGENT_META: Record<
  string,
  { label: string; icon: string; accent: string; bg: string }
> = {
  fraud:      { label: "Fraud Agent",      icon: "security",        accent: "#c5221f", bg: "#fce8e6" },
  sentiment:  { label: "Sentiment Agent",  icon: "sentiment_very_dissatisfied", accent: "#e37400", bg: "#fef7e0" },
  loan:       { label: "Loan Agent",       icon: "account_balance", accent: "#1a73e8", bg: "#e8f0fe" },
  branch:     { label: "Branch Monitor",   icon: "storefront",      accent: "#137333", bg: "#e6f4ea" },
  advisory:   { label: "Advisory Agent",   icon: "tips_and_updates",accent: "#7b2d8b", bg: "#f3e8fd" },
  supervisor: { label: "Supervisor",       icon: "hub",             accent: "#5f6368", bg: "#f1f3f4" },
};

// ── Match user input to a sample flow ───────────────────────────────────────
function matchFlow(input: string): ChatMessage[] | null {
  const lower = input.toLowerCase();
  if (lower.includes("fraud") || lower.includes("c-asha001"))
    return SAMPLE_FLOWS.fraud ?? null;
  if (lower.includes("churn") || lower.includes("risk"))
    return SAMPLE_FLOWS.churn ?? null;
  if (lower.includes("loan") || lower.includes("l-001"))
    return SAMPLE_FLOWS.loan ?? null;
  if (lower.includes("branch") || lower.includes("west"))
    return SAMPLE_FLOWS.branch ?? null;
  if (lower.includes("advi") || lower.includes("recommend"))
    return SAMPLE_FLOWS.advice ?? null;
  return null;
}

// ── Agent Card component ─────────────────────────────────────────────────────
function AgentCardView({ card }: { card: AgentCard }) {
  const icons: Record<string, string> = {
    alert:    "warning",
    metric:   "bar_chart",
    action:   "check_circle",
    summary:  "summarize",
    evidence: "list_alt",
  };

  return (
    <div
      className="rounded-xl border overflow-hidden mt-2"
      style={{ borderColor: card.color ? `${card.color}30` : "#e0e0e0" }}
    >
      {/* Card header */}
      <div
        className="flex items-start gap-3 px-4 py-3"
        style={{
          background: card.color ? `${card.color}12` : "#f8f9fa",
          borderBottom: `1px solid ${card.color ? `${card.color}20` : "#e0e0e0"}`,
        }}
      >
        <span
          className="material-symbols-outlined text-[18px] mt-0.5 flex-shrink-0"
          style={{ color: card.color ?? "#5f6368" }}
        >
          {icons[card.type] ?? "info"}
        </span>
        <div className="flex-1 min-w-0">
          <p
            className="text-sm font-semibold leading-snug"
            style={{ color: card.color ?? "#202124" }}
          >
            {card.title}
          </p>
          {card.value && (
            <p className="text-base font-bold mt-0.5" style={{ color: card.color ?? "#202124" }}>
              {card.value}
            </p>
          )}
        </div>
        {card.status && (
          <span className="status-pill text-[10px] px-2 py-0.5 bg-white border rounded-full"
            style={{ color: card.color ?? "#5f6368", borderColor: `${card.color ?? "#5f6368"}40` }}>
            {card.status.replace(/_/g, " ")}
          </span>
        )}
      </div>

      {/* Card body */}
      {(card.subtitle || card.items?.length) && (
        <div className="px-4 py-3 space-y-2">
          {card.subtitle && (
            <p className="text-xs text-[#5f6368] leading-relaxed">{card.subtitle}</p>
          )}
          {card.items && card.items.length > 0 && (
            <ul className="space-y-1.5">
              {card.items.map((item, i) => (
                <li key={i} className="flex items-start gap-2 text-xs text-[#202124]">
                  <span
                    className="w-1.5 h-1.5 rounded-full mt-1.5 flex-shrink-0"
                    style={{ background: card.color ?? "#5f6368" }}
                  />
                  {item}
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
    </div>
  );
}

// ── Typing indicator ─────────────────────────────────────────────────────────
function TypingIndicator({ agentType }: { agentType?: string }) {
  const meta = AGENT_META[agentType ?? "supervisor"];
  return (
    <div className="flex items-end gap-3 animate-fade-in">
      {/* Avatar */}
      <div
        className="w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 text-white text-xs font-bold shadow-md-1"
        style={{ background: meta?.accent ?? "#1a73e8" }}
      >
        <span className="material-symbols-outlined text-[16px]">
          {meta?.icon ?? "smart_toy"}
        </span>
      </div>

      <div className="chat-bubble-agent flex items-center gap-1.5 px-4 py-3 !rounded-bl-sm">
        <span
          className="w-2 h-2 rounded-full animate-bounce"
          style={{ background: meta?.accent ?? "#1a73e8", animationDelay: "0ms" }}
        />
        <span
          className="w-2 h-2 rounded-full animate-bounce"
          style={{ background: meta?.accent ?? "#1a73e8", animationDelay: "150ms" }}
        />
        <span
          className="w-2 h-2 rounded-full animate-bounce"
          style={{ background: meta?.accent ?? "#1a73e8", animationDelay: "300ms" }}
        />
      </div>
    </div>
  );
}

// ── Message bubble ───────────────────────────────────────────────────────────
function MessageBubble({ msg }: { msg: ChatMessage }) {
  const isUser = msg.role === "user";
  const meta = msg.agentType ? AGENT_META[msg.agentType] : AGENT_META.supervisor;

  if (isUser) {
    return (
      <div className="flex justify-end animate-slide-up">
        <div className="max-w-[72%]">
          <div className="chat-bubble-user">
            <p className="text-sm leading-relaxed">{msg.content}</p>
          </div>
          <p className="text-[10px] text-[#9aa0a6] text-right mt-1">
            {new Date(msg.timestamp).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex items-start gap-3 animate-slide-up">
      {/* Agent avatar */}
      <div
        className="w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 text-white shadow-md-1 mt-1"
        style={{ background: meta?.accent ?? "#1a73e8" }}
      >
        <span className="material-symbols-outlined text-[16px]">
          {meta?.icon ?? "smart_toy"}
        </span>
      </div>

      <div className="flex-1 max-w-[82%] space-y-1">
        {/* Agent label */}
        <div className="flex items-center gap-2">
          <span
            className="text-[11px] font-semibold"
            style={{ color: meta?.accent ?? "#1a73e8" }}
          >
            {meta?.label ?? "Agent"}
          </span>
          {msg.agentType && (
            <span
              className="text-[10px] px-2 py-0.5 rounded-full font-medium"
              style={{ background: meta?.bg, color: meta?.accent }}
            >
              {msg.agentType}
            </span>
          )}
        </div>

        {/* Message content */}
        <div className="chat-bubble-agent">
          <p className="text-sm leading-relaxed">
            <InlineMd>{msg.content}</InlineMd>
          </p>

          {/* Agent cards */}
          {msg.cards && msg.cards.length > 0 && (
            <div className="space-y-2 mt-3 pt-3 border-t border-[#e0e0e0]">
              {msg.cards.map((card, i) => (
                <AgentCardView key={i} card={card} />
              ))}
            </div>
          )}
        </div>

        <p className="text-[10px] text-[#9aa0a6] mt-1">
          {new Date(msg.timestamp).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
        </p>
      </div>
    </div>
  );
}

// ── Welcome state ────────────────────────────────────────────────────────────
function WelcomeScreen({ onPrompt }: { onPrompt: (p: string) => void }) {
  return (
    <div className="flex flex-col items-center justify-center h-full px-6 py-12 animate-fade-in">
      {/* Gemini-style gradient logo */}
      <div className="w-16 h-16 rounded-2xl flex items-center justify-center mb-6 shadow-md-2"
        style={{ background: "linear-gradient(135deg, #1a73e8 0%, #0d47a1 50%, #6200ea 100%)" }}>
        <span className="material-symbols-outlined text-white text-[32px]">
          smart_toy
        </span>
      </div>

      <h1 className="text-2xl font-normal text-[#202124] mb-2">
        How can I help you today?
      </h1>
      <p className="text-sm text-[#5f6368] mb-10 text-center max-w-md">
        Ask me about fraud alerts, customer churn risk, loan applications,
        branch performance, or financial advice generation.
      </p>

      {/* Suggested prompt chips */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 w-full max-w-xl">
        {SUGGESTED_PROMPTS.map((sp) => (
          <button
            key={sp.label}
            onClick={() => onPrompt(sp.prompt)}
            className="group text-left px-4 py-3 rounded-2xl border border-[#dadce0]
              hover:border-[#1a73e8] hover:bg-[#f8f9ff]
              transition-all duration-150 shadow-sm hover:shadow-md-1"
          >
            <span className="text-xl mr-2">{sp.icon}</span>
            <span className="text-sm font-medium text-[#202124] group-hover:text-[#1a73e8]">
              {sp.label}
            </span>
            <p className="text-xs text-[#9aa0a6] mt-1 line-clamp-2 leading-snug">
              {sp.prompt}
            </p>
          </button>
        ))}
      </div>
    </div>
  );
}

// ── Main ChatPage ────────────────────────────────────────────────────────────
export default function ChatPage() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [typing, setTyping] = useState(false);
  const [typingAgent, setTypingAgent] = useState<string | undefined>();
  const [sessionLabel, setSessionLabel] = useState<string | null>(null);
  const [liveMode, setLiveMode] = useState<boolean | null>(null); // null = unknown
  const bottomRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  // Auto-scroll to bottom
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, typing]);

  // Auto-resize textarea
  const handleInputChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setInput(e.target.value);
    e.target.style.height = "auto";
    e.target.style.height = `${Math.min(e.target.scrollHeight, 160)}px`;
  };

  const sendMessage = useCallback(
    async (text: string) => {
      if (!text.trim()) return;
      setInput("");
      if (inputRef.current) {
        inputRef.current.style.height = "auto";
      }

      // Set session label from first message
      if (!sessionLabel) {
        setSessionLabel(text.slice(0, 40) + (text.length > 40 ? "…" : ""));
      }

      // Add user message
      const userMsg: ChatMessage = {
        id: `u-${Date.now()}`,
        role: "user",
        content: text,
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, userMsg]);

      // ── Attempt live backend ──────────────────────────────────────────
      const history = messages.map((m) => ({
        role: m.role,
        content: m.content,
      }));

      // Guess the typing agent from keyword before the response arrives
      const guessedAgent = matchFlow(text)?.find((m) => m.role === "agent")?.agentType;
      setTypingAgent(guessedAgent);
      setTyping(true);

      let responded = false;
      if (liveMode !== false) {
        try {
          const data = await sendChatQuery(text, history);
          setTyping(false);
          responded = true;
          if (liveMode === null) setLiveMode(true);
          const response: ChatMessage = {
            id: `a-${Date.now()}`,
            role: "agent",
            agentType: data.agent_type as ChatMessage["agentType"],
            content: data.content,
            cards: data.cards as AgentCard[],
            timestamp: new Date(),
          };
          setMessages((prev) => [...prev, response]);
        } catch {
          // Backend unavailable — switch to demo mode for the session
          if (liveMode === null) setLiveMode(false);
        }
      }

      // ── Demo fallback ─────────────────────────────────────────────────
      if (!responded) {
        const delay = 800 + Math.random() * 800;
        await new Promise((r) => setTimeout(r, delay));
        setTyping(false);

        const flow = matchFlow(text);
        const agentMsg = flow?.find((m) => m.role === "agent");
        if (flow && agentMsg) {
          setMessages((prev) => [
            ...prev,
            { ...agentMsg, id: `a-${Date.now()}`, timestamp: new Date() },
          ]);
        } else {
          setMessages((prev) => [
            ...prev,
            {
              id: `a-${Date.now()}`,
              role: "agent",
              agentType: "supervisor",
              content:
                "I don't have a specific dataset for that query in this demo. " +
                "Try asking about **fraud alerts**, **churn risk**, a **loan review**, " +
                "**branch operations**, or **customer advice**.",
              timestamp: new Date(),
            },
          ]);
        }
      }
    },
    [sessionLabel]
  );

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage(input);
    }
  };

  const clearChat = () => {
    setMessages([]);
    setSessionLabel(null);
  };

  const isEmpty = messages.length === 0 && !typing;

  return (
    <div className="flex flex-col h-[calc(100vh-64px)] bg-[#f8f9fa]">
      {/* ── Top bar ─────────────────────────────────────────────────── */}
      <div className="flex items-center justify-between px-6 py-3 bg-white border-b border-[#e0e0e0] shadow-sm">
        <div className="flex items-center gap-3">
          <span className="material-symbols-outlined text-[#1a73e8]">smart_toy</span>
          <div>
            <h2 className="text-sm font-semibold text-[#202124]">
              {sessionLabel ?? "Ask the Agents"}
            </h2>
            <p className="text-xs text-[#9aa0a6]">Multi-agent banking assistant</p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          {/* Agent capability chips */}
          {(["fraud", "sentiment", "loan", "branch", "advisory"] as const).map((t) => {
            const m = AGENT_META[t];
            return (
              <span
                key={t}
                className="hidden md:inline-flex items-center gap-1 text-[11px] px-2.5 py-1
                  rounded-full font-medium border"
                style={{ color: m.accent, borderColor: `${m.accent}40`, background: m.bg }}
              >
                <span className="material-symbols-outlined text-[12px]">{m.icon}</span>
                {m.label.split(" ")[0]}
              </span>
            );
          })}

          {messages.length > 0 && (
            <button
              onClick={clearChat}
              className="ml-2 p-2 rounded-full hover:bg-[#f1f3f4] transition-colors
                text-[#5f6368] hover:text-[#202124]"
              title="New conversation"
            >
              <span className="material-symbols-outlined text-[20px]">add_comment</span>
            </button>
          )}
        </div>
      </div>

      {/* ── Messages area ──────────────────────────────────────────── */}
      <div className="flex-1 overflow-y-auto">
        {isEmpty ? (
          <WelcomeScreen onPrompt={sendMessage} />
        ) : (
          <div className="max-w-3xl mx-auto px-4 py-6 space-y-6">
            {messages.map((msg) => (
              <MessageBubble key={msg.id} msg={msg} />
            ))}
            {typing && <TypingIndicator agentType={typingAgent} />}
            <div ref={bottomRef} />
          </div>
        )}
      </div>

      {/* ── Input bar ──────────────────────────────────────────────── */}
      <div className="bg-white border-t border-[#e0e0e0] px-4 py-3">
        <div className="max-w-3xl mx-auto">
          {/* Quick chips (only when no messages yet) */}
          {isEmpty && (
            <div className="flex gap-2 mb-3 flex-wrap">
              {SUGGESTED_PROMPTS.map((sp) => (
                <button
                  key={sp.label}
                  onClick={() => sendMessage(sp.prompt)}
                  className="chip text-xs hover:bg-[#e8f0fe] hover:border-[#1a73e8]
                    hover:text-[#1a73e8] transition-colors"
                >
                  {sp.icon} {sp.label}
                </button>
              ))}
            </div>
          )}

          {/* Text input */}
          <div className="flex items-end gap-3 bg-[#f1f3f4] rounded-2xl px-4 py-2
            focus-within:ring-2 focus-within:ring-[#1a73e8] focus-within:bg-white
            transition-all duration-150">
            <span className="material-symbols-outlined text-[#9aa0a6] text-[20px] mb-1.5 flex-shrink-0">
              keyboard
            </span>

            <textarea
              ref={inputRef}
              rows={1}
              value={input}
              onChange={handleInputChange}
              onKeyDown={handleKeyDown}
              placeholder="Ask about fraud, loans, customers, branches…"
              className="flex-1 resize-none bg-transparent text-sm text-[#202124]
                placeholder-[#9aa0a6] outline-none py-1.5 leading-relaxed max-h-40"
            />

            <button
              onClick={() => sendMessage(input)}
              disabled={!input.trim() || typing}
              className={clsx(
                "mb-1 p-2 rounded-full transition-all duration-150 flex-shrink-0",
                input.trim() && !typing
                  ? "bg-[#1a73e8] text-white hover:bg-[#1557b0] shadow-md-1"
                  : "text-[#dadce0] cursor-not-allowed"
              )}
            >
              <span className="material-symbols-outlined text-[20px]">send</span>
            </button>
          </div>

          <p className="text-[10px] text-center mt-2"
            style={{ color: liveMode ? "#34a853" : "#9aa0a6" }}>
            {liveMode
              ? "Live mode — responses from real agent data."
              : liveMode === false
              ? "Demo mode — backend unavailable, using sample data."
              : "Connecting to agent backend…"}
          </p>
        </div>
      </div>
    </div>
  );
}
