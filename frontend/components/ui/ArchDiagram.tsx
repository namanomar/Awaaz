"use client";
import { motion, AnimatePresence } from "framer-motion";
import { useState, useEffect } from "react";

const STEPS = [
  { id: 0, label: "User calls / speaks",   sub: "Phone or web browser" },
  { id: 1, label: "Speech to Text",        sub: "Multilingual STT via Vapi" },
  { id: 2, label: "Intent & Language",     sub: "Detect topic and language" },
  { id: 3, label: "Vector Search",         sub: "Qdrant knowledge base" },
  { id: 4, label: "LLM Orchestration",     sub: "Context-grounded answer" },
  { id: 5, label: "Text to Speech",        sub: "Voice response in your language" },
  { id: 6, label: "Escalation",            sub: "Human handoff if unsure" },
];

const BLOCKS = [
  { id: "user",    x: 60,  y: 40,  w: 90, h: 44, label: "User",      step: 0, color: "#6b7280" },
  { id: "vapi",   x: 60,  y: 120, w: 90, h: 44, label: "Vapi STT",  step: 1, color: "#3b82f6" },
  { id: "intent", x: 200, y: 120, w: 90, h: 44, label: "Intent",    step: 2, color: "#8b5cf6" },
  { id: "qdrant", x: 340, y: 100, w: 90, h: 64, label: "Qdrant",    step: 3, color: "#10b981" },
  { id: "llm",    x: 200, y: 200, w: 90, h: 44, label: "LLM",       step: 4, color: "#f59e0b" },
  { id: "tts",    x: 60,  y: 200, w: 90, h: 44, label: "TTS",       step: 5, color: "#ec4899" },
  { id: "esc",    x: 340, y: 200, w: 90, h: 44, label: "Escalate",  step: 6, color: "#ef4444" },
];

const EDGES = [
  { from: "user",    to: "vapi",   d: "M105,84 L105,120" },
  { from: "vapi",   to: "intent", d: "M150,142 L200,142" },
  { from: "intent", to: "qdrant", d: "M290,138 L340,128" },
  { from: "qdrant", to: "llm",    d: "M385,164 L340,222" },  // actually: qdrant to llm
  { from: "intent", to: "llm",    d: "M245,164 L245,200" },
  { from: "llm",    to: "tts",    d: "M200,222 L150,222" },
  { from: "llm",    to: "esc",    d: "M290,222 L340,222" },
];

