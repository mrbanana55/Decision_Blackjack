/** @type {import('tailwindcss').Config} */
export default {
  darkMode: ["class"],
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      fontFamily: {
        display: ['"Space Grotesk"', 'system-ui', '-apple-system', 'sans-serif'],
        sans: ['"Plus Jakarta Sans"', '"Geist Variable"', 'system-ui', '-apple-system', 'sans-serif'],
        mono: ['ui-monospace', 'SFMono-Regular', 'Menlo', 'Monaco', 'Consolas', 'monospace'],
      },
      colors: {
        border: "var(--border)",
        input: "var(--input)",
        ring: "var(--ring)",
        background: "var(--background)",
        foreground: "var(--foreground)",
        canvas: "#0a0d3a",
        surface: {
          indigo: "#1e2353",
          onyx: "#23272a",
          black: "#000000",
        },
        blurple: {
          DEFAULT: "#5865f2",
          hover: "#4752c4",
          light: "#7983f5",
          dark: "#3c45a5",
        },
        discord: {
          green: "#35ed7e",
          magenta: "#ec48bd",
          link: "#00b0f4",
          canvas: "#0a0d3a",
          surface: "#1e2353",
          onyx: "#23272a",
          muted: "#949ba4",
          hairline: "#2b305c",
        },
        primary: {
          DEFAULT: "var(--primary)",
          foreground: "var(--primary-foreground)",
        },
        secondary: {
          DEFAULT: "var(--secondary)",
          foreground: "var(--secondary-foreground)",
        },
        destructive: {
          DEFAULT: "var(--destructive)",
          foreground: "var(--destructive-foreground)",
        },
        muted: {
          DEFAULT: "var(--muted)",
          foreground: "var(--muted-foreground)",
        },
        accent: {
          DEFAULT: "var(--accent)",
          foreground: "var(--accent-foreground)",
        },
        popover: {
          DEFAULT: "var(--popover)",
          foreground: "var(--popover-foreground)",
        },
        card: {
          DEFAULT: "var(--card)",
          foreground: "var(--card-foreground)",
        },
        table: {
          green: "#0b6623",
          felt: "#1b4d3e",
        },
      },
      borderRadius: {
        xs: "6px",
        sm: "12px",
        md: "14px",
        lg: "16px",
        xl: "24px",
        "2xl": "32px",
        jumbo: "40px",
        pill: "50px",
      },
    },
  },
  plugins: [],
}
