// Render an ISO 3166-1 alpha-2 country code as a unicode flag emoji.
// Works for any two-letter code; falls back to a globe for invalid input.

export function countryFlag(country: string): string {
  if (!country || country.length !== 2) return "🌐";
  const c = country.toUpperCase();
  if (!/^[A-Z]{2}$/.test(c)) return "🌐";
  const A = 0x1f1e6; // Regional indicator 'A'
  const codePoints = [...c].map((ch) => A + (ch.charCodeAt(0) - 65));
  return String.fromCodePoint(...codePoints);
}
