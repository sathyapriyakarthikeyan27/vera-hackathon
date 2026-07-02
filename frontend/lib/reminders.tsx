"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
} from "react";
import {
  dismissReminder,
  getReminders,
  markReminderRead,
  type Reminder,
} from "@/lib/api";
import { useAuth } from "@/lib/auth";

interface RemindersContextValue {
  reminders: Reminder[];
  unreadDue: number;
  loading: boolean;
  refresh: () => Promise<void>;
  markRead: (id: string) => Promise<void>;
  dismiss: (id: string) => Promise<void>;
}

const RemindersContext = createContext<RemindersContextValue | null>(null);

export function RemindersProvider({ children }: { children: React.ReactNode }) {
  const { user } = useAuth();
  const [reminders, setReminders] = useState<Reminder[]>([]);
  const [unreadDue, setUnreadDue] = useState(0);
  const [loading, setLoading] = useState(false);

  const refresh = useCallback(async () => {
    if (!user) {
      setReminders([]);
      setUnreadDue(0);
      return;
    }
    setLoading(true);
    try {
      const { reminders, unread_due } = await getReminders();
      setReminders(reminders);
      setUnreadDue(unread_due);
    } catch {
      // Non-fatal — reminders are a secondary surface.
    } finally {
      setLoading(false);
    }
  }, [user]);

  // Load whenever auth state changes (login / logout).
  useEffect(() => {
    refresh();
  }, [refresh]);

  const markRead = useCallback(
    async (id: string) => {
      await markReminderRead(id).catch(() => {});
      await refresh();
    },
    [refresh],
  );

  const dismiss = useCallback(
    async (id: string) => {
      // Optimistic removal so the UI feels instant.
      setReminders((prev) => prev.filter((r) => r.id !== id));
      await dismissReminder(id).catch(() => {});
      await refresh();
    },
    [refresh],
  );

  return (
    <RemindersContext.Provider
      value={{ reminders, unreadDue, loading, refresh, markRead, dismiss }}
    >
      {children}
    </RemindersContext.Provider>
  );
}

export function useReminders(): RemindersContextValue {
  const ctx = useContext(RemindersContext);
  if (!ctx) throw new Error("useReminders must be used within a RemindersProvider");
  return ctx;
}
