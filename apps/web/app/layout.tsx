import "./globals.css";
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Agent Reliability Platform (ARP) - AI Observability & Reliability Engineering",
  description: "Distributed tracing, reliability findings, deterministic policy enforcement, regression detection, and model cost visibility for AI agents.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="dark">
      <body className="bg-background text-foreground antialiased selection:bg-cyan-500/20 selection:text-cyan-300">
        {children}
      </body>
    </html>
  );
}
