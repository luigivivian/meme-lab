import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "memeLab — clip-flow dashboard",
  description: "Dashboard para o pipeline multi-agente clip-flow",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="pt-BR" className="dark">
      <head>
        <link
          href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap"
          rel="stylesheet"
        />
      </head>
      <body className="antialiased">
        {children}
      </body>
    </html>
  );
}
