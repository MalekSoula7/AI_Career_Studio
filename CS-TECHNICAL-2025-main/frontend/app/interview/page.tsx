"use client";

import { useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { io, Socket } from "socket.io-client";

let socket: Socket | null = null;

function getSocket(baseUrl: string) {
  if (socket) return socket;
  socket = io(baseUrl, {
    transports: ["websocket"],
  });
  return socket;
}

export default function InterviewPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const sessionId = searchParams.get("session_id");
  const role = searchParams.get("role") || "Software Engineer";

  const [connected, setConnected] = useState(false);
  const [question, setQuestion] = useState<string | null>(null);
  const [answer, setAnswer] = useState("");
  const [timeLeft, setTimeLeft] = useState(60);
  const [feedback, setFeedback] = useState<string | null>(null);
  const [finalResult, setFinalResult] = useState<any | null>(null);
  const [submitting, setSubmitting] = useState(false);

  // Socket setup
  useEffect(() => {
    if (!sessionId) return;
    const baseUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
    const s = getSocket(baseUrl);

    const handleConnect = () => {
      setConnected(true);
      s.emit("join_interview", { session_id: sessionId });
    };

    const handleQuestion = (payload: { question?: { text?: string } | string | null }) => {
      const q =
        typeof payload?.question === "string"
          ? payload.question
          : payload?.question?.text || null;
      setQuestion(q);
      setAnswer("");
      setTimeLeft(60);
      setFeedback(null);
    };

    const handleFeedback = (payload: { feedback?: string | null }) => {
      setFeedback(payload.feedback || null);
    };

    const handleFinal = (payload: any) => {
      setFinalResult(payload);
    };

    s.on("connect", handleConnect);
    s.on("question", handleQuestion);
    s.on("feedback", handleFeedback);
    s.on("final", handleFinal);

    return () => {
      s.off("connect", handleConnect);
      s.off("question", handleQuestion);
      s.off("feedback", handleFeedback);
      s.off("final", handleFinal);
    };
  }, [sessionId]);

  // 60-second timer
  useEffect(() => {
    if (!question) return;
    if (timeLeft <= 0) return;
    const id = setInterval(() => {
      setTimeLeft((t) => (t > 0 ? t - 1 : 0));
    }, 1000);
    return () => clearInterval(id);
  }, [question, timeLeft]);

  // Auto-submit on timeout
  useEffect(() => {
    if (!question) return;
    if (timeLeft > 0) return;
    handleNext();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [timeLeft, question]);

  const handleNext = () => {
    if (!sessionId || !question || submitting) return;
    const baseUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
    const s = getSocket(baseUrl);
    setSubmitting(true);
    s.emit("answer_done", { session_id: sessionId, answer: answer.trim() }, () => {
      setSubmitting(false);
    });
  };

  const percent = Math.max(0, Math.min(100, (timeLeft / 60) * 100));
  const timeColor = timeLeft <= 10 ? "bg-rose-500" : timeLeft <= 20 ? "bg-amber-400" : "bg-emerald-500";

  if (!sessionId) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-950 text-slate-200">
        <p className="text-sm text-slate-400">Missing session id.</p>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-950 text-slate-50 flex flex-col">
      {/* Top bar with timer */}
      <header className="border-b border-slate-800/80 bg-slate-950/80 backdrop-blur-sm">
        <div className="max-w-4xl mx-auto px-4 py-3 flex items-center justify-between gap-4">
          <div>
            <p className="text-sm font-semibold">Live AI Interview</p>
            <p className="text-xs text-slate-400">Role: {role}</p>
          </div>
          <div className="flex flex-col items-end gap-1 text-xs">
            <span className="text-slate-400">Time left</span>
            <div className="flex items-center gap-2">
              <div className="w-32 h-2 rounded-full bg-slate-800 overflow-hidden">
                <div className={`h-full ${timeColor}`} style={{ width: `${percent}%` }} />
              </div>
              <span className="font-mono text-slate-200">
                00:{timeLeft.toString().padStart(2, "0")}
              </span>
            </div>
          </div>
        </div>
      </header>

      <main className="flex-1 flex flex-col items-center justify-center px-4 py-8">
        <div className="w-full max-w-3xl bg-slate-900/80 border border-slate-800/80 rounded-2xl p-6 shadow-lg shadow-slate-950/40 space-y-4">
          <div className="flex items-center justify-between">
            <h1 className="text-base font-semibold">Question</h1>
            <span className="text-[11px] text-slate-400">Session ID: {sessionId.slice(0, 8)}...</span>
          </div>
          <p className="text-sm text-slate-100 min-h-[3rem]">
            {question || "Waiting for question..."}
          </p>

          <div className="space-y-2">
            <label className="text-xs text-slate-400">Your answer</label>
            <textarea
              value={answer}
              onChange={(e) => setAnswer(e.target.value)}
              rows={6}
              className="w-full rounded-lg border border-slate-700 bg-slate-950/70 px-3 py-2 text-xs text-slate-100 placeholder:text-slate-500 focus:outline-none focus:ring-1 focus:ring-sky-500"
              placeholder="Talk through your experience, mention tools and metrics (%, users, latency, etc.)."
            />
            {feedback && (
              <p className="text-[11px] text-emerald-300">AI hint: {feedback}</p>
            )}
          </div>

          <div className="flex justify-between items-center pt-2">
            <button
              onClick={() => router.push("/dashboard")}
              className="text-xs text-slate-400 hover:text-slate-200"
            >
              Exit interview
            </button>
            <button
              onClick={handleNext}
              disabled={!question || submitting}
              className="inline-flex items-center justify-center rounded-md bg-emerald-500/90 hover:bg-emerald-400 text-slate-950 text-xs font-medium px-4 py-2 disabled:opacity-50"
            >
              {submitting ? "Submitting..." : "Submit & next"}
            </button>
          </div>
        </div>
      </main>

      {/* Final modal */}
      {finalResult && (
        <div className="fixed inset-0 z-50 flex items-center justify-center">
          <div className="absolute inset-0 bg-black/70" />
          <div className="relative z-10 w-full max-w-xl rounded-2xl border border-slate-800 bg-slate-950 text-slate-100 p-5 space-y-4">
            <h2 className="text-sm font-semibold">Interview Summary</h2>
            <p className="text-xs text-slate-400">
              Overall score: {finalResult.insights?.overall_score ?? "—"}
            </p>
            {finalResult.insights?.strengths && (
              <div>
                <p className="text-xs font-medium text-emerald-300 mb-1">Strengths</p>
                <ul className="space-y-1 text-xs list-disc list-inside">
                  {finalResult.insights.strengths.map((s: string, i: number) => (
                    <li key={`is-${i}`}>{s}</li>
                  ))}
                </ul>
              </div>
            )}
            {finalResult.insights?.weaknesses && (
              <div>
                <p className="text-xs font-medium text-rose-300 mb-1">Areas to improve</p>
                <ul className="space-y-1 text-xs list-disc list-inside">
                  {finalResult.insights.weaknesses.map((s: string, i: number) => (
                    <li key={`iw-${i}`}>{s}</li>
                  ))}
                </ul>
              </div>
            )}
            <div className="flex justify-end gap-2 pt-2">
              <button
                onClick={() => router.push("/dashboard")}
                className="rounded-md border border-slate-700 bg-slate-900/80 px-3 py-1.5 text-xs text-slate-200 hover:bg-slate-800"
              >
                Back to dashboard
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
