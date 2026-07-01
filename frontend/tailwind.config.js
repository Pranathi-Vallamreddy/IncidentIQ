/** @type {import('tailwindcss').Config} */
export default {
  darkMode: "class",
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        canvas: "#0a0a0b",
        panel: "#0f0f11",
        card: "#151518",
        elevated: "#1b1b1f",
        hairline: "#26262b",
        muted: "#8a8a94",
        faint: "#5f5f68",
        ink: "#f4f4f5",
        sev: {
          critical: "#f87171",
          high: "#fb923c",
          medium: "#facc15",
          low: "#60a5fa",
        },
      },
      fontFamily: {
        sans: ["Inter", "ui-sans-serif", "system-ui", "sans-serif"],
        mono: ["ui-monospace", "SFMono-Regular", "Menlo", "monospace"],
      },
      borderRadius: {
        xl: "0.9rem",
      },
      keyframes: {
        "fade-in": { from: { opacity: "0", transform: "translateY(4px)" }, to: { opacity: "1", transform: "translateY(0)" } },
        pulse2: { "0%,100%": { opacity: "1" }, "50%": { opacity: "0.35" } },
      },
      animation: {
        "fade-in": "fade-in 0.25s ease-out",
        pulse2: "pulse2 2s ease-in-out infinite",
      },
    },
  },
  plugins: [],
};
