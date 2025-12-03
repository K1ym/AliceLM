"use client"

interface TabButtonProps {
  active: boolean
  onClick: () => void
  icon: React.ElementType
  label: string
}

export function TabButton({ active, onClick, icon: Icon, label }: TabButtonProps) {
  return (
    <button
      onClick={onClick}
      className={`flex-1 py-4 flex items-center justify-center gap-2 text-sm font-medium border-b-2 transition-colors ${
        active
          ? "border-neutral-900 text-neutral-900"
          : "border-transparent text-neutral-400 hover:text-neutral-600"
      }`}
    >
      <Icon size={16} />
      {label}
    </button>
  )
}
