import Link from "next/link";

/** Non-blocking prompt (shown on the results page) to set up reminder channels. */
export function NotificationPrefsCard() {
  return (
    <div className="bg-primary-container/10 border border-primary-container/20 rounded-2xl p-6 flex flex-col md:flex-row md:items-center gap-4">
      <div className="flex-shrink-0 w-12 h-12 rounded-full bg-primary-container/20 flex items-center justify-center">
        <span className="material-symbols-outlined text-primary" aria-hidden="true">
          notifications_active
        </span>
      </div>
      <div className="flex-1">
        <h3 className="text-body-lg font-bold text-on-surface mb-1">Stay on track with reminders</h3>
        <p className="text-body-md text-on-surface-variant leading-relaxed">
          Choose how VERA reaches you, by email, SMS, or WhatsApp, so you never miss a screening step.
        </p>
      </div>
      <Link
        href="/notifications"
        className="flex-shrink-0 bg-primary text-on-primary px-6 py-3 rounded-xl text-label-md font-bold hover:bg-primary/90 transition-colors text-center min-h-[48px] flex items-center justify-center"
      >
        Set up reminders
      </Link>
    </div>
  );
}
