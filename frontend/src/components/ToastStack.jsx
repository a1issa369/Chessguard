import { useCallback, useEffect, useRef, useState } from "react";

const DURATION_MS = 5500;

// useToasts() owns the list; <ToastStack /> just renders it.
export function useToasts() {
  const [toasts, setToasts] = useState([]);
  const nextId = useRef(1);

  const dismiss = useCallback((id) => {
    setToasts((t) => t.filter((x) => x.id !== id));
  }, []);

  const push = useCallback((toast) => {
    const id = nextId.current++;
    // Same message twice in a row replaces itself instead of stacking.
    setToasts((t) => [...t.filter((x) => x.message !== toast.message), { id, ...toast }].slice(-3));
    return id;
  }, []);

  return { toasts, push, dismiss };
}

const STYLES = {
  error: { bar: "bg-oxblood", title: "text-oxblood", icon: "!" },
  warning: { bar: "bg-brass", title: "text-brass-ink", icon: "i" },
};

function Toast({ toast, onDismiss }) {
  const { id, kind = "error", title, message } = toast;
  const s = STYLES[kind] || STYLES.error;

  useEffect(() => {
    const timer = setTimeout(() => onDismiss(id), DURATION_MS);
    return () => clearTimeout(timer);
  }, [id, onDismiss]);

  return (
    <div
      role={kind === "error" ? "alert" : "status"}
      className="animate-rise-in pointer-events-auto relative flex w-full items-start gap-3 overflow-hidden
                 rounded-lg border border-board-dark/20 bg-surface py-3 pl-5 pr-3 shadow-lg"
    >
      <span className={`absolute inset-y-0 left-0 w-1.5 ${s.bar}`} aria-hidden="true" />
      <span
        className={`mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full border
                    border-current font-data text-xs font-bold ${s.title}`}
        aria-hidden="true"
      >
        {s.icon}
      </span>
      <div className="min-w-0 flex-1">
        <p className={`font-body text-sm font-semibold ${s.title}`}>{title}</p>
        <p className="mt-0.5 font-body text-sm text-ink/70">{message}</p>
      </div>
      <button
        type="button"
        onClick={() => onDismiss(id)}
        aria-label="Dismiss notification"
        className="rounded-md px-2 py-0.5 font-body text-lg leading-none text-ink/70 outline-none
                   hover:text-ink focus-visible:ring-2 focus-visible:ring-felt/50"
      >
        &times;
      </button>
    </div>
  );
}

export default function ToastStack({ toasts, onDismiss }) {
  return (
    <div
      className="pointer-events-none fixed inset-x-0 top-4 z-50 mx-auto flex w-full max-w-sm
                 flex-col gap-2 px-4"
    >
      {toasts.map((t) => (
        <Toast key={t.id} toast={t} onDismiss={onDismiss} />
      ))}
    </div>
  );
}
