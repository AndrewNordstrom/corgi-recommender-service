import '@/styles/globals.css'
import { Metadata } from 'next'
import { Inter, JetBrains_Mono } from 'next/font/google'
import Sidebar from '@/components/layout/sidebar'
import Header from '@/components/layout/header'
import ThemeProvider from '@/components/providers/theme-provider'
// Remove toaster import

const inter = Inter({
  subsets: ['latin'],
  display: 'swap',
  variable: '--font-inter',
})

const jetbrainsMono = JetBrains_Mono({
  subsets: ['latin'],
  display: 'swap',
  variable: '--font-jetbrains-mono',
})

export const metadata: Metadata = {
  title: 'Corgi Recommender Service',
  description: 'A privacy-aware recommendation engine for the Fediverse. Small body. Big brain.',
  icons: {
    icon: [
      {
        media: '(prefers-color-scheme: light)',
        url: '/favicon/favicon-32x32.png',
        href: '/favicon/favicon-32x32.png',
      },
      {
        media: '(prefers-color-scheme: dark)',
        url: '/favicon/favicon-32x32.png',
        href: '/favicon/favicon-32x32.png',
      },
    ],
  },
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className={`${inter.variable} ${jetbrainsMono.variable} font-sans antialiased`}>
        <ThemeProvider attribute="class" defaultTheme="system" enableSystem>
          <div className="flex min-h-screen">
            <Sidebar />
            <div className="flex-1 ml-64">
              <Header />
              <main className="p-6">
                {children}
              </main>
            </div>
          </div>
          {/* Remove Toaster component */}
        </ThemeProvider>
      </body>
    </html>
  )
}