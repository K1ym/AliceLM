"use client"

import Image from "next/image"
import { useScroll, useTransform, motion } from "framer-motion"
import { useRef } from "react"

export default function Section() {
  const container = useRef(null)
  const { scrollYProgress } = useScroll({
    target: container,
    offset: ["start end", "end start"],
  })
  const y = useTransform(scrollYProgress, [0, 1], ["-10vh", "10vh"])

  return (
    <div
      ref={container}
      className="relative flex items-center justify-center h-screen overflow-hidden"
      style={{ clipPath: "polygon(0% 0, 100% 0%, 100% 100%, 0 100%)" }}
    >
      <div className="fixed top-[-10vh] left-0 h-[120vh] w-full">
        <motion.div style={{ y }} className="relative w-full h-full">
          <Image 
            src="/images/3.png" 
            fill 
            alt="Misty forest" 
            className="object-cover"
          />
          <div className="absolute inset-0 bg-black/50" />
        </motion.div>
      </div>

      <div className="relative z-10 max-w-6xl mx-auto px-8 md:px-12 w-full h-full flex flex-col justify-end py-16 md:py-24">
        <div className="max-w-xl">
          <p className="text-sm text-white/50 uppercase tracking-widest mb-4">
            Knowledge Graph
          </p>
          <h2 className="text-3xl sm:text-4xl md:text-5xl font-semibold text-white leading-[1.15] mb-6">
            繁杂的信息中，
            <br />
            构建真正价值。
          </h2>
          <p className="text-lg text-white/60 leading-relaxed">
            让AI帮你构建知识网络，发现知识间的联系。
          </p>
        </div>
      </div>
    </div>
  )
}
