import type { Metadata, Viewport } from "next";
import { Inter, Space_Grotesk, Noto_Sans_Devanagari, JetBrains_Mono } from "next/font/google";
import "./globals.css";

const inter = Inter({
  variable: "--font-body",
  subsets: ["latin"],
  display: "swap",
});

const spaceGrotesk = Space_Grotesk({
  variable: "--font-display",
  subsets: ["latin"],
  display: "swap",
});

const notoDevanagari = Noto_Sans_Devanagari({
  variable: "--font-noto-devanagari",
  subsets: ["devanagari", "latin"],
  display: "swap",
});

const jetbrainsMono = JetBrains_Mono({
  variable: "--font-mono",
  subsets: ["latin"],
  display: "swap",
});

export const metadata: Metadata = {
  title: {
    default: "Scheme Finder Line — Voice-Enabled Government Scheme Discovery",
    template: "%s | Scheme Finder Line",
  },
  description:
    "A production-ready voice-enabled assistant that helps citizens discover and understand government schemes through natural conversation in 11 Indian languages + English. Built with Gnani Prisma STT, Evon LLM, and Timbre TTS.",
  keywords: [
    "government schemes",
    "voice assistant",
    "speech to text",
    "text to speech",
    "Gnani AI",
    "Prisma STT",
    "Timbre TTS",
    "Evon LLM",
    "Twilio Media Streams",
    "Indian languages",
  ],
  authors: [{ name: "Scheme Finder Line Team" }],
  creator: "Scheme Finder Line",
  publisher: "Scheme Finder Line",
  robots: "index, follow",
  openGraph: {
    type: "website",
    locale: "en_IN",
    url: "https://scheme-finder-line.vercel.app",
    siteName: "Scheme Finder Line",
    title: "Scheme Finder Line — Voice-Enabled Government Scheme Discovery",
    description:
      "Discover government schemes through natural voice conversation in your language.",
    images: [
      {
        url: "/og-image.png",
        width: 1200,
        height: 630,
        alt: "Scheme Finder Line - Voice Assistant for Government Schemes",
      },
    ],
  },
  twitter: {
    card: "summary_large_image",
    title: "Scheme Finder Line",
    description: "Voice-enabled government scheme discovery in 11 Indian languages",
    images: ["/og-image.png"],
  },
  verification: {
    google: "google-site-verification-code",
  },
};

export const viewport: Viewport = {
  themeColor: [
    { media: "(prefers-color-scheme: light)", color: "#ffffff" },
    { media: "(prefers-color-scheme: dark)", color: "#0a0a0f" },
  ],
  colorScheme: "dark",
  width: "device-width",
  initialScale: 1,
  maximumScale: 5,
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html
      lang="en"
      className={`${inter.variable} ${spaceGrotesk.variable} ${notoDevanagari.variable} ${jetbrainsMono.variable} h-full antialiased`}
      suppressHydrationWarning
    >
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
        <link rel="dns-prefetch" href="https://api.vachana.ai" />
      </head>
      <body className="min-h-full flex flex-col bg-bg-primary text-text-primary">
        {children}
      </body>
    </html>
  );
}