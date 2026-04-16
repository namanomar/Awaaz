"use client";
import { motion, AnimatePresence } from "framer-motion";
import { Mic, Square, Loader2 } from "lucide-react";

type OrbState = "idle" | "connecting" | "active";

interface Props {
  state: OrbState;
  onToggle: () => void;
  timerDisplay?: string;
}

export default function VoiceOrb({ state, onToggle, timerDisplay }: Props) {
  const isActive = state === "active";
  const isConnecting = state === "connecting";

  return (
    <div className="flex flex-col items-center gap-2">
      <div className="relative flex items-center justify-center w-24 h-24">
        {/* Rings */}
        {isActive && (
          <>
            <div className="orb-ring text-red-400/30" style={{ borderColor: "rgba(239,68,68,0.3)" }} />
            <div className="orb-ring text-red-400/20" style={{ borderColor: "rgba(239,68,68,0.15)", animationDelay: "0.9s" }} />
            <div className="orb-ring text-red-400/10" style={{ borderColor: "rgba(239,68,68,0.08)", animationDelay: "1.8s" }} />
          </>
        )}
        {state === "idle" && (
          <>
            <div className="orb-ring" style={{ borderColor: "rgba(16,185,129,0.25)" }} />
            <div className="orb-ring" style={{ borderColor: "rgba(16,185,129,0.12)", animationDelay: "0.9s" }} />
          </>
        )}

        <motion.button
          onClick={onToggle}
          disabled={isConnecting}
          whileTap={{ scale: 0.93 }}
          whileHover={{ scale: isConnecting ? 1 : 1.04 }}
          className={`relative z-10 w-16 h-16 rounded-full flex items-center justify-center transition-colors duration-300 ${
            isActive
              ? "bg-red-500 text-white shadow-[0_0_0_4px_rgba(239,68,68,0.15)]"
              : isConnecting
              ? "bg-zinc-200 dark:bg-zinc-700 text-zinc-500 cursor-not-allowed"
              : "bg-zinc-900 dark:bg-zinc-100 text-white dark:text-zinc-900 shadow-[0_4px_20px_rgba(0,0,0,0.15)] dark:shadow-[0_4px_20px_rgba(255,255,255,0.08)]"
          }`}
        >
          <AnimatePresence mode="wait">
            {isConnecting ? (
              <motion.div key="load" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
                <Loader2 size={22} className="animate-spin" />
              </motion.div>
            ) : isActive ? (
              <motion.div key="stop" initial={{ scale: 0.6, opacity: 0 }} animate={{ scale: 1, opacity: 1 }} exit={{ scale: 0.6, opacity: 0 }}>
                <Square size={20} fill="currentColor" />
              </motion.div>
            ) : (
              <motion.div key="mic" initial={{ scale: 0.6, opacity: 0 }} animate={{ scale: 1, opacity: 1 }} exit={{ scale: 0.6, opacity: 0 }}>
                <Mic size={22} />
              </motion.div>
            )}
          </AnimatePresence>
        </motion.button>
      </div>

      <AnimatePresence mode="wait">
        {isActive && timerDisplay ? (
          <motion.div
            key="timer"
            initial={{ opacity: 0, y: 4 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -4 }}
            className="text-center"
          >
            <div className="text-xl font-bold tabular-nums text-red-500">{timerDisplay}</div>
            <div className="text-[11px] text-zinc-400 mt-0.5">Tap to end</div>
          </motion.div>
        ) : (
          <motion.div
            key="label"
            initial={{ opacity: 0, y: 4 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -4 }}
            className="text-[12px] text-zinc-500 font-medium"
          >
            {isConnecting ? "Connecting…" : "Tap to speak"}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
