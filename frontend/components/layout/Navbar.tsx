"use client";
import Link from "next/link";
import ThemeToggle from "@/components/ui/ThemeToggle";

interface NavbarProps { callActive?: boolean; }

export default function Navbar({ callActive = false }: NavbarProps) {
  return (
    <header className="sticky top-0 z-50 border-b border-zinc-200 dark:border-zinc-800 bg-white/90 dark:bg-[#0c0c0c]/90 backdrop-blur-md">
      <div className="mx-auto max-w-6xl px-5 h-14 flex items-center justify-between">
        <Link href="/" className="flex items-center gap-2.5">
          <div className="w-7 h-7 rounded-md bg-zinc-900 dark:bg-white flex items-center justify-center">
            <span className="text-white dark:text-zinc-900 text-[11px] font-black tracking-tight">AW</span>
          </div>
          <span className="text-[15px] font-bold tracking-tight">Awaaz</span>
        </Link>

        <div className="flex items-center gap-3">
          {callActive && (
            <div className="flex items-center gap-1.5 text-xs font-medium text-red-500">
              <span className="w-1.5 h-1.5 rounded-full bg-red-500 animate-pulse" />
              Live
            </div>
          )}
          <ThemeToggle />
        </div>
      </div>
    </header>
  );
}
