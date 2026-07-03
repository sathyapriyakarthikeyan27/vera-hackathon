"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Navbar } from "@/components/Navbar";
import { Footer } from "@/components/Footer";
import { useRequireAuth } from "@/lib/auth";
import {
  getNotificationPreferences,
  updateNotificationPreferences,
  sendPhoneOtp,
  verifyPhoneOtp,
  type ChannelOptin,
} from "@/lib/api";

const INPUT =
  "w-full px-4 py-3 rounded-xl border border-outline bg-surface-container-low text-body-md text-on-surface focus:outline-none focus:border-primary-container focus:ring-2 focus:ring-primary/10 transition-all";

type ChannelKey = keyof ChannelOptin;

function Toggle({
  checked,
  onChange,
  disabled,
  label,
}: {
  checked: boolean;
  onChange: (v: boolean) => void;
  disabled?: boolean;
  label: string;
}) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={checked}
      aria-label={label}
      disabled={disabled}
      onClick={() => onChange(!checked)}
      className={`relative w-12 h-7 rounded-full transition-colors flex-shrink-0 ${
        checked ? "bg-primary" : "bg-surface-container-high"
      } ${disabled ? "opacity-50 cursor-not-allowed" : ""}`}
    >
      <span
        className={`absolute top-1 left-1 w-5 h-5 rounded-full bg-white transition-transform ${
          checked ? "translate-x-5" : ""
        }`}
        aria-hidden="true"
      />
    </button>
  );
}

function Badge({ ok, okText, noText }: { ok: boolean; okText: string; noText: string }) {
  return (
    <span
      className={`text-label-sm font-semibold px-2 py-0.5 rounded-full ${
        ok ? "bg-secondary-container text-on-secondary-container" : "bg-tertiary-fixed text-on-tertiary-fixed-variant"
      }`}
    >
      {ok ? okText : noText}
    </span>
  );
}

