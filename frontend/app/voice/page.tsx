"use client";

import { Suspense } from "react";
import VoiceInterface from "./VoiceInterface";

export default function VoicePage() {
  return (
    <Suspense fallback={<div className="min-h-screen bg-[#080a0d] flex items-center justify-center text-white/40">Loading…</div>}>
      <VoiceInterface />
    </Suspense>
  );
}
