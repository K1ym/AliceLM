import Link from "next/link"

export default function Header() {
  return (
    <header className="absolute top-0 left-0 right-0 z-20 px-8 py-6 md:px-12 md:py-8">
      <div className="flex justify-between items-center max-w-6xl mx-auto">
        <Link href="/" className="text-white text-xl font-medium tracking-tight">
          AliceLM
        </Link>
        <Link
          href="/home"
          className="text-sm font-medium px-5 py-2.5 bg-white text-neutral-900 rounded-full transition-all hover:bg-white/90"
        >
          Get Started
        </Link>
      </div>
    </header>
  )
}
