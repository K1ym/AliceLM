import Image from "next/image"

export default function Featured() {
  return (
    <div className="min-h-screen bg-neutral-50 flex items-center">
      <div className="max-w-6xl mx-auto px-8 md:px-12 py-24 w-full">
        <div className="grid lg:grid-cols-2 gap-16 lg:gap-24 items-center">
          <div className="order-2 lg:order-1">
            <p className="text-sm text-neutral-500 uppercase tracking-widest mb-4">
              Core Features
            </p>
            <h2 className="text-3xl sm:text-4xl font-semibold text-neutral-900 leading-[1.2] mb-6">
              Multi ASR语音转写
              <br />
              <span className="text-neutral-500">Agent智能摘要</span>
              <br />
              <span className="text-neutral-400">RAG语义检索</span>
            </h2>
            <p className="text-lg text-neutral-600 leading-relaxed mb-8">
              将碎片化的视频内容，转化为结构化的知识体系。
            </p>
            <a 
              href="/videos" 
              className="inline-flex items-center px-6 py-3 bg-neutral-900 text-white text-sm font-medium rounded-full transition-all hover:bg-neutral-800"
            >
              查看知识库
            </a>
          </div>
          <div className="order-1 lg:order-2">
            <div className="aspect-[4/5] relative rounded-2xl overflow-hidden">
              <Image
                src="/images/2.png"
                alt="White flowers"
                fill
                className="object-cover"
              />
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
