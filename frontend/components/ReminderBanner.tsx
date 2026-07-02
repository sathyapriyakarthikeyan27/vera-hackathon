"use client";

import { useReminders } from "@/lib/reminders";
import { useAuth } from "@/lib/auth";

/**
 * A slim bar for the single most-urgent due+unread reminder. Sits just below the
 * fixed Navbar (which is h-20). Closing it marks the reminder read, so it stops
 * nagging but stays in the bell list. Reserved for one item — the bell holds the rest.
 */
export function ReminderBanner() {
  const { user } = useAuth();
  const { reminders, markRead } = useReminders();

  if (!user) return null;

  const urgent = reminders.find(
    (r) => r.due && r.status !== "read" && r.status !== "dismissed",
  );
  if (!urgent) return null;

  return (
    <div className="fixed top-20 left-0 right-0 z-40 px-container-padding-mobile md:px-container-padding-desktop">
      <div className="max-w-[1200px] mx-auto mt-2">
        <div
          role="status"
          className="flex items-center gap-3 bg-primary text-on-primary rounded-xl px-4 py-2.5 soft-elevation"
        >
          <span className="material-symbols-outlined text-[20px] flex-shrink-0" aria-hidden="true">
            notifications_active
          </span>
          <p className="flex-1 text-label-md leading-snug line-clamp-2">{urgent.message}</p>
          <button
            type="button"
            onClick={() => markRead(urgent.id)}
            className="flex-shrink-0 w-9 h-9 flex items-center justify-center rounded-full hover:bg-on-primary/10 transition-colors"
            aria-label="Dismiss this reminder"
          >
            <span className="material-symbols-outlined text-[20px]" aria-hidden="true">close</span>
          </button>
        </div>
      </div>
    </div>
  );
}