export default function NotificationsPage() {
  useRequireAuth();
  const router = useRouter();

  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);

  const [email, setEmail] = useState("");
  const [emailVerified, setEmailVerified] = useState(false);
  const [optin, setOptin] = useState<ChannelOptin>({ in_app: true, email: false, sms: false, whatsapp: false });
  const [timezone, setTimezone] = useState("UTC");
  const [quietStart, setQuietStart] = useState<number | null>(null);
  const [quietEnd, setQuietEnd] = useState<number | null>(null);
  const [consented, setConsented] = useState(false);

  // Phone verification
  const [phone, setPhone] = useState("");
  const [phoneVerified, setPhoneVerified] = useState(false);
  const [otpSent, setOtpSent] = useState(false);
  const [otp, setOtp] = useState("");
  const [phoneMsg, setPhoneMsg] = useState<string | null>(null);
  const [phoneBusy, setPhoneBusy] = useState(false);

  useEffect(() => {
    getNotificationPreferences()
      .then((d) => {
        setEmail(d.email);
        setEmailVerified(d.email_verified);
        setOptin(d.preferences.channel_optin);
        setPhone(d.preferences.phone_e164 ?? "");
        setPhoneVerified(d.preferences.phone_verified);
        setQuietStart(d.preferences.quiet_hours_start);
        setQuietEnd(d.preferences.quiet_hours_end);
        setConsented(!!d.preferences.consent_at);
        const detected =
          typeof Intl !== "undefined" ? Intl.DateTimeFormat().resolvedOptions().timeZone : "";
        setTimezone(
          d.preferences.timezone && d.preferences.timezone !== "UTC"
            ? d.preferences.timezone
            : detected || "UTC",
        );
      })
      .catch(() => setError("Could not load your notification settings."))
      .finally(() => setLoading(false));
  }, []);

  const wantsExternal = optin.email || optin.sms || optin.whatsapp;

  function setChannel(key: ChannelKey, value: boolean) {
    setSaved(false);
    setOptin((o) => ({ ...o, [key]: value }));
  }

  async function handleSave() {
    setError(null);
    setSaved(false);
    if (wantsExternal && !consented) {
      setError("Please agree to receive reminders before enabling email, SMS, or WhatsApp.");
      return;
    }
    setSaving(true);
    try {
      await updateNotificationPreferences({
        channel_optin: optin,
        timezone,
        quiet_hours_start: quietStart,
        quiet_hours_end: quietEnd,
        give_consent: consented,
      });
      setSaved(true);
      // Let the success land, then return to the plan where reminders live.
      setTimeout(() => router.push("/companion"), 1200);
    } catch {
      setError("Something went wrong saving your settings. Please try again.");
      setSaving(false);
    }
  }

  async function handleSendOtp() {
    setPhoneMsg(null);
    setPhoneBusy(true);
    try {
      await sendPhoneOtp(phone.trim());
      setOtpSent(true);
      setPhoneMsg("I sent a 6-digit code to your phone. Enter it below.");
    } catch (e) {
      setPhoneMsg(
        String(e).includes("422")
          ? "Enter a valid phone number in international format, e.g. +14155552671."
          : "Could not send the code. Please try again.",
      );
    } finally {
      setPhoneBusy(false);
    }
  }

  async function handleVerifyOtp() {
    setPhoneMsg(null);
    setPhoneBusy(true);
    try {
      const d = await verifyPhoneOtp(otp.trim());
      setPhoneVerified(d.preferences.phone_verified);
      setOtpSent(false);
      setOtp("");
      setPhoneMsg("Your phone is verified.");
    } catch {
      setPhoneMsg("That code is invalid or has expired. Try sending a new one.");
    } finally {
      setPhoneBusy(false);
    }
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-background">
        <Navbar />
        <div className="pt-40 flex justify-center" role="status" aria-live="polite">
          <div className="w-10 h-10 border-4 border-primary/20 border-t-primary rounded-full animate-spin" aria-hidden="true" />
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background">
      <Navbar />
      <main
        id="main-content"
        className="pt-32 pb-stack-lg max-w-2xl mx-auto px-container-padding-mobile md:px-container-padding-desktop"
      >
        <h1 className="text-headline-lg text-on-surface mb-2">Notification settings</h1>
        <p className="text-body-md text-on-surface-variant mb-stack-md">
          Choose how VERA reaches you with reminders. You are always in control and can change this anytime.
        </p>

        {/* Channels */}
        <section className="bg-surface-container-lowest border border-outline-variant rounded-2xl p-6 soft-elevation mb-6">
          <h2 className="text-label-md font-bold text-on-surface uppercase tracking-wide mb-4">How VERA reaches you</h2>
          <div className="space-y-5">
            <ChannelRow
              title="In-app"
              desc="Always on. Reminders show in your notification bell."
              control={<Toggle checked disabled onChange={() => {}} label="In-app reminders (always on)" />}
            />
            <ChannelRow
              title="Email"
              desc={email}
              badge={<Badge ok={emailVerified} okText="Verified" noText="Unverified" />}
              control={
                <Toggle
                  checked={optin.email}
                  onChange={(v) => setChannel("email", v)}
                  label="Email reminders"
                />
              }
              hint={!emailVerified && optin.email ? "Verify your email to receive email reminders. Check the link from signup." : undefined}
            />
            <ChannelRow
              title="SMS"
              desc="Text messages to your phone."
              badge={<Badge ok={phoneVerified} okText="Phone verified" noText="Phone needed" />}
              control={
                <Toggle checked={optin.sms} onChange={(v) => setChannel("sms", v)} label="SMS reminders" />
              }
              hint={!phoneVerified && optin.sms ? "Verify your phone below to receive SMS reminders." : undefined}
            />
            <ChannelRow
              title="WhatsApp"
              desc="Messages to your WhatsApp number."
              badge={<Badge ok={phoneVerified} okText="Phone verified" noText="Phone needed" />}
              control={
                <Toggle checked={optin.whatsapp} onChange={(v) => setChannel("whatsapp", v)} label="WhatsApp reminders" />
              }
              hint={!phoneVerified && optin.whatsapp ? "Verify your phone below to receive WhatsApp reminders." : undefined}
            />
          </div>
        </section>

        {/* Phone verification */}
        <section className="bg-surface-container-lowest border border-outline-variant rounded-2xl p-6 soft-elevation mb-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-label-md font-bold text-on-surface uppercase tracking-wide">Phone number</h2>
            {phoneVerified && <Badge ok okText="Verified" noText="" />}
          </div>
          <div className="flex flex-col sm:flex-row gap-3">
            <input
              type="tel"
              value={phone}
              onChange={(e) => {
                setPhone(e.target.value);
                setPhoneVerified(false);
                setOtpSent(false);
              }}
              placeholder="+14155552671"
              className={INPUT}
              aria-label="Phone number in international format"
            />
            <button
              type="button"
              onClick={handleSendOtp}
              disabled={phoneBusy || !phone.trim() || phoneVerified}
              className="flex-shrink-0 bg-primary text-on-primary px-5 py-3 rounded-xl text-label-md font-bold disabled:bg-surface-container-high disabled:text-outline min-h-[48px]"
            >
              {otpSent ? "Resend code" : "Send code"}
            </button>
          </div>

          {otpSent && !phoneVerified && (
            <div className="flex flex-col sm:flex-row gap-3 mt-3">
              <input
                type="text"
                inputMode="numeric"
                value={otp}
                onChange={(e) => setOtp(e.target.value)}
                placeholder="6-digit code"
                className={INPUT}
                aria-label="Verification code"
              />
              <button
                type="button"
                onClick={handleVerifyOtp}
                disabled={phoneBusy || otp.trim().length < 4}
                className="flex-shrink-0 bg-secondary text-on-secondary px-5 py-3 rounded-xl text-label-md font-bold disabled:bg-surface-container-high disabled:text-outline min-h-[48px]"
              >
                Verify
              </button>
            </div>
          )}
          {phoneMsg && (
            <p className="text-label-md text-on-surface-variant mt-3" role="status">
              {phoneMsg}
            </p>
          )}
        </section>

        {/* Timing */}
        <section className="bg-surface-container-lowest border border-outline-variant rounded-2xl p-6 soft-elevation mb-6">
          <h2 className="text-label-md font-bold text-on-surface uppercase tracking-wide mb-4">Timing</h2>
          <div className="mb-5">
            <label htmlFor="tz" className="block text-label-md text-on-surface-variant mb-2">
              Your timezone
            </label>
            <input id="tz" type="text" value={timezone} onChange={(e) => setTimezone(e.target.value)} className={INPUT} />
          </div>
          <div>
            <p className="text-label-md text-on-surface-variant mb-2">
              Quiet hours <span className="text-on-surface-variant/60">(no messages during this window)</span>
            </p>
            <div className="flex items-center gap-3">
              <HourSelect label="From" value={quietStart} onChange={setQuietStart} />
              <HourSelect label="To" value={quietEnd} onChange={setQuietEnd} />
            </div>
          </div>
        </section>

        {/* Consent */}
        <section className="bg-primary-container/10 border border-primary-container/20 rounded-2xl p-6 mb-6">
          <label className="flex items-start gap-3 cursor-pointer">
            <input
              type="checkbox"
              checked={consented}
              onChange={(e) => setConsented(e.target.checked)}
              className="mt-1 w-5 h-5 accent-primary flex-shrink-0"
            />
            <span className="text-body-md text-on-surface-variant leading-relaxed">
              I agree to receive health reminders from VERA on the channels I have enabled. I understand I can
              turn these off at any time.
            </span>
          </label>
        </section>

        {error && (
          <p className="text-body-md text-error mb-4" role="alert">
            {error}
          </p>
        )}
        {saved && (
          <div
            className="mb-4 flex items-center gap-3 bg-secondary-container/40 border border-secondary-container rounded-2xl px-5 py-4"
            role="status"
            aria-live="polite"
          >
            <span
              className="material-symbols-outlined text-secondary"
              style={{ fontVariationSettings: "'FILL' 1" }}
              aria-hidden="true"
            >
              check_circle
            </span>
            <div>
              <p className="text-body-md font-semibold text-on-surface">Your reminder settings are saved.</p>
              <p className="text-label-md text-on-surface-variant">Taking you back to your plan…</p>
            </div>
          </div>
        )}

        <button
          type="button"
          onClick={handleSave}
          disabled={saving || saved}
          className="bg-primary text-on-primary px-8 py-3 rounded-full text-label-md font-bold disabled:opacity-60 min-h-[48px]"
        >
          {saved ? "Saved" : saving ? "Saving..." : "Save settings"}
        </button>
      </main>
      <Footer />
    </div>
  );
}

