"use client";

import React from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { Library, Settings, Plus, MessageSquare, Trash2, Network } from "lucide-react";
import { Conversation } from "@/lib/api";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import { Empty, EmptyDescription, EmptyHeader, EmptyMedia, EmptyTitle } from "@/components/ui/empty";

interface SidebarProps {
  conversations?: Conversation[];
  videoCount?: number;
  isOpen?: boolean;
  onToggle?: () => void;
  onNewChat?: () => void;
  onSelectChat?: (id: number | null) => void;
  onDeleteChat?: (id: number) => void;
  currentChatId?: number | null;
}

export function Sidebar({ 
  conversations = [], 
  videoCount = 0,
  isOpen = true, 
  onNewChat,
  onSelectChat,
  onDeleteChat,
  currentChatId,
}: SidebarProps) {
  const pathname = usePathname();
  const router = useRouter();

  const isActive = (path: string) => pathname === path;
  const isDashboard = pathname === "/home";

  const handleNewChat = () => {
    if (onNewChat) {
      onNewChat();
    } else {
      router.push("/home");
    }
  };

  const handleSelectChat = (id: number) => {
    if (onSelectChat) {
      onSelectChat(id);
    }
  };

  const handleDeleteChat = async (e: React.MouseEvent, id: number) => {
    e.stopPropagation();
    if (onDeleteChat) {
      onDeleteChat(id);
    }
  };

  return (
    <aside
      className={`
        fixed inset-y-0 left-0 z-40 w-64 bg-neutral-50 border-r border-neutral-100
        transform transition-transform duration-300 ease-in-out flex flex-col
        ${isOpen ? "translate-x-0" : "-translate-x-full"}
        md:relative md:translate-x-0
      `}
    >
      {/* Header */}
      <div className="p-6 pb-2">
        <Link href="/home" className="flex items-center gap-2 mb-6">
          <span className="font-bold text-xl tracking-tight">AliceLM</span>
        </Link>

        <button
          onClick={handleNewChat}
          className="w-full flex items-center gap-2 px-4 py-3 bg-white border border-neutral-200 shadow-sm rounded-xl text-sm font-medium hover:border-neutral-300 hover:shadow-md transition-all group"
        >
          <Plus size={16} className="text-neutral-500 group-hover:text-neutral-900" />
          <span className="text-neutral-700 group-hover:text-neutral-900">
            新对话
          </span>
        </button>
      </div>

      {/* Navigation */}
      <div className="flex-1 overflow-y-auto px-4 py-2 scrollbar-hide">
        {/* History */}
        <div className="mb-6">
          <div className="px-3 py-2 text-xs font-semibold text-neutral-400 uppercase tracking-widest">
            对话历史
          </div>
          {conversations.length > 0 ? (
            <div className="space-y-1 mt-1">
              {conversations.map((conv) => (
                <div
                  key={conv.id}
                  onClick={() => handleSelectChat(conv.id)}
                  className={`
                    group flex items-center justify-between px-3 py-2.5 rounded-lg text-sm cursor-pointer transition-colors
                    ${currentChatId === conv.id 
                      ? "bg-neutral-200 text-neutral-900" 
                      : "text-neutral-600 hover:bg-neutral-100"
                    }
                  `}
                >
                  <div className="flex items-center gap-2 min-w-0 flex-1">
                    <MessageSquare size={14} className="flex-shrink-0 opacity-50" />
                    <span className="truncate">{conv.title || "新对话"}</span>
                  </div>
                  <Tooltip>
                    <TooltipTrigger asChild>
                      <button
                        onClick={(e) => handleDeleteChat(e, conv.id)}
                        className="opacity-0 group-hover:opacity-100 p-1 hover:bg-neutral-200 rounded transition-all"
                      >
                        <Trash2 size={14} className="text-neutral-400 hover:text-red-500" />
                      </button>
                    </TooltipTrigger>
                    <TooltipContent side="right">删除对话</TooltipContent>
                  </Tooltip>
                </div>
              ))}
            </div>
          ) : (
            <Empty className="py-6 border-0">
              <EmptyHeader>
                <EmptyMedia variant="icon">
                  <MessageSquare size={20} />
                </EmptyMedia>
                <EmptyTitle className="text-sm">暂无对话</EmptyTitle>
                <EmptyDescription className="text-xs">
                  点击上方按钮开始新对话
                </EmptyDescription>
              </EmptyHeader>
            </Empty>
          )}
        </div>

        {/* Navigation Links */}
        <div className="space-y-1">
          <NavItem
            href="/home/library"
            icon={Library}
            label="知识库"
            count={videoCount}
            active={isActive("/home/library")}
          />
          <NavItem
            href="/home/graph"
            icon={Network}
            label="知识图谱"
            active={isActive("/home/graph")}
          />
        </div>
      </div>

      {/* Footer */}
      <div className="p-4 border-t border-neutral-100">
        <NavItem
          href="/home/settings"
          icon={Settings}
          label="设置"
          active={isActive("/home/settings")}
        />
      </div>
    </aside>
  );
}

interface NavItemProps {
  href: string;
  icon: React.ElementType;
  label: string;
  count?: number;
  active?: boolean;
}

function NavItem({ href, icon: Icon, label, count, active }: NavItemProps) {
  return (
    <Link
      href={href}
      className={`
        w-full flex items-center justify-between px-3 py-2.5 rounded-lg text-sm font-medium transition-colors
        ${
          active
            ? "bg-neutral-200 text-neutral-900"
            : "text-neutral-500 hover:bg-neutral-100 hover:text-neutral-900"
        }
      `}
    >
      <div className="flex items-center gap-3">
        <Icon size={18} strokeWidth={2} />
        <span>{label}</span>
      </div>
      {count !== undefined && count > 0 && (
        <span className="bg-neutral-100 text-neutral-600 px-1.5 py-0.5 rounded-md text-xs border border-neutral-200">
          {count}
        </span>
      )}
    </Link>
  );
}

export default Sidebar;
