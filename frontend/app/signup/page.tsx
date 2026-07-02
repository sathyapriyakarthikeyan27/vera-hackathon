"use client";

import { useState, useRef, useEffect } from "react";
import { useRouter } from "next/navigation";
import { signup, linkSession } from "@/lib/api";
import { useRequireAuth } from "@/lib/auth";

// ── City list ────────────────────────────────────────────────────────────────

const CITIES = [
  // India
  "Agra, India", "Ahmedabad, India", "Allahabad, India", "Amritsar, India",
  "Aurangabad, India", "Bangalore, India", "Bhopal, India", "Chandigarh, India",
  "Chennai, India", "Coimbatore, India", "Delhi, India", "Dhanbad, India",
  "Faridabad, India", "Ghaziabad, India", "Guwahati, India", "Gwalior, India",
  "Howrah, India", "Hyderabad, India", "Indore, India", "Jabalpur, India",
  "Jaipur, India", "Jodhpur, India", "Kalyan, India", "Kanpur, India",
  "Kochi, India", "Kolkata, India", "Kota, India", "Lucknow, India",
  "Ludhiana, India", "Madurai, India", "Meerut, India", "Mumbai, India",
  "Nagpur, India", "Nashik, India", "Navi Mumbai, India", "Patna, India",
  "Pune, India", "Raipur, India", "Rajkot, India", "Ranchi, India",
  "Srinagar, India", "Surat, India", "Thane, India", "Vadodara, India",
  "Varanasi, India", "Vijayawada, India", "Visakhapatnam, India",
  // Egypt
  "Alexandria, Egypt", "Aswan, Egypt", "Asyut, Egypt", "Cairo, Egypt",
  "Damietta, Egypt", "El Minya, Egypt", "Faiyum, Egypt", "Giza, Egypt",
  "Hurghada, Egypt", "Ismailia, Egypt", "Luxor, Egypt", "Mansoura, Egypt",
  "Port Said, Egypt", "Qena, Egypt", "Sharm El Sheikh, Egypt", "Sohag, Egypt",
  "Suez, Egypt", "Tanta, Egypt", "Zagazig, Egypt",
  // UK
  "Belfast, UK", "Birmingham, UK", "Bradford, UK", "Brighton, UK",
  "Bristol, UK", "Cardiff, UK", "Coventry, UK", "Edinburgh, UK",
  "Glasgow, UK", "Leeds, UK", "Leicester, UK", "Liverpool, UK",
  "London, UK", "Manchester, UK", "Newcastle upon Tyne, UK",
  "Nottingham, UK", "Oxford, UK", "Plymouth, UK", "Sheffield, UK",
  "Southampton, UK", "Sunderland, UK", "Wakefield, UK",
  // Italy
  "Bologna, Italy", "Florence, Italy", "Genoa, Italy", "Milan, Italy",
  "Naples, Italy", "Palermo, Italy", "Rome, Italy", "Turin, Italy",
  "Venice, Italy", "Verona, Italy",
  // Europe
  "Amsterdam, Netherlands", "Athens, Greece", "Barcelona, Spain",
  "Berlin, Germany", "Brussels, Belgium", "Bucharest, Romania",
  "Budapest, Hungary", "Cologne, Germany", "Copenhagen, Denmark",
  "Dublin, Ireland", "Frankfurt, Germany", "Geneva, Switzerland",
  "Hamburg, Germany", "Helsinki, Finland", "Lisbon, Portugal",
  "Ljubljana, Slovenia", "Luxembourg, Luxembourg", "Lyon, France",
  "Madrid, Spain", "Marseille, France", "Munich, Germany",
  "Nice, France", "Oslo, Norway", "Paris, France", "Prague, Czech Republic",
  "Riga, Latvia", "Rotterdam, Netherlands", "Seville, Spain",
  "Stockholm, Sweden", "Strasbourg, France", "Tallinn, Estonia",
  "Valencia, Spain", "Vienna, Austria", "Vilnius, Lithuania",
  "Warsaw, Poland", "Zurich, Switzerland",
  // Middle East
  "Abu Dhabi, UAE", "Amman, Jordan", "Baghdad, Iraq", "Bahrain, Bahrain",
  "Beirut, Lebanon", "Damascus, Syria", "Doha, Qatar", "Dubai, UAE",
  "Jerusalem, Israel", "Kuwait City, Kuwait", "Manama, Bahrain",
  "Muscat, Oman", "Riyadh, Saudi Arabia", "Sharjah, UAE",
  "Tel Aviv, Israel", "Tehran, Iran",
  // Africa
  "Abidjan, Ivory Coast", "Accra, Ghana", "Addis Ababa, Ethiopia",
  "Algiers, Algeria", "Cape Town, South Africa", "Casablanca, Morocco",
  "Dar es Salaam, Tanzania", "Johannesburg, South Africa",
  "Kampala, Uganda", "Khartoum, Sudan", "Kinshasa, DRC",
  "Lagos, Nigeria", "Lusaka, Zambia", "Nairobi, Kenya",
  "Rabat, Morocco", "Tunis, Tunisia",
  // North America
  "Atlanta, USA", "Austin, USA", "Baltimore, USA", "Boston, USA",
  "Chicago, USA", "Dallas, USA", "Denver, USA", "Detroit, USA",
  "Houston, USA", "Las Vegas, USA", "Los Angeles, USA",
  "Memphis, USA", "Miami, USA", "Minneapolis, USA",
  "Nashville, USA", "New Orleans, USA", "New York, USA",
  "Philadelphia, USA", "Phoenix, USA", "Portland, USA",
  "San Diego, USA", "San Francisco, USA", "San Jose, USA",
  "Seattle, USA", "Toronto, Canada", "Vancouver, Canada",
  "Washington DC, USA", "Montreal, Canada", "Ottawa, Canada",
  "Mexico City, Mexico", "Guadalajara, Mexico", "Monterrey, Mexico",
  // Asia Pacific
  "Bangkok, Thailand", "Beijing, China", "Dhaka, Bangladesh",
  "Ho Chi Minh City, Vietnam", "Hong Kong, China", "Jakarta, Indonesia",
  "Karachi, Pakistan", "Kuala Lumpur, Malaysia", "Lahore, Pakistan",
  "Manila, Philippines", "Melbourne, Australia", "Osaka, Japan",
  "Perth, Australia", "Seoul, South Korea", "Shanghai, China",
  "Singapore, Singapore", "Sydney, Australia", "Taipei, Taiwan",
  "Tokyo, Japan", "Auckland, New Zealand", "Wellington, New Zealand",
  // South America
  "Bogotá, Colombia", "Buenos Aires, Argentina", "Caracas, Venezuela",
  "La Paz, Bolivia", "Lima, Peru", "Montevideo, Uruguay",
  "Quito, Ecuador", "Rio de Janeiro, Brazil", "Santiago, Chile",
  "São Paulo, Brazil",
];

