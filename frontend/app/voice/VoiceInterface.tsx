"use client";
import { useEffect, useState, useRef, useCallback } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { ArrowLeft, Send, ChevronDown, Mic, Square, Loader2, Lightbulb, X } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import Navbar from "@/components/layout/Navbar";
import ChatArea, { Message } from "@/components/voice/ChatArea";
import { DOMAINS, LANGUAGES, Domain } from "@/lib/domains";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
type OrbState = "idle" | "connecting" | "active";

const fmt = (d: Date) => d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
const uid = () => Math.random().toString(36).slice(2);

export default function VoiceInterface() {
  const router = useRouter();
  const params = useSearchParams();
  const domain: Domain = DOMAINS.find((d) => d.id === params.get("domain")) ?? DOMAINS[0];

  const [messages, setMessages] = useState<Message[]>([]);
  const [isTyping, setIsTyping] = useState(false);
  const [textInput, setTextInput] = useState("");
  const [orbState, setOrbState] = useState<OrbState>("idle");
  const [lang, setLang] = useState("en");
  const [timerSecs, setTimerSecs] = useState(0);
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const vapiRef = useRef<unknown>(null);
  const assistantMsgIdRef = useRef<string | null>(null);
  const assistantCommittedRef = useRef<string>("");
  const userMsgIdRef = useRef<string | null>(null);

  /* Reset messages when domain changes */
  useEffect(() => {
    setMessages([]);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [domain.id]);

  /* Timer */
  const startTimer = useCallback(() => {
    setTimerSecs(0);
    timerRef.current = setInterval(() => setTimerSecs((s) => s + 1), 1000);
  }, []);
  const stopTimer = useCallback(() => {
    if (timerRef.current) clearInterval(timerRef.current);
    setTimerSecs(0);
  }, []);
  const timerDisplay = `${String(Math.floor(timerSecs / 60)).padStart(2, "0")}:${String(timerSecs % 60).padStart(2, "0")}`;

  /* Text send */
  const sendText = useCallback(async (q?: string) => {
    const query = (q ?? textInput).trim();
    if (!query) return;
    setTextInput("");
    setSidebarOpen(false);
    setMessages((p) => [...p, { id: uid(), role: "user", text: query, time: fmt(new Date()) }]);
    setIsTyping(true);
    try {
      const res = await fetch(`${API_BASE}/webhook`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          message: { functionCall: { parameters: { query, domain: domain.id } } },
          call: { id: "web-" + uid(), customer: { number: "web-user" }, duration: 0 },
        }),
      });
      const data = await res.json();
      setIsTyping(false);

      let text: string;
      if (data.result === "ESCALATE") {
        text = "I'm not confident enough to answer this accurately. Please call helpline 14555 or visit your nearest Common Service Centre.";
      } else {
        text = data.result;
        if (data.sources?.length) {
          const unique = [...new Set(data.sources as string[])].filter(Boolean);
          if (unique.length) text += `\n\nSource: ${unique.join(", ")}`;
        }
      }
      setMessages((p) => [...p, { id: uid(), role: "assistant", time: fmt(new Date()), text }]);
    } catch {
      setIsTyping(false);
      setMessages((p) => [...p, { id: uid(), role: "assistant", text: "Server error. Please try again.", time: fmt(new Date()) }]);
    }
  }, [textInput, domain.id]);

  /* Voice */
  const startCall = useCallback(async () => {
    const key = process.env.NEXT_PUBLIC_VAPI_KEY;
    const aid = process.env.NEXT_PUBLIC_VAPI_ASSISTANT_ID;
    if (!key || !aid) {
      setMessages((p) => [...p, {
        id: uid(), role: "assistant", time: fmt(new Date()),
        text: "Voice agent is not connected yet — use the text input below in the meantime!",
      }]);
      return;
    }
    setOrbState("connecting");
    try {
      const { default: Vapi } = await import("@vapi-ai/web");
      const vapi = new Vapi(key);
      vapiRef.current = vapi;
      const resetAssistant = () => {
        assistantMsgIdRef.current = null;
        assistantCommittedRef.current = "";
      };
      const resetUser = () => { userMsgIdRef.current = null; };

      vapi.on("call-start", () => { setOrbState("active"); startTimer(); });
      vapi.on("call-end", () => {
        setMessages((p) => p.map((m) => m.partial ? { ...m, partial: false } : m));
        resetAssistant(); resetUser();
        setOrbState("idle"); stopTimer();
      });

      vapi.on("message", (m: { type: string; transcriptType?: string; role?: string; transcript?: string }) => {
        if (m.type !== "transcript" || !m.transcript) return;
        const text = m.transcript;
        const isFinal = m.transcriptType === "final";

        if (m.role === "user") {
          if (!isFinal) return;
          setMessages((p) => p.map((msg) => msg.partial ? { ...msg, partial: false } : msg));
          resetAssistant();
          if (!userMsgIdRef.current) {
            const id = uid();
            userMsgIdRef.current = id;
            setMessages((p) => [...p, { id, role: "user", text, time: fmt(new Date()) }]);
          } else {
            setMessages((p) => p.map((msg) =>
              msg.id === userMsgIdRef.current ? { ...msg, text: msg.text + " " + text } : msg
            ));
          }
          return;
        }

        if (m.role === "assistant") {
          resetUser();
          if (isFinal) {
            assistantCommittedRef.current = assistantCommittedRef.current
              ? assistantCommittedRef.current + " " + text : text;
            if (!assistantMsgIdRef.current) {
              const id = uid();
              assistantMsgIdRef.current = id;
              setMessages((p) => [...p, { id, role: "assistant", text: assistantCommittedRef.current, time: fmt(new Date()), partial: false }]);
            } else {
              setMessages((p) => p.map((msg) =>
                msg.id === assistantMsgIdRef.current
                  ? { ...msg, text: assistantCommittedRef.current, partial: false } : msg
              ));
            }
          } else {
            const displayText = assistantCommittedRef.current
              ? assistantCommittedRef.current + " " + text : text;
            if (!assistantMsgIdRef.current) {
              const id = uid();
              assistantMsgIdRef.current = id;
              setMessages((p) => [...p, { id, role: "assistant", text: displayText, time: fmt(new Date()), partial: true }]);
            } else {
              setMessages((p) => p.map((msg) =>
                msg.id === assistantMsgIdRef.current
                  ? { ...msg, text: displayText, partial: true } : msg
              ));
            }
          }
        }
      });
      vapi.on("error", () => { setOrbState("idle"); stopTimer(); });

      const deepgramLangMap: Record<string, string> = {
        en: "en", hi: "hi", ta: "ta", kn: "kn",
        te: "multi", mr: "multi", bn: "multi", ml: "multi",
      };
      const deepgramLang = deepgramLangMap[lang] ?? "multi";
      vapi.start(aid, {
        transcriber: { provider: "deepgram", model: "nova-3-general", language: deepgramLang },
        variableValues: { language: lang, languageLabel: LANGUAGES.find(l => l.code === lang)?.label ?? "English" },
      } as Parameters<typeof vapi.start>[1]);
    } catch { setOrbState("idle"); }
  }, [startTimer, stopTimer, lang]);

  const endCall = useCallback(() => {
    try { (vapiRef.current as { stop: () => void })?.stop(); } catch {}
    setOrbState("idle"); stopTimer();
  }, [stopTimer]);

  const toggleCall = useCallback(() => {
    if (orbState === "active") endCall();
    else if (orbState === "idle") startCall();
  }, [orbState, startCall, endCall]);

  const isActive = orbState === "active";
  const isConnecting = orbState === "connecting";

  return (
    <div className="h-screen bg-white dark:bg-[#0c0c0c] flex flex-col overflow-hidden">
      <Navbar callActive={isActive} />

      {/* Main area */}
      <div className="flex flex-1 min-h-0">

        {/* Right sidebar — Explore Queries */}
        <AnimatePresence>
          {sidebarOpen && (
            <>
              <motion.div
                initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
                className="fixed inset-0 z-20 bg-black/20 dark:bg-black/40"
                onClick={() => setSidebarOpen(false)}
              />
              <motion.aside
                initial={{ x: "100%" }}
                animate={{ x: 0 }}
                exit={{ x: "100%" }}
                transition={{ type: "spring", stiffness: 280, damping: 28 }}
                className="fixed right-0 top-0 z-30 h-full w-full sm:w-1/2 bg-white dark:bg-[#111] border-l border-zinc-200 dark:border-zinc-800 flex flex-col pt-14 shadow-2xl"
              >
                <div className="flex items-center justify-between px-4 py-3 border-b border-zinc-100 dark:border-zinc-800">
                  <div className="flex items-center gap-2">
                    <span className="text-lg">{domain.icon}</span>
                    <span className="text-sm font-semibold text-zinc-900 dark:text-zinc-100">Explore queries</span>
                  </div>
                  <button onClick={() => setSidebarOpen(false)} className="p-1 rounded-lg hover:bg-zinc-100 dark:hover:bg-zinc-800 text-zinc-400">
                    <X size={15} />
                  </button>
                </div>
                <div className="flex-1 overflow-y-auto px-3 py-4 flex flex-col gap-5">
                  {domain.questionGroups.map((group) => (
                    <div key={group.topic}>
                      {/* Topic header */}
                      <div className="flex items-center gap-2 mb-2 px-1">
                        <span className="text-base leading-none">{group.icon}</span>
                        <span className="text-[11px] font-semibold uppercase tracking-wider text-zinc-400 dark:text-zinc-500">{group.topic}</span>
                      </div>
                      {/* Questions */}
                      <div className="flex flex-col gap-1.5">
                        {group.questions.map((q) => (
                          <button
                            key={q}
                            onClick={() => sendText(q)}
                            className="text-left text-[13px] px-3 py-2 rounded-lg bg-zinc-50 dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 text-zinc-700 dark:text-zinc-300 hover:bg-indigo-50 dark:hover:bg-indigo-950/40 hover:border-indigo-200 dark:hover:border-indigo-800 hover:text-indigo-700 dark:hover:text-indigo-300 transition-colors leading-snug"
                          >
                            {q}
                          </button>
                        ))}
                      </div>
                    </div>
                  ))}
                </div>
                <div className="px-3 py-2.5 border-t border-zinc-100 dark:border-zinc-800 bg-zinc-50/50 dark:bg-zinc-900/50">
                  <p className="text-[11px] text-zinc-400 text-center">Tap any question to send it instantly</p>
                </div>
              </motion.aside>
            </>
          )}
        </AnimatePresence>

        {/* Chat column */}
        <div className="flex-1 flex flex-col min-w-0">

          {/* Domain header bar */}
          <div className="flex-shrink-0 px-4 py-2.5 border-b border-zinc-100 dark:border-zinc-800 flex items-center gap-3 bg-white dark:bg-[#0c0c0c]">
            <button
              onClick={() => router.push("/")}
              className="flex items-center gap-1 text-xs text-zinc-400 hover:text-zinc-700 dark:hover:text-zinc-200 transition-colors flex-shrink-0"
            >
              <ArrowLeft size={13} /> Back
            </button>
            <div className="w-px h-4 bg-zinc-200 dark:bg-zinc-700" />
            <span className="text-lg flex-shrink-0">{domain.icon}</span>
            <div className="flex-1 min-w-0">
              <div className="text-sm font-semibold text-zinc-900 dark:text-zinc-100 truncate leading-tight">{domain.name}</div>
              <div className="text-[11px] text-zinc-400 truncate leading-tight hidden sm:block">{domain.description}</div>
            </div>

            {/* Live indicator */}
            {isActive && (
              <div className="flex items-center gap-1.5 text-xs font-medium text-red-500 flex-shrink-0">
                <span className="w-1.5 h-1.5 rounded-full bg-red-500 animate-pulse" />
                {timerDisplay}
              </div>
            )}

            {/* Language */}
            <div className="relative flex-shrink-0">
              <select
                value={lang}
                onChange={(e) => setLang(e.target.value)}
                className="appearance-none text-xs bg-zinc-100 dark:bg-zinc-800 border-0 text-zinc-700 dark:text-zinc-300 rounded-lg pl-2.5 pr-6 py-1.5 outline-none cursor-pointer"
              >
                {LANGUAGES.map((l) => (
                  <option key={l.code} value={l.code}>{l.nativeLabel}</option>
                ))}
              </select>
              <ChevronDown size={10} className="absolute right-1.5 top-1/2 -translate-y-1/2 text-zinc-400 pointer-events-none" />
            </div>
          </div>

          {/* Messages or empty state */}
          <div className="flex-1 min-h-0 relative">
            <AnimatePresence mode="wait">
              {messages.length === 0 && !isTyping ? (
                <motion.div
                  key="empty"
                  initial={{ opacity: 0, y: 16 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -12 }}
                  transition={{ duration: 0.35 }}
                  className="absolute inset-0 flex flex-col items-center justify-center px-6 text-center gap-5"
                >
                  <div className="text-6xl mb-1 select-none">{domain.icon}</div>
                  <div>
                    <h1 className="text-2xl sm:text-3xl font-bold text-zinc-900 dark:text-zinc-100 mb-2">
                      How can I help you?
                    </h1>
                    <p className="text-sm text-zinc-500 dark:text-zinc-400 max-w-sm leading-relaxed">
                      Ask me anything about <span className="text-zinc-700 dark:text-zinc-300 font-medium">{domain.name}</span> — schemes, eligibility, documents, or how to apply.
                    </p>
                  </div>

                  {/* Quick-pick chips from first group */}
                  <div className="flex flex-wrap gap-2 justify-center max-w-lg mt-1">
                    {domain.questionGroups[0]?.questions.map((q) => (
                      <button
                        key={q}
                        onClick={() => sendText(q)}
                        className="text-xs px-3.5 py-2 rounded-full border border-zinc-200 dark:border-zinc-700 text-zinc-600 dark:text-zinc-300 hover:border-indigo-300 dark:hover:border-indigo-700 hover:bg-indigo-50 dark:hover:bg-indigo-950/40 hover:text-indigo-700 dark:hover:text-indigo-300 transition-colors"
                      >
                        {q}
                      </button>
                    ))}
                  </div>

                  <p className="text-[11px] text-zinc-400 mt-1">
                    Or tap <span className="font-medium">Explore queries</span> for more questions →
                  </p>
                </motion.div>
              ) : (
                <motion.div
                  key="chat"
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  className="absolute inset-0"
                >
                  <ChatArea messages={messages} isTyping={isTyping} />
                </motion.div>
              )}
            </AnimatePresence>
          </div>

          {/* Bottom input bar */}
          <div className="flex-shrink-0 border-t border-zinc-100 dark:border-zinc-800 px-3 py-3 bg-white dark:bg-[#0c0c0c]">
            <div className="flex items-center gap-2 max-w-4xl mx-auto">

              {/* Explore Queries button */}
              <button
                onClick={() => setSidebarOpen((v) => !v)}
                className={`flex-shrink-0 flex items-center gap-1.5 px-3 h-9 rounded-xl text-xs font-medium transition-colors ${
                  sidebarOpen
                    ? "bg-indigo-500 text-white"
                    : "bg-zinc-100 dark:bg-zinc-800 text-zinc-500 hover:text-zinc-900 dark:hover:text-zinc-100"
                }`}
              >
                <Lightbulb size={14} />
                <span className="hidden sm:inline">Explore queries</span>
              </button>

              {/* Text input */}
              <input
                type="text"
                value={textInput}
                onChange={(e) => setTextInput(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && sendText()}
                placeholder="Type your question…"
                className="flex-1 bg-zinc-50 dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-700 rounded-xl px-4 py-2.5 text-sm text-zinc-900 dark:text-zinc-100 placeholder-zinc-400 outline-none focus:border-zinc-400 dark:focus:border-zinc-500 transition-colors"
              />

              {/* Mic / Voice button */}
              <button
                onClick={toggleCall}
                disabled={isConnecting}
                title={isActive ? "End call" : "Start voice call"}
                className={`flex-shrink-0 w-9 h-9 rounded-xl flex items-center justify-center transition-colors ${
                  isActive
                    ? "bg-red-500 text-white shadow-[0_0_0_3px_rgba(239,68,68,0.2)]"
                    : isConnecting
                    ? "bg-zinc-200 dark:bg-zinc-700 text-zinc-400 cursor-not-allowed"
                    : "bg-zinc-900 dark:bg-zinc-100 text-white dark:text-zinc-900 hover:bg-zinc-700 dark:hover:bg-zinc-200"
                }`}
              >
                <AnimatePresence mode="wait">
                  {isConnecting ? (
                    <motion.span key="spin" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
                      <Loader2 size={16} className="animate-spin" />
                    </motion.span>
                  ) : isActive ? (
                    <motion.span key="stop" initial={{ scale: 0.6, opacity: 0 }} animate={{ scale: 1, opacity: 1 }} exit={{ scale: 0.6, opacity: 0 }}>
                      <Square size={14} fill="currentColor" />
                    </motion.span>
                  ) : (
                    <motion.span key="mic" initial={{ scale: 0.6, opacity: 0 }} animate={{ scale: 1, opacity: 1 }} exit={{ scale: 0.6, opacity: 0 }}>
                      <Mic size={16} />
                    </motion.span>
                  )}
                </AnimatePresence>
              </button>

              {/* Send button */}
              <button
                onClick={() => sendText()}
                className="flex-shrink-0 w-9 h-9 rounded-xl bg-indigo-500 hover:bg-indigo-600 flex items-center justify-center text-white transition-colors"
              >
                <Send size={14} />
              </button>
            </div>

            {/* Mic state hint */}
            <AnimatePresence>
              {(isActive || isConnecting) && (
                <motion.div
                  initial={{ opacity: 0, y: 4 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: 4 }}
                  className="flex items-center justify-center gap-2 mt-2"
                >
                  {isActive ? (
                    <>
                      <span className="flex gap-0.5">
                        {[0, 1, 2, 3].map((i) => (
                          <span key={i} className="w-0.5 bg-red-400 rounded-full animate-[typingBounce_1s_infinite]" style={{ height: 12 + (i % 2) * 6, animationDelay: `${i * 0.15}s` }} />
                        ))}
                      </span>
                      <span className="text-[11px] text-red-500 font-medium">Listening — tap mic to end</span>
                    </>
                  ) : (
                    <span className="text-[11px] text-zinc-400">Connecting…</span>
                  )}
                </motion.div>
              )}
            </AnimatePresence>
          </div>
        </div>
      </div>
    </div>
  );
}
