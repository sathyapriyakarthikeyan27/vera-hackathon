"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { useReminders } from "@/lib/reminders";
import { useAuth } from "@/lib/auth";
import type { Reminder } from "@/lib/api";

function formatDate(iso: string): string {
  try {
    return new Date(iso).toLocaleDateString("en-IN", {
      day: "numeric",
      month: "short",
      year: "numeric",
    });
  } catch {
    return iso;
  }
}

export function NotificationBell() {
  const { user } = useAuth();
  const { reminders, unreadDue, markRead, dismiss } = useReminders();
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function onClick(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    }
    document.addEventListener("mousedown", onClick);
    return () => document.removeEventListener("mousedown", onClick);
  }, []);

  if (!user) return null;

  return (
    <div ref={ref} className="relative">
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        className="relative flex items-center justify-center w-11 h-11 rounded-full hover:bg-surface-container transition-colors"
        aria-label={
          unreadDue > 0 ? `Reminders, ${unreadDue} due` : "Reminders"
        }
        aria-haspopup="true"
        aria-expanded={open}
      >
        <span className="material-symbols-outlined text-on-surface" aria-hidden="true">
          notifications
        </span>
        {unreadDue > 0 && (
          <span
            className="absolute top-1 right-1 min-w-[18px] h-[18px] px-1 rounded-full bg-error text-on-error text-[11px] font-bold flex items-center justify-center"
            aria-hidden="true"
          >
            {unreadDue > 9 ? "9+" : unreadDue}
          </span>
        )}
      </button>

      {open && (
        <div
          role="dialog"
          aria-label="Reminders"
          className="absolute right-0 mt-2 w-80 max-w-[calc(100vw-2rem)] bg-surface-container-lowest border border-outline-variant rounded-2xl soft-elevation-lg overflow-hidden z-50"
        >
          <div className="px-4 py-3 border-b border-outline-variant flex items-center justify-between">
            <p className="text-label-md font-bold text-on-surface">Reminders</p>
            <Link
              href="/notifications"
              onClick={() => setOpen(false)}
              className="text-label-sm text-primary font-semibold hover:underline"
            >
              Settings
            </Link>
          </div>

          {reminders.length === 0 ? (
            <p className="px-4 py-8 text-body-md text-on-surface-variant text-center">
              You have no reminders yet.
            </p>
          ) : (
            <ul className="max-h-96 overflow-y-auto divide-y divide-outline-variant/50">
              {reminders.map((r) => (
                <ReminderRow
                  key={r.id}
                  reminder={r}
                  onRead={() => markRead(r.id)}
                  onDismiss={() => dismiss(r.id)}
                />
              ))}
            </ul>
          )}
        </div>
      )}
    </div>
  );
}

function ReminderRow({
  reminder,
  onRead,
  onDismiss,
}: {
  reminder: Reminder;
  onRead: () => void;
  onDismiss: () => void;
}) {
  const isUnreadDue =
    reminder.due && reminder.status !== "read" && reminder.status !== "dismissed";

  return (
    <li className={`px-4 py-3 ${isUnreadDue ? "bg-primary-fixed/10" : ""}`}>
      <div className="flex items-start gap-2">
        <span
          className={`mt-1.5 w-2 h-2 rounded-full flex-shrink-0 ${
            isUnreadDue ? "bg-primary" : "bg-outline-variant"
          }`}
          aria-hidden="true"
        />
        <div className="flex-1 min-w-0">
          <p className="text-body-md text-on-surface leading-snug">{reminder.message}</p>
          <p className="text-label-sm text-on-surface-variant mt-1">
            {reminder.due ? "Due" : "Scheduled"} · {formatDate(reminder.due_at)}
          </p>
          <div className="flex gap-3 mt-2">
            {isUnreadDue && (
              <button
                type="button"
                onClick={onRead}
                className="text-label-sm text-primary font-semibold hover:underline"
              >
                Mark read
              </button>
            )}
            <button
              type="button"
              onClick={onDismiss}
              className="text-label-sm text-on-surface-variant hover:text-error hover:underline"
            >
              Dismiss
            </button>
          </div>
        </div>
      </div>
    </li>
  );
}