// ── Helpers ──────────────────────────────────────────────────────────────────

function computeAgeGroup(dob: string): string {
  const birth = new Date(dob);
  const today = new Date();
  let age = today.getFullYear() - birth.getFullYear();
  const m = today.getMonth() - birth.getMonth();
  if (m < 0 || (m === 0 && today.getDate() < birth.getDate())) age--;
  if (age < 25) return "under_25";
  if (age < 35) return "25_34";
  if (age < 45) return "35_44";
  if (age < 55) return "45_54";
  return "55_plus";
}

function mapGender(g: string): "female" | "male" | "other" {
  if (g === "female") return "female";
  if (g === "male") return "male";
  return "other";
}

const today = new Date().toISOString().split("T")[0];

// ── Sub-components ────────────────────────────────────────────────────────────

function VeraLogo({ className = "h-10 w-auto" }: { className?: string }) {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      viewBox="0 0 200 60"
      fill="none"
      className={className}
      aria-label="VERA"
      role="img"
    >
      <path
        d="M10 12C10 8.68629 12.6863 6 16 6H44C47.3137 6 50 8.68629 50 12V48C50 51.3137 47.3137 54 44 54H16C12.6863 54 10 51.3137 10 48V12Z"
        fill="#2d7d9a"
        fillOpacity="0.08"
      />
      <path
        d="M22 24L30 40L38 24"
        stroke="#2d7d9a"
        strokeWidth="3.5"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      <path
        d="M38 24C42 24 45 27 45 31C45 35 42 38 38 38"
        stroke="#2d7d9a"
        strokeWidth="2.5"
        strokeLinecap="round"
        strokeDasharray="0.1 6"
      />
      <text
        x="65"
        y="39"
        fontFamily="Montserrat, sans-serif"
        fontSize="28"
        fontWeight="700"
        fill="#2d7d9a"
        letterSpacing="-0.5"
      >
        VERA
      </text>
    </svg>
  );
}

