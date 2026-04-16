"use client";
import { motion } from "framer-motion";
import { ArrowRight } from "lucide-react";
import { Domain } from "@/lib/domains";

interface Props { domain: Domain; onClick: (d: Domain) => void; index: number; }

export default function DomainCard({ domain, onClick, index }: Props) {
  return (
    <motion.button
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.05, duration: 0.3, ease: "easeOut" }}
      onClick={() => onClick(domain)}
      className="group relative text-left w-full bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-2xl p-5 cursor-pointer hover:border-zinc-400 dark:hover:border-zinc-600 hover:shadow-sm transition-all duration-200"
    >
      <div className="flex items-start justify-between gap-3 mb-3">
        <span className="text-3xl">{domain.icon}</span>
        <ArrowRight
          size={15}
          className="text-zinc-300 dark:text-zinc-700 group-hover:text-zinc-500 dark:group-hover:text-zinc-400 group-hover:translate-x-0.5 transition-all mt-1"
        />
      </div>

      <h3 className="text-[15px] font-semibold text-zinc-900 dark:text-zinc-100 mb-1">
        {domain.name}
      </h3>
      <p className="text-xs text-zinc-500 mb-4 leading-relaxed">{domain.description}</p>

      <div className="flex flex-wrap gap-1.5">
        {domain.schemes.slice(0, 2).map((s) => (
          <span
            key={s}
            className="text-[10px] px-2 py-0.5 rounded-full bg-zinc-100 dark:bg-zinc-800 text-zinc-600 dark:text-zinc-400 font-medium"
          >
            {s}
          </span>
        ))}
      </div>
    </motion.button>
  );
}
