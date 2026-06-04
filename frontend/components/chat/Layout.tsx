"use client";

import type { ReactNode } from "react";
import { SideNavBar } from './SideNavBar';
import { TopAppBar } from './TopAppBar';

type LayoutProps = {
  content: ReactNode;
  onLogout?: () => void;
};

export function Layout({ content, onLogout }: LayoutProps) {
  return (
    <div className="flex w-full h-screen relative bg-[#f9f9f9] dark:bg-[#0a0a0a] text-[#1b1b1b] dark:text-white overflow-hidden">
      <div className="mesh-bg pointer-events-none"></div>
      
      <SideNavBar />

      <div className="flex-1 flex flex-col h-full relative z-10 w-full overflow-hidden">
        <TopAppBar onLogout={onLogout} />

        <div className="flex-1 flex flex-row relative h-[calc(100vh-64px)] overflow-hidden">
          {content}
        </div>
      </div>
    </div>
  );
}
