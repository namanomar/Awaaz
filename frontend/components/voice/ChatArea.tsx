"use client";
import { useEffect, useRef } from "react";

/** Convert spoken-aloud URLs back to proper hyperlinks.
 *  e.g. "h t t p s slash slash p m j a y dot gov dot in"
 *    → "https://pmjay.gov.in"
 */
function normalizeSpokenUrls(text: string): string {
  if (!text) return "";
  return text.replace(
    /h\s+t\s+t\s+p\s*(s\s+)?(?:colon\s+)?slash\s+slash\s+((?:[a-z0-9]+\s*)+(?:(?:dot|slash)\s+(?:[a-z0-9]+\s*)*)*)(?=[,\s]|$)/gi,
    (_match, s, rest) => {
      const proto = s ? "https://" : "http://";
      const url = rest
        .replace(/\s*(dot)\s*/gi, ".")
        .replace(/\s*(slash)\s*/gi, "/")
        .replace(/\s+/g, "")
        .replace(/[./]+$/, "");
      return proto + url;
    }
  );
}

/** Split text around URLs and return mixed text+link nodes. */
function renderText(raw: string): React.ReactNode {
  if (!raw) return null;
  const text = normalizeSpokenUrls(raw);
  const urlRe = /(https?:\/\/[^\s,;!?]+)/g;
  const parts: React.ReactNode[] = [];
  let last = 0;
  let m: RegExpExecArray | null;
  while ((m = urlRe.exec(text)) !== null) {
    if (m.index > last) parts.push(text.slice(last, m.index));
    const href = m[1].replace(/[.,;!?]+$/, "");
    parts.push(
      <a key={m.index} href={href} target="_blank" rel="noopener noreferrer"
         className="text-emerald-500 dark:text-emerald-400 underline underline-offset-2 break-all hover:opacity-80">
        {href}
      </a>
    );
    last = m.index + m[1].length;
  }
  if (last < text.length) parts.push(text.slice(last));
  return parts.length > 1 ? <>{parts}</> : text;
}

export interface Message {
  id: string;
  role: "user" | "assistant";
  text: string;
  time: string;
  partial?: boolean;
}

export default function ChatArea({ messages, isTyping }: { messages: Message[]; isTyping: boolean }) {
  const bottomRef = useRef<HTMLDivElement>(null);
  useEffect(() => { bottomRef.current?.scrollIntoView({ behavior: "smooth" }); }, [messages, isTyping]);

  return (
    <div className="flex-1 overflow-y-auto px-4 py-4 flex flex-col gap-3 min-h-0">
      {messages.map((msg) =>
        msg.role === "assistant" ? (
          <div key={msg.id} className="flex items-start gap-2.5 max-w-[88%]">
            <div className="w-7 h-7 rounded-full bg-zinc-100 dark:bg-zinc-800 border border-zinc-200 dark:border-zinc-700 flex items-center justify-center text-sm flex-shrink-0 mt-0.5">
              🎙
            </div>
            <div>
              <div className="bg-zinc-100 dark:bg-zinc-800 border border-zinc-200 dark:border-zinc-700/60 rounded-2xl rounded-tl-sm px-3.5 py-2.5 text-sm text-zinc-800 dark:text-zinc-200 leading-relaxed">
                {renderText(msg.text)}
                {msg.partial && (
                  <span className="inline-block w-[2px] h-[1em] bg-zinc-400 dark:bg-zinc-500 ml-0.5 align-middle animate-[blink_1s_step-end_infinite]" />
                )}
              </div>
              <div className="text-[10px] text-zinc-400 mt-1 ml-1">{msg.time}</div>
            </div>
          </div>
        ) : (
          <div key={msg.id} className="flex items-start gap-2.5 flex-row-reverse ml-auto max-w-[88%]">
            <div className="w-7 h-7 rounded-full bg-zinc-900 dark:bg-zinc-100 flex items-center justify-center text-sm flex-shrink-0 mt-0.5">
              <span className="text-white dark:text-zinc-900 text-[10px] font-bold">U</span>
            </div>
            <div>
              <div className="bg-zinc-900 dark:bg-zinc-100 rounded-2xl rounded-tr-sm px-3.5 py-2.5 text-sm text-white dark:text-zinc-900 leading-relaxed">
                {msg.text}
              </div>
              <div className="text-[10px] text-zinc-400 mt-1 mr-1 text-right">{msg.time}</div>
            </div>
          </div>
        )
      )}

      {isTyping && (
        <div className="flex items-start gap-2.5">
          <div className="w-7 h-7 rounded-full bg-zinc-100 dark:bg-zinc-800 border border-zinc-200 dark:border-zinc-700 flex items-center justify-center text-sm flex-shrink-0">
            🎙
          </div>
          <div className="bg-zinc-100 dark:bg-zinc-800 border border-zinc-200 dark:border-zinc-700/60 rounded-2xl rounded-tl-sm px-3.5 py-3 flex gap-1.5 items-center">
            <div className="typing-dot text-zinc-500" />
            <div className="typing-dot text-zinc-500" />
            <div className="typing-dot text-zinc-500" />
          </div>
        </div>
      )}
      <div ref={bottomRef} />
    </div>
  );
}
