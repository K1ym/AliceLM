import { Header, Hero, Featured, Promo, Footer } from "@/components/landing";

export default function Home() {
  return (
    <main className="min-h-screen bg-white">
      <Header />
      <Hero />
      <Featured />
      <Promo />
      <Footer />
    </main>
  );
}
