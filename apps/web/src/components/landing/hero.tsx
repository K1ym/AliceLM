"use client"
import Image from "next/image"
import { useScroll, useTransform, motion } from "framer-motion"
import { useRef } from "react"
import Header from "./header"

export default function Hero() {
  const container = useRef(null)
  const { scrollYProgress } = useScroll({
    target: container,
    offset: ["start start", "end start"],
  })

  const y = useTransform(scrollYProgress, [0, 1], ["0vh", "150vh"])

  return (
    <div ref={container} className="h-screen overflow-hidden relative">
      <Header />
      <motion.div style={{ y }} className="absolute inset-0">
        <Image
          src="/images/1.png"
          fill
          alt="Cherry blossoms"
          className="object-cover"
          priority
        />
        <div className="absolute inset-0 bg-black/40" />
      </motion.div>
      <div className="absolute inset-0 flex items-end z-10 pb-16 sm:pb-20 md:pb-28">
        <div className="text-left text-white px-6 md:px-12 lg:px-16">
          <p className="text-xs md:text-sm uppercase tracking-[0.2em] text-white/60 mb-4 md:mb-6">
            Anything to Knowledge
          </p>
          <h1 className="text-4xl sm:text-5xl md:text-7xl lg:text-8xl font-light mb-6 md:mb-8 leading-[0.95] tracking-tight">
            <span className="block">让世界的声音，</span>
            <span className="block font-normal">凝为你的洞见。</span>
          </h1>
          <p className="text-sm md:text-base text-white/70 max-w-md mb-8 md:mb-10 font-light leading-relaxed">
            自动转写 / AI摘要 / 智能问答 / 智能检索
          </p>
          <a 
            href="/home" 
            className="inline-block px-6 py-3 bg-white text-neutral-900 text-xs md:text-sm uppercase tracking-wider font-medium transition-all duration-300 hover:bg-white/90"
          >
            Get Started
          </a>
        </div>
      </div>
    </div>
  )
}