function ChannelRow({
  title,
  desc,
  badge,
  control,
  hint,
}: {
  title: string;
  desc: string;
  badge?: React.ReactNode;
  control: React.ReactNode;
  hint?: string;
}) {
  return (
    <div>
      <div className="flex items-center gap-4">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <p className="text-body-md font-semibold text-on-surface">{title}</p>
            {badge}
          </div>
          <p className="text-label-md text-on-surface-variant truncate">{desc}</p>
        </div>
        {control}
      </div>
      {hint && <p className="text-label-sm text-tertiary mt-1.5">{hint}</p>}
    </div>
  );
}

function HourSelect({
  label,
  value,
  onChange,
}: {
  label: string;
  value: number | null;
  onChange: (v: number | null) => void;
}) {
  return (
    <label className="flex items-center gap-2 text-label-md text-on-surface-variant">
      {label}
      <select
        value={value ?? ""}
        onChange={(e) => onChange(e.target.value === "" ? null : Number(e.target.value))}
        className="px-3 py-2 rounded-xl border border-outline bg-surface-container-low text-body-md text-on-surface min-h-[44px]"
      >
        <option value="">Off</option>
        {Array.from({ length: 24 }, (_, h) => (
          <option key={h} value={h}>
            {String(h).padStart(2, "0")}:00
          </option>
        ))}
      </select>
    </label>
  );
}
