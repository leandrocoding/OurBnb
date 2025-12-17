"use client";

import { useEffect, useMemo, useRef } from "react";
import { createPortal } from "react-dom";
import { CheckCircle2, X, ThumbsUp, SlidersHorizontal, Trophy, Users } from "lucide-react";

type TutorialStep = {
  title: string;
  body: string;
  icon: React.ReactNode;
};

export function OnboardingTutorialModal({
  open,
  onClose,
  groupId,
}: {
  open: boolean;
  onClose: () => void;
  groupId: number | null;
}) {
  const steps: TutorialStep[] = useMemo(
    () => [
      {
        title: "Voting",
        body: "Like or dislike airbnbs by swiping; vetoing removes them for everyone.",
        icon: <ThumbsUp className="w-6 h-6 text-emerald-500" />,
      },
      {
        title: "Filters",
        body: "To find something that works for everyone you may at times see airbnbs that don't match some of your filters.",
        icon: <SlidersHorizontal className="w-6 h-6 text-purple-500" />,
      },
      {
        title: "Leaderboard",
        body: "Rank shows the group’s top picks, click on one to open it in Airbnb.",
        icon: <Trophy className="w-6 h-6 text-yellow-500" />,
      },
      {
        title: "Inviting People",
        body: "Go to Group → Invite to copy a join link and share it with your friends.",
        icon: <Users className="w-6 h-6 text-blue-500" />,
      },
    ],
    []
  );

  const scrollLockRef = useRef<{ scrollY: number; prevStyle: Partial<CSSStyleDeclaration> } | null>(null);

  // Lock background scroll while open (mobile friendly)
  useEffect(() => {
    if (!open) return;
    if (typeof window === "undefined" || typeof document === "undefined") return;

    const body = document.body;
    const scrollY = window.scrollY;
    scrollLockRef.current = {
      scrollY,
      prevStyle: {
        overflow: body.style.overflow,
        position: body.style.position,
        top: body.style.top,
        left: body.style.left,
        right: body.style.right,
        width: body.style.width,
      },
    };

    body.style.overflow = "hidden";
    body.style.position = "fixed";
    body.style.top = `-${scrollY}px`;
    body.style.left = "0";
    body.style.right = "0";
    body.style.width = "100%";

    return () => {
      const saved = scrollLockRef.current;
      if (!saved) return;
      body.style.overflow = saved.prevStyle.overflow ?? "";
      body.style.position = saved.prevStyle.position ?? "";
      body.style.top = saved.prevStyle.top ?? "";
      body.style.left = saved.prevStyle.left ?? "";
      body.style.right = saved.prevStyle.right ?? "";
      body.style.width = saved.prevStyle.width ?? "";
      window.scrollTo(0, saved.scrollY);
      scrollLockRef.current = null;
    };
  }, [open]);

  useEffect(() => {
    if (!open) return;
    const onKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        e.preventDefault();
        onClose();
        return;
      }
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [open, onClose]);

  if (!open) return null;
  if (typeof document === "undefined") return null;

  return createPortal(
    <div
      className="fixed inset-0 z-[1100] bg-black/60 backdrop-blur-sm flex items-center justify-center p-4 overscroll-contain"
      onClick={onClose}
      aria-modal="true"
      role="dialog"
      aria-label="App tutorial"
    >
      <div
        className="w-full max-w-md rounded-2xl bg-white shadow-2xl border border-slate-200 overflow-hidden"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="px-5 pt-5 pb-4 border-b border-slate-100 flex items-start justify-between gap-3">
          <div className="min-w-0">
            <div className="mt-1 text-lg font-bold text-slate-900">How it works</div>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="p-2 rounded-lg hover:bg-slate-100 transition-colors"
            aria-label="Close tutorial"
          >
            <X className="w-5 h-5 text-slate-500" />
          </button>
        </div>

        <div className="p-5">
          <div className="space-y-4">
            {steps.map((s) => (
              <div key={s.title} className="flex items-start gap-3">
                <div className="w-10 h-10 rounded-xl bg-slate-50 border border-slate-200 flex items-center justify-center flex-shrink-0">
                  {s.icon}
                </div>
                <div className="min-w-0">
                  <div className="font-bold text-slate-900">{s.title}</div>
                  <div className="text-slate-700 leading-relaxed text-sm mt-1">{s.body}</div>
                </div>
              </div>
            ))}
          </div>
        </div>

        <div className="px-5 pb-5 flex items-center justify-end gap-3">
          <button
            type="button"
            onClick={onClose}
            className="inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-rose-500 text-white font-bold hover:bg-rose-600 transition-colors"
          >
            <CheckCircle2 className="w-5 h-5" />
            Got it
          </button>
        </div>
      </div>
    </div>,
    document.body
  );
}