function CityCombobox({
  value,
  onChange,
}: {
  value: string;
  onChange: (v: string) => void;
}) {
  const [query, setQuery] = useState(value);
  const [open, setOpen] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function onClickOutside(e: MouseEvent) {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    }
    document.addEventListener("mousedown", onClickOutside);
    return () => document.removeEventListener("mousedown", onClickOutside);
  }, []);

  const matches = CITIES.filter((c) =>
    c.split(",")[0].toLowerCase().startsWith(query.toLowerCase().trim())
  ).slice(0, 8);

  function handleSelect(city: string) {
    setQuery(city);
    onChange(city);
    setOpen(false);
  }

  function handleChange(e: React.ChangeEvent<HTMLInputElement>) {
    setQuery(e.target.value);
    onChange(e.target.value);
    setOpen(true);
  }

  return (
    <div ref={containerRef} className="relative">
      <span
        className="material-symbols-outlined absolute left-4 top-1/2 -translate-y-1/2 text-outline pointer-events-none select-none"
        aria-hidden="true"
      >
        search
      </span>
      <input
        id="location"
        type="text"
        value={query}
        onChange={handleChange}
        onFocus={() => query.length > 0 && setOpen(true)}
        placeholder="Search your city"
        className="w-full pl-12 pr-4 py-3 rounded-xl border border-outline bg-surface-container-low text-body-md text-on-surface focus:outline-none focus:border-primary-container focus:ring-2 focus:ring-primary/10 transition-all"
        autoComplete="off"
        role="combobox"
        aria-autocomplete="list"
        aria-expanded={open && matches.length > 0}
        aria-controls="city-listbox"
        aria-haspopup="listbox"
        aria-required="true"
      />
      {open && matches.length > 0 && (
        <ul
          id="city-listbox"
          role="listbox"
          aria-label="City suggestions"
          className="absolute z-20 w-full mt-1 bg-surface-container-lowest border border-outline-variant rounded-xl overflow-hidden"
          style={{ boxShadow: "0 8px 24px rgba(45,125,154,0.12)" }}
        >
          {matches.map((city) => (
            <li
              key={city}
              role="option"
              aria-selected={value === city}
              onMouseDown={(e) => { e.preventDefault(); handleSelect(city); }}
              className="px-4 py-3 text-body-md text-on-surface cursor-pointer hover:bg-primary-fixed/30 transition-colors border-b border-outline-variant/30 last:border-b-0"
            >
              {city}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

// ── Page ─────────────────────────────────────────────────────────────────────

export default function SignupPage() {
  const router = useRouter();
  useRequireAuth(); // health profile is only collected for signed-in accounts

  const [name, setName] = useState("");
  const [dob, setDob] = useState("");
  const [genderSelect, setGenderSelect] = useState("");
  const [location, setLocation] = useState("");
  const [height, setHeight] = useState("");
  const [weight, setWeight] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const isValid = name.trim() && dob && genderSelect && location.trim();

  async function handleSubmit(e: { preventDefault(): void }) {
    e.preventDefault();
    if (!isValid || loading) return;
    setLoading(true);
    setError(null);
    try {
      const result = await signup({
        name: name.trim(),
        age_group: computeAgeGroup(dob),
        gender: mapGender(genderSelect),
        location: location.trim(),
        language: "en",
        height_cm: height ? parseInt(height) : undefined,
        weight_kg: weight ? parseInt(weight) : undefined,
        date_of_birth: dob,
      });
      localStorage.setItem("vera_session_id", result.session_id);
      localStorage.setItem("vera_profile_complete", "1");
      await linkSession(result.session_id).catch(() => {}); // bind session to the account
      router.push("/assessment");
    } catch (e) {
      console.error("Signup error:", e);
      setError("Something went wrong. Please check your details and try again.");
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen bg-background">

      {/* Header — logo only, transactional screen */}
      <header className="w-full py-8 px-container-padding-mobile md:px-container-padding-desktop">
        <div className="max-w-7xl mx-auto flex items-center justify-center">
          <VeraLogo className="h-12 md:h-16 w-auto" />
        </div>
      </header>

      <main
        id="main-content"
        className="max-w-4xl mx-auto px-container-padding-mobile md:px-container-padding-desktop pb-20"
      >
        {/* Hero */}
        <div className="text-center mb-12">
          <h1 className="text-headline-xl text-primary mb-4">
            Welcome to VERA.
          </h1>
          <p className="text-body-lg text-on-surface-variant max-w-2xl mx-auto">
            Let&apos;s personalise your health journey. This helps VERA give you
            more accurate screenings and guidance that fits your life.
          </p>
        </div>

        <form onSubmit={handleSubmit} noValidate>
          <div className="grid grid-cols-1 md:grid-cols-12 gap-gutter">

            {/* Left column */}
            <div className="md:col-span-7 flex flex-col gap-6">

              {/* Basic Identity card */}
              <div className="bg-surface-container-lowest p-8 rounded-3xl border border-outline-variant soft-elevation hover:-translate-y-0.5 transition-transform">
                <h2 className="text-headline-md text-primary mb-6 flex items-center gap-2">
                  <span className="material-symbols-outlined" aria-hidden="true">person</span>
                  Basic Identity
                </h2>
                <div className="space-y-6">

                  {/* Full name */}
                  <div>
                    <label htmlFor="name" className="block text-label-md text-on-surface-variant mb-2">
                      Full Name
                    </label>
                    <input
                      id="name"
                      type="text"
                      value={name}
                      onChange={(e) => setName(e.target.value)}
                      placeholder="E.g. Jane Doe"
                      className="w-full px-4 py-3 rounded-xl border border-outline bg-surface-container-low text-body-md text-on-surface focus:outline-none focus:border-primary-container focus:ring-2 focus:ring-primary/10 transition-all"
                      autoFocus
                      autoComplete="name"
                      required
                      aria-required="true"
                    />
                  </div>

                  {/* DOB + Gender row */}
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                    <div>
                      <label htmlFor="dob" className="block text-label-md text-on-surface-variant mb-2">
                        Date of Birth
                      </label>
                      <input
                        id="dob"
                        type="date"
                        value={dob}
                        onChange={(e) => setDob(e.target.value)}
                        max={today}
                        className="w-full px-4 py-3 rounded-xl border border-outline bg-surface-container-low text-body-md text-on-surface focus:outline-none focus:border-primary-container focus:ring-2 focus:ring-primary/10 transition-all"
                        required
                        aria-required="true"
                      />
                    </div>
                    <div>
                      <label htmlFor="gender" className="block text-label-md text-on-surface-variant mb-2">
                        Gender
                      </label>
                      <select
                        id="gender"
                        value={genderSelect}
                        onChange={(e) => setGenderSelect(e.target.value)}
                        className="w-full px-4 py-3 rounded-xl border border-outline bg-surface-container-low text-body-md text-on-surface focus:outline-none focus:border-primary-container focus:ring-2 focus:ring-primary/10 transition-all"
                        required
                        aria-required="true"
                      >
                        <option value="" disabled>Select Gender</option>
                        <option value="female">Female</option>
                        <option value="male">Male</option>
                        <option value="non-binary">Non-binary</option>
                        <option value="prefer_not_to_say">Prefer not to say</option>
                      </select>
                    </div>
                  </div>
                </div>
              </div>

              {/* Location card */}
              <div className="bg-surface-container-lowest p-8 rounded-3xl border border-outline-variant soft-elevation hover:-translate-y-0.5 transition-transform">
                <h2 className="text-headline-md text-primary mb-6 flex items-center gap-2">
                  <span className="material-symbols-outlined" aria-hidden="true">location_on</span>
                  Location
                </h2>
                <p className="text-label-sm text-on-surface-variant mb-4">
                  This allows VERA to find nearby specialists and clinics that match your risk profile.
                </p>
                <div>
                  <label htmlFor="location" className="block text-label-md text-on-surface-variant mb-2">
                    City or Country
                  </label>
                  <CityCombobox value={location} onChange={setLocation} />
                </div>
              </div>
            </div>

            {/* Right column */}
            <div className="md:col-span-5 flex flex-col gap-6">

              {/* Biometrics card */}
              <div className="bg-secondary-container text-on-secondary-container p-8 rounded-3xl soft-elevation hover:-translate-y-0.5 transition-transform">
                <h2 className="text-headline-md mb-6 flex items-center gap-2">
                  <span className="material-symbols-outlined" aria-hidden="true">monitoring</span>
                  Biometrics
                </h2>
                <div className="space-y-6">
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <label htmlFor="height" className="block text-label-md mb-2">
                        Height (cm)
                      </label>
                      <input
                        id="height"
                        type="number"
                        value={height}
                        onChange={(e) => setHeight(e.target.value)}
                        placeholder="170"
                        min="50"
                        max="250"
                        className="w-full px-4 py-3 rounded-xl border-none bg-white/50 text-body-md text-on-secondary-container placeholder:text-on-secondary-container/50 focus:outline-none focus:ring-2 focus:ring-primary transition-all"
                      />
                    </div>
                    <div>
                      <label htmlFor="weight" className="block text-label-md mb-2">
                        Weight (kg)
                      </label>
                      <input
                        id="weight"
                        type="number"
                        value={weight}
                        onChange={(e) => setWeight(e.target.value)}
                        placeholder="65"
                        min="20"
                        max="300"
                        className="w-full px-4 py-3 rounded-xl border-none bg-white/50 text-body-md text-on-secondary-container placeholder:text-on-secondary-container/50 focus:outline-none focus:ring-2 focus:ring-primary transition-all"
                      />
                    </div>
                  </div>
                  <div className="bg-white/30 p-4 rounded-xl">
                    <p className="text-label-sm leading-relaxed">
                      <span className="material-symbols-outlined text-base align-middle mr-1" aria-hidden="true">info</span>
                      Used to calculate BMI and give you more personalised health context. Optional.
                    </p>
                  </div>
                </div>
              </div>

              {/* Privacy card */}
              <div className="flex-grow bg-primary-container text-on-primary-container p-8 rounded-3xl soft-elevation hover:-translate-y-0.5 transition-transform flex flex-col justify-between">
                <div>
                  <h2 className="text-headline-md mb-4 flex items-center gap-2">
                    <span className="material-symbols-outlined" aria-hidden="true">verified_user</span>
                    Your Privacy
                  </h2>
                  <p className="text-body-md opacity-90 leading-relaxed mb-6">
                    Your health data is used only to give you guidance and risk assessments.
                    VERA never shares your data with anyone.
                  </p>
                </div>
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-full bg-white/20 flex items-center justify-center flex-shrink-0">
                    <span className="material-symbols-outlined" aria-hidden="true">lock</span>
                  </div>
                  <span className="text-label-md">End-to-End Encrypted</span>
                </div>
              </div>
            </div>
          </div>

          {/* Error */}
          {error && (
            <p className="text-body-md text-error text-center mt-6" role="alert">
              {error}
            </p>
          )}

          {/* Submit */}
          <div className="mt-12 flex flex-col items-center gap-4">
            <button
              type="submit"
              disabled={!isValid || loading}
              aria-disabled={!isValid || loading}
              className="bg-primary hover:bg-primary/90 disabled:bg-surface-container-high disabled:text-outline disabled:cursor-not-allowed text-on-primary px-12 py-4 rounded-full text-headline-md shadow-lg transition-all active:scale-95 flex items-center gap-3 min-h-[56px]"
            >
              {loading ? (
                <>
                  <div className="w-5 h-5 border-2 border-on-primary/40 border-t-on-primary rounded-full animate-spin" />
                  Getting ready...
                </>
              ) : (
                <>
                  Continue to Assessment
                  <span className="material-symbols-outlined" aria-hidden="true">arrow_forward</span>
                </>
              )}
            </button>
          </div>
        </form>
      </main>

      {/* The VERA Edge */}
      <section
        className="max-w-7xl mx-auto px-container-padding-mobile md:px-container-padding-desktop mb-20"
        aria-label="Why VERA"
      >
        <div className="bg-surface-variant/30 rounded-[32px] overflow-hidden grid grid-cols-1 md:grid-cols-2 items-center">
          <div className="p-8 md:p-12 lg:p-16">
            <span className="inline-block px-4 py-1 rounded-full bg-tertiary-container text-on-tertiary-container text-label-sm mb-6 uppercase tracking-wider">
              The VERA Edge
            </span>
            <h3 className="text-headline-lg text-on-surface mb-6">
              Expert guidance, personalised for your life.
            </h3>
            <p className="text-body-lg text-on-surface-variant mb-8">
              By understanding your unique profile, VERA can cross-reference the
              latest medical research to help you catch risks before they become issues.
            </p>
            <div className="space-y-4">
              <div className="flex items-start gap-4">
                <span className="material-symbols-outlined text-primary mt-1" aria-hidden="true">check_circle</span>
                <div>
                  <p className="text-label-md text-on-surface">Data-Driven Screenings</p>
                  <p className="text-body-md text-on-surface-variant">Assessments that adjust based on your age and health history.</p>
                </div>
              </div>
              <div className="flex items-start gap-4">
                <span className="material-symbols-outlined text-primary mt-1" aria-hidden="true">check_circle</span>
                <div>
                  <p className="text-label-md text-on-surface">Local Specialist Guidance</p>
                  <p className="text-body-md text-on-surface-variant">VERA identifies local doctors who specialise in your specific needs and helps you reach them.</p>
                </div>
              </div>
            </div>
          </div>
          <div className="h-[400px] md:h-full relative overflow-hidden">
            <img
              src="https://lh3.googleusercontent.com/aida-public/AB6AXuAk3gve4JC6X9O7C4UWPeriZ3akStwQYU9W_0mbChNFX_V87ZtsWBYWl27K_kg5KeMPrXvWkfz6nUALgALRrP7bub69Kw0hGV2sy7l2Ahz4TCsG1w8TgEOHDj2p7h1lLLFHuG3EOMbYuFYlUHdwqudJuObZwR-HJgFY0oAb3GpvpyYBdielLZbaYpMENpxIRgqz352IVqc3dPYLWuqEspC6FOpOQp0MRsu_Yk0p16coi4Gr-RwwBmcF38-Iu9Jj6SnB8UfOs7JvCeAs"
              alt="A doctor with a tablet in a bright modern clinic"
              className="w-full h-full object-cover"
            />
            <div
              className="absolute inset-0 bg-gradient-to-r from-surface-variant/50 to-transparent hidden md:block"
              aria-hidden="true"
            />
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="py-12 border-t border-outline-variant/30">
        <div className="max-w-7xl mx-auto px-container-padding-mobile md:px-container-padding-desktop flex flex-col items-center gap-4 text-center">
          <VeraLogo className="h-8 w-auto grayscale opacity-60" />
          <p className="text-label-sm text-outline max-w-md leading-relaxed">
            VERA is a health awareness tool, not a medical device. Always consult a qualified doctor.
          </p>
        </div>
      </footer>
    </div>
  );
}
