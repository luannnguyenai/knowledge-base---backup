"use client";

import { Search, Bell, User, LogOut, Moon, Sun } from 'lucide-react';
import { useRouter } from 'next/navigation';
import { useState, useRef, useEffect } from 'react';
import { useTheme } from '@/ThemeProvider';

interface TopAppBarProps {
  onLogout?: () => void;
}

export function TopAppBar({ onLogout }: TopAppBarProps) {
  const [showNotifications, setShowNotifications] = useState(false);
  const [showProfileMenu, setShowProfileMenu] = useState(false);
  const notificationRef = useRef<HTMLDivElement>(null);
  const profileMenuRef = useRef<HTMLDivElement>(null);
  const router = useRouter();
  const { theme, toggleTheme } = useTheme();

  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (notificationRef.current && !notificationRef.current.contains(event.target as Node)) {
        setShowNotifications(false);
      }
      if (profileMenuRef.current && !profileMenuRef.current.contains(event.target as Node)) {
        setShowProfileMenu(false);
      }
    }
    document.addEventListener('mousedown', handleClickOutside);
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, []);

  return (
    <header className="bg-white/[0.02] backdrop-blur-[16px] w-full z-40 border-b border-black/10 dark:border-white/10 flex justify-between items-center h-16 px-4 md:px-8 shrink-0 shadow-sm shadow-black/5 dark:shadow-black/10">
      <div className="flex items-center gap-4">
      </div>
      <div className="flex items-center gap-4 md:gap-6">
        <div className="relative group hidden sm:flex items-center">
          <Search className="w-4 h-4 absolute left-3.5 text-gray-500 dark:text-gray-500 group-focus-within:text-[#1b1b1b] dark:group-focus-within:text-white transition-colors" />
          <input 
            className="pl-10 pr-4 py-2 bg-black/5 dark:bg-white/5 border border-black/10 dark:border-white/10 focus:border-black/30 dark:border-white/30 focus:ring-1 focus:ring-black/30 dark:ring-white/30 rounded-full text-sm text-[#1b1b1b] dark:text-white w-48 md:w-64 transition-all focus:w-64 md:focus:w-80 outline-none placeholder:text-gray-500 dark:text-gray-500" 
            placeholder="Tìm kiếm chính sách..." 
            type="text" 
          />
        </div>

        <div className="flex items-center gap-2 md:gap-4">
          <button
            onClick={toggleTheme}
            className="transition-colors p-2 rounded-full text-gray-600 dark:text-gray-400 hover:text-[#1b1b1b] dark:hover:text-white hover:bg-black/10 dark:hover:bg-white/10 hover:scale-110 active:scale-95"
            title="Toggle theme"
          >
            {theme === 'dark' ? <Sun className="w-5 h-5" /> : <Moon className="w-5 h-5" />}
          </button>

          <div className="relative flex items-center" ref={notificationRef}>
            <button 
              onClick={() => setShowNotifications(!showNotifications)}
              className={`transition-colors p-2 rounded-full relative ${showNotifications ? 'text-[#1b1b1b] dark:text-white bg-black/10 dark:bg-white/10' : 'text-gray-600 dark:text-gray-400 hover:text-[#1b1b1b] dark:hover:text-white hover:bg-black/10 dark:bg-white/10 hover:scale-110 active:scale-95'}`}
            >
              <Bell className="w-5 h-5" />
              <span className="absolute top-1 right-1.5 w-2 h-2 bg-red-500 rounded-full border border-black/50"></span>
            </button>
            
            {showNotifications && (
              <div className="absolute top-12 right-0 w-80 bg-white dark:bg-[#1e1e1e] border border-black/10 dark:border-white/10 rounded-xl shadow-2xl z-50 overflow-hidden flex flex-col">
                <div className="p-4 border-b border-black/10 dark:border-white/10 flex justify-between items-center bg-black/5 dark:bg-white/5">
                  <h3 className="text-[#1b1b1b] dark:text-white font-semibold flex items-center gap-2">
                    <Bell className="w-4 h-4 text-gray-600 dark:text-gray-400" /> Notifications
                  </h3>
                  <span className="text-xs bg-red-500/20 text-red-400 border border-red-500/20 px-2 py-0.5 rounded-full font-medium">3 New</span>
                </div>
                <div className="max-h-80 overflow-y-auto">
                  <div className="p-4 border-b border-black/5 dark:border-white/5 hover:bg-black/5 dark:bg-white/5 cursor-pointer transition-colors relative">
                    <div className="absolute left-0 top-0 bottom-0 w-1 bg-red-500"></div>
                    <p className="text-sm text-gray-800 dark:text-gray-200"><strong>Policy Update:</strong> Remote work policy has been revised for 2026.</p>
                    <p className="text-xs text-gray-500 dark:text-gray-500 mt-1">10 minutes ago</p>
                  </div>
                  <div className="p-4 border-b border-black/5 dark:border-white/5 hover:bg-black/5 dark:bg-white/5 cursor-pointer transition-colors relative">
                    <div className="absolute left-0 top-0 bottom-0 w-1 bg-red-500"></div>
                    <p className="text-sm text-gray-800 dark:text-gray-200"><strong>System Alert:</strong> HR system will undergo maintenance this weekend.</p>
                    <p className="text-xs text-gray-500 dark:text-gray-500 mt-1">2 hours ago</p>
                  </div>
                  <div className="p-4 border-b border-black/5 dark:border-white/5 hover:bg-black/5 dark:bg-white/5 cursor-pointer transition-colors relative">
                    <div className="absolute left-0 top-0 bottom-0 w-1 bg-red-500"></div>
                    <p className="text-sm text-gray-800 dark:text-gray-200"><strong>Action Required:</strong> Please complete your annual compliance training.</p>
                    <p className="text-xs text-gray-500 dark:text-gray-500 mt-1">Yesterday</p>
                  </div>
                  <div className="p-4 hover:bg-black/5 dark:bg-white/5 cursor-pointer transition-colors text-gray-600 dark:text-gray-400">
                    <p className="text-sm"><strong>Welcome!</strong> Thank you for joining the HR Policy Explorer.</p>
                    <p className="text-xs text-gray-600 mt-1">Last week</p>
                  </div>
                </div>
                <div className="p-3 border-t border-black/10 dark:border-white/10 text-center bg-black/5 dark:bg-white/5 hover:bg-black/10 dark:bg-white/10 cursor-pointer transition-colors">
                  <span className="text-sm text-blue-400 font-medium">Mark all as read</span>
                </div>
              </div>
            )}
          </div>

          <div className="relative flex items-center" ref={profileMenuRef}>
            <button 
              title="Profile"
              onClick={() => setShowProfileMenu(!showProfileMenu)}
              className={`transition-all duration-200 p-2 rounded-full transform ${showProfileMenu ? 'text-[#1b1b1b] dark:text-white bg-black/10 dark:bg-white/10 ring-2 ring-black/20 dark:ring-white/20' : 'text-gray-600 dark:text-gray-400 hover:text-[#1b1b1b] dark:hover:text-white hover:bg-black/10 dark:bg-white/10 hover:scale-110 active:scale-95'}`}
            >
              <User className="w-5 h-5" />
            </button>

            {showProfileMenu && (
              <div className="absolute top-12 right-0 w-48 bg-white dark:bg-[#1e1e1e] border border-black/10 dark:border-white/10 rounded-xl shadow-2xl z-50 overflow-hidden flex flex-col py-2">
                <div 
                  className="px-4 py-2 hover:bg-black/5 dark:bg-white/5 cursor-pointer transition-colors flex items-center gap-3 text-gray-800 dark:text-gray-200 hover:text-[#1b1b1b] dark:hover:text-white"
                  onClick={() => {
                    setShowProfileMenu(false);
                    router.push('/profile');
                  }}
                >
                  <User className="w-4 h-4" />
                  <span className="text-sm font-medium">Profile</span>
                </div>
                
                <div className="my-1 border-t border-black/10 dark:border-white/10"></div>
                
                <div 
                  className="px-4 py-2 hover:bg-[#ea0029]/10 cursor-pointer transition-colors flex items-center gap-3 text-red-500 hover:text-red-400"
                  onClick={() => {
                    setShowProfileMenu(false);
                    onLogout?.();
                  }}
                >
                  <LogOut className="w-4 h-4" />
                  <span className="text-sm font-medium">Logout</span>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </header>
  );
}
