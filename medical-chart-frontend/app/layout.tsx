import type { Metadata } from 'next';
import { Inter, Noto_Sans_JP } from 'next/font/google';
import './styles/globals.css';

const inter = Inter({ subsets: ['latin'] });
const notoSansJp = Noto_Sans_JP({ 
  weight: ['400', '500', '700'],
  subsets: ['latin'],
  variable: '--font-noto-sans-jp',
});

export const metadata: Metadata = {
  title: '紙カルテ電子化・構造化システム',
  description: '紙カルテ画像をアップロードし、AIにより主訴、現病歴などを抽出するシステム',
};

// 医療アイコンコンポーネント
const MedicalIcon = () => (
  <svg xmlns="http://www.w3.org/2000/svg" className="h-8 w-8 mr-3 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
  </svg>
);

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="ja">
      <body className={`${inter.className} ${notoSansJp.variable} min-h-screen overflow-hidden font-sans`}>
        <header className="bg-gradient-to-r from-blue-600 to-indigo-700 p-4 shadow-md relative overflow-hidden">
          <div className="absolute inset-0 bg-grid-white/[0.05] bg-[length:16px_16px]"></div>
          <div className="absolute inset-0 bg-gradient-to-b from-black/[0.05] to-transparent"></div>
          <div className="relative flex items-center">
            <MedicalIcon />
            <h1 className="text-2xl font-bold text-white tracking-wide">カルテ情報抽出システム</h1>
          </div>
        </header>
        {children}
      </body>
    </html>
  );
}
