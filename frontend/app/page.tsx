"use client";
import { useRouter } from "next/navigation";
import { motion, type Variants } from "framer-motion";
import { ArrowRight, Mic } from "lucide-react";
import dynamic from "next/dynamic";
import Navbar from "@/components/layout/Navbar";
import DomainCard from "@/components/ui/DomainCard";
import { DOMAINS, LANGUAGES, Domain } from "@/lib/domains";

const ArchDiagram = dynamic(() => import("@/components/ui/ArchDiagram"), { ssr: false });

const fadeUp: Variants = {
  hidden: { opacity: 0, y: 18 },
  show: (i: number = 0) => ({ opacity: 1, y: 0, transition: { delay: i * 0.07, duration: 0.4, ease: "easeOut" } }),
};

export default function Home() {
  const router = useRouter();

  function handleDomain(domain: Domain) {
    router.push(`/voice?domain=${domain.id}`);
  }

  return (
    <div className="min-h-screen bg-white dark:bg-[#0c0c0c]">
      <Navbar />

      {/* ── Hero ──────────────────────────────────────────────────────────── */}
      <section className="relative overflow-hidden px-5 pt-24 pb-20 text-center">
        <div className="grid-bg absolute inset-0 pointer-events-none" />

        <div className="relative z-10 max-w-3xl mx-auto">
          <motion.p
            variants={fadeUp} initial="hidden" animate="show" custom={0}
            className="text-xs font-semibold uppercase tracking-widest text-zinc-400 mb-5"
          >
            Voice AI · Public Services
          </motion.p>

          <motion.h1
            variants={fadeUp} initial="hidden" animate="show" custom={1}
            className="text-5xl sm:text-6xl lg:text-[72px] font-black tracking-tight leading-[1.05] text-zinc-900 dark:text-zinc-50 mb-6"
          >
            Ask government.
            <br />
            <span className="text-zinc-400 dark:text-zinc-500">Get answers.</span>
          </motion.h1>

          <motion.p
            variants={fadeUp} initial="hidden" animate="show" custom={2}
            className="text-base sm:text-lg text-zinc-500 dark:text-zinc-400 max-w-lg mx-auto leading-relaxed mb-10"
          >
            Speak in your language. Get accurate, real-time answers about healthcare, farming, education, and government schemes — no app needed.
          </motion.p>

          <motion.div
            variants={fadeUp} initial="hidden" animate="show" custom={3}
            className="flex flex-wrap items-center justify-center gap-3 mb-14"
          >
            <button
              onClick={() => document.getElementById("domains")?.scrollIntoView({ behavior: "smooth" })}
              className="flex items-center gap-2 px-5 py-2.5 bg-zinc-900 dark:bg-zinc-100 text-white dark:text-zinc-900 text-sm font-semibold rounded-xl hover:bg-zinc-700 dark:hover:bg-zinc-200 transition-colors"
            >
              Choose a service <ArrowRight size={14} />
            </button>
            <button
              onClick={() => handleDomain(DOMAINS[0])}
              className="flex items-center gap-2 px-5 py-2.5 border border-zinc-200 dark:border-zinc-700 text-sm font-semibold rounded-xl hover:border-zinc-400 dark:hover:border-zinc-500 transition-colors text-zinc-700 dark:text-zinc-300"
            >
              <Mic size={14} /> Try demo
            </button>
          </motion.div>

          {/* Language pills */}
          <motion.div
            variants={fadeUp} initial="hidden" animate="show" custom={4}
            className="flex flex-wrap justify-center gap-2"
          >
            {LANGUAGES.map((l) => (
              <span
                key={l.code}
                className="text-xs px-3 py-1 rounded-full border border-zinc-200 dark:border-zinc-800 text-zinc-500 dark:text-zinc-500 font-medium"
              >
                {l.nativeLabel}
              </span>
            ))}
          </motion.div>
        </div>
      </section>

      {/* ── Architecture section ───────────────────────────────────────────── */}
      <section className="px-5 py-16 border-t border-zinc-100 dark:border-zinc-900">
        <div className="max-w-5xl mx-auto">
          <motion.div
            initial={{ opacity: 0, y: 12 }} whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }} transition={{ duration: 0.4 }}
            className="mb-10"
          >
            <p className="text-xs font-semibold uppercase tracking-widest text-zinc-400 mb-2">How it works</p>
            <h2 className="text-2xl sm:text-3xl font-black tracking-tight text-zinc-900 dark:text-zinc-50">
              A single, unified Voice Agent pipeline
            </h2>
            <p className="text-sm text-zinc-500 mt-2 max-w-lg">
              Instead of stitching together components yourself, Awaaz handles STT, knowledge retrieval, LLM orchestration, and TTS in one flow.
            </p>
          </motion.div>

          <motion.div
            initial={{ opacity: 0, y: 16 }} whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }} transition={{ duration: 0.4, delay: 0.1 }}
          >
            <ArchDiagram />
          </motion.div>
        </div>
      </section>

      {/* ── Domain cards ───────────────────────────────────────────────────── */}
      <section id="domains" className="px-5 py-16 border-t border-zinc-100 dark:border-zinc-900">
        <div className="max-w-5xl mx-auto">
          <motion.div
            initial={{ opacity: 0, y: 12 }} whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }} transition={{ duration: 0.4 }}
            className="mb-8"
          >
            <p className="text-xs font-semibold uppercase tracking-widest text-zinc-400 mb-2">Service domains</p>
            <h2 className="text-2xl sm:text-3xl font-black tracking-tight text-zinc-900 dark:text-zinc-50">
              What can we help with?
            </h2>
          </motion.div>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
            {DOMAINS.map((d, i) => (
              <DomainCard key={d.id} domain={d} onClick={handleDomain} index={i} />
            ))}
          </div>
        </div>
      </section>

      {/* ── Stats strip ────────────────────────────────────────────────────── */}
      <section className="px-5 py-12 border-t border-zinc-100 dark:border-zinc-900">
        <div className="max-w-5xl mx-auto grid grid-cols-2 sm:grid-cols-4 gap-6">
          {[
            { num: "8",    label: "Languages supported" },
            { num: "6",    label: "Service domains" },
            { num: "24/7", label: "Always available" },
            { num: "<1s",  label: "Response time" },
          ].map((s) => (
            <div key={s.label} className="text-center sm:text-left">
              <div className="text-3xl font-black text-zinc-900 dark:text-zinc-50 tabular-nums">{s.num}</div>
              <div className="text-xs text-zinc-500 mt-1">{s.label}</div>
            </div>
          ))}
        </div>
      </section>

      {/* ── Footer ─────────────────────────────────────────────────────────── */}
      <footer className="border-t border-zinc-100 dark:border-zinc-900 px-5 py-6">
        <div className="max-w-5xl mx-auto flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center gap-2">
            <div className="w-6 h-6 rounded bg-zinc-900 dark:bg-zinc-100 flex items-center justify-center">
              <span className="text-white dark:text-zinc-900 text-[9px] font-black">AW</span>
            </div>
            <span className="text-sm font-bold text-zinc-900 dark:text-zinc-100">Awaaz</span>
          </div>
          <p className="text-xs text-zinc-400">Built at HackBLR · Making public services accessible</p>
        </div>
      </footer>
    </div>
  );
}