export default function ArchDiagram() {
  const [active, setActive] = useState(0);

  useEffect(() => {
    const t = setInterval(() => setActive((a) => (a + 1) % STEPS.length), 1800);
    return () => clearInterval(t);
  }, []);

  return (
    <div className="flex flex-col lg:flex-row gap-8 items-start">
      {/* Left: step list */}
      <div className="flex flex-col gap-1 min-w-[220px]">
        {STEPS.map((step) => (
          <button
            key={step.id}
            onClick={() => setActive(step.id)}
            className="flex items-start gap-3 px-3 py-2.5 rounded-lg text-left transition-all group"
          >
            <div className="mt-1 flex-shrink-0 relative">
              <div className={`w-2 h-2 rounded-full transition-colors duration-300 ${
                active === step.id ? "bg-emerald-500" : "bg-zinc-300 dark:bg-zinc-700"
              }`} />
              {active === step.id && (
                <motion.div
                  className="absolute inset-0 rounded-full bg-emerald-500"
                  initial={{ scale: 1, opacity: 0.6 }}
                  animate={{ scale: 2.5, opacity: 0 }}
                  transition={{ duration: 1, repeat: Infinity }}
                />
              )}
            </div>
            <div>
              <div className={`text-sm font-medium transition-colors ${
                active === step.id ? "text-zinc-900 dark:text-zinc-100" : "text-zinc-400 dark:text-zinc-600"
              }`}>
                {step.label}
              </div>
              <AnimatePresence>
                {active === step.id && (
                  <motion.div
                    initial={{ height: 0, opacity: 0 }}
                    animate={{ height: "auto", opacity: 1 }}
                    exit={{ height: 0, opacity: 0 }}
                    transition={{ duration: 0.2 }}
                    className="overflow-hidden"
                  >
                    <p className="text-xs text-zinc-500 mt-0.5">{step.sub}</p>
                  </motion.div>
                )}
              </AnimatePresence>
            </div>
          </button>
        ))}
      </div>

      {/* Right: animated SVG diagram */}
      <div className="flex-1 relative">
        <div className="rounded-2xl border border-zinc-200 dark:border-zinc-800 bg-zinc-50 dark:bg-zinc-900/60 p-4 overflow-hidden">
          <svg viewBox="0 0 480 280" className="w-full" style={{ maxHeight: 280 }}>
            {/* Edges */}
            {EDGES.map((e) => {
              const fromBlock = BLOCKS.find((b) => b.id === e.from);
              const toBlock = BLOCKS.find((b) => b.id === e.to);
              const isActive = fromBlock && active >= fromBlock.step && toBlock && active >= toBlock.step;
              return (
                <g key={`${e.from}-${e.to}`}>
                  {/* Base line */}
                  <path
                    d={e.d}
                    stroke={isActive ? "#10b981" : "#e5e7eb"}
                    strokeWidth="1.5"
                    fill="none"
                    strokeDasharray="4 4"
                    className="dark:[stroke:var(--edge-color)]"
                    style={{ "--edge-color": isActive ? "#10b981" : "#374151" } as React.CSSProperties}
                  />
                  {/* Animated flow dot */}
                  {isActive && (
                    <motion.circle
                      r="3"
                      fill="#10b981"
                      initial={false}
                      animate={{ offsetDistance: ["0%", "100%"] }}
                      transition={{ duration: 1, repeat: Infinity, ease: "linear" }}
                      style={{
                        offsetPath: `path("${e.d}")`,
                        offsetRotate: "0deg",
                      }}
                    />
                  )}
                </g>
              );
            })}

            {/* Blocks */}
            {BLOCKS.map((b) => {
              const isActive = active >= b.step;
              const isCurrent = active === b.step;
              return (
                <g key={b.id} onClick={() => setActive(b.step)} style={{ cursor: "pointer" }}>
                  {/* Glow behind active */}
                  {isCurrent && (
                    <motion.rect
                      x={b.x - 4} y={b.y - 4}
                      width={b.w + 8} height={b.h + 8}
                      rx="10"
                      fill={b.color}
                      opacity={0}
                      animate={{ opacity: [0, 0.15, 0] }}
                      transition={{ duration: 1.5, repeat: Infinity }}
                    />
                  )}
                  {/* Card */}
                  <rect
                    x={b.x} y={b.y}
                    width={b.w} height={b.h}
                    rx="8"
                    fill={isActive ? "#1c1c1e" : "#f4f4f5"}
                    stroke={isCurrent ? b.color : isActive ? "#374151" : "#e5e7eb"}
                    strokeWidth={isCurrent ? 1.5 : 1}
                    className="dark:fill-zinc-800 dark:stroke-zinc-700"
                  />
                  {/* Color accent bar */}
                  {isActive && (
                    <rect
                      x={b.x} y={b.y}
                      width={b.w} height="3"
                      rx="8"
                      fill={b.color}
                    />
                  )}
                  {/* Label */}
                  <text
                    x={b.x + b.w / 2}
                    y={b.y + b.h / 2 + 4}
                    textAnchor="middle"
                    fontSize="11"
                    fontWeight={isCurrent ? "700" : "500"}
                    fill={isActive ? "#f4f4f5" : "#9ca3af"}
                    className="select-none"
                  >
                    {b.label}
                  </text>
                </g>
              );
            })}

            {/* API label */}
            <text x="440" y="50" fontSize="9" fill="#6b7280" textAnchor="end" className="select-none">
              Voice Agent API
            </text>
            <text x="440" y="62" fontSize="8" fill="#9ca3af" textAnchor="end" className="select-none">
              awaaz.ai
            </text>
          </svg>

          {/* Active step label */}
          <div className="mt-3 px-2 flex items-center gap-2">
            <div className="w-1.5 h-1.5 rounded-full bg-emerald-500" />
            <span className="text-xs font-medium text-zinc-600 dark:text-zinc-400">
              {STEPS[active]?.label}
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}
