import { MessageSquarePlus, FileText, CreditCard, HeartPulse, Calendar, History, Plus, Settings, HelpCircle, Info } from 'lucide-react';
import { NavLink } from 'react-router-dom';

export function SideNavBar() {
  const getNavClasses = ({ isActive }: { isActive: boolean }) => {
    return `flex items-center space-x-3 px-4 py-3 rounded-lg font-semibold active:scale-95 duration-150 transition-colors ${
      isActive 
        ? 'bg-[#ea0029]/10 text-[#ea0029] shadow-sm' 
        : 'text-gray-600 dark:text-gray-400 hover:bg-black/5 dark:hover:bg-white/5 hover:text-[#1b1b1b] dark:hover:text-white'
    }`;
  };

  return (
    <nav className="w-[280px] h-full flex flex-col z-40 bg-white/[0.03] backdrop-blur-xl border-r border-black/10 dark:border-white/10 shrink-0 hidden md:flex">
      <div className="px-6 py-4 flex flex-col gap-1 mb-4 h-16 justify-center">
        <div className="flex items-center justify-start py-2 gap-3">
          <div className="w-8 h-8 rounded-lg bg-gradient-to-tr from-[#ea0029] to-[#a3001c] flex items-center justify-center shadow-md shadow-[#ea0029]/10 shrink-0">
            <span className="text-white font-bold text-sm">VF</span>
          </div>
          <span className="font-bold text-lg tracking-tight text-[#1b1b1b] dark:text-white">HR Portal</span>
        </div>
      </div>
      
      <div className="flex-1 overflow-y-auto px-4 flex flex-col gap-1">
        <div className="space-y-1">
          <NavLink to="/overview" className={getNavClasses}>
            <Info className="w-5 h-5" />
            <span className="text-sm">Overview</span>
          </NavLink>
          <NavLink to="/" className={getNavClasses}>
            <MessageSquarePlus className="w-5 h-5" />
            <span className="text-sm">HR Assistant</span>
          </NavLink>
          <a className="flex items-center space-x-3 px-4 py-3 text-gray-600 dark:text-gray-400 hover:bg-black/5 dark:hover:bg-white/5 hover:text-[#1b1b1b] dark:hover:text-white rounded-lg transition-colors active:scale-95 duration-150 cursor-pointer" href="#">
            <FileText className="w-5 h-5" />
            <span className="text-sm">Policy Guide</span>
          </a>
          <a className="flex items-center space-x-3 px-4 py-3 text-gray-600 dark:text-gray-400 hover:bg-black/5 dark:hover:bg-white/5 hover:text-[#1b1b1b] dark:hover:text-white rounded-lg transition-colors active:scale-95 duration-150 cursor-pointer" href="#">
            <HeartPulse className="w-5 h-5" />
            <span className="text-sm">Benefits</span>
          </a>
          <a className="flex items-center space-x-3 px-4 py-3 text-gray-600 dark:text-gray-400 hover:bg-black/5 dark:hover:bg-white/5 hover:text-[#1b1b1b] dark:hover:text-white rounded-lg transition-colors active:scale-95 duration-150 cursor-pointer" href="#">
            <CreditCard className="w-5 h-5" />
            <span className="text-sm font-medium">Salary & Pay</span>
          </a>
        </div>
        
        <div className="h-px w-full bg-black/10 dark:bg-white/10 my-4"></div>
        
        <div className="px-4 mb-2 text-[10px] font-bold text-gray-500 dark:text-gray-500 uppercase tracking-widest">Lịch sử hội thoại</div>
        <a className="flex items-center gap-3 text-gray-700 dark:text-gray-300 hover:text-[#1b1b1b] dark:hover:text-white px-4 py-1.5 hover:bg-black/5 dark:hover:bg-white/5 transition-colors duration-200 rounded-xl group" href="#">
          <History className="w-[18px] h-[18px] opacity-70 group-hover:opacity-100" />
          <span className="text-sm truncate font-medium">Cách tính lương OT ngày lễ</span>
        </a>
        <a className="flex items-center gap-3 text-gray-700 dark:text-gray-300 hover:text-[#1b1b1b] dark:hover:text-white px-4 py-1.5 hover:bg-black/5 dark:hover:bg-white/5 transition-colors duration-200 rounded-xl group" href="#">
          <History className="w-[18px] h-[18px] opacity-70 group-hover:opacity-100" />
          <span className="text-sm truncate font-medium">Cập nhật tài khoản ngân hàng</span>
        </a>
      </div>
      
      <div className="px-4 mt-auto pt-4 pb-4 border-t border-black/10 dark:border-white/10 flex flex-col gap-3">
        <button className="w-full bg-[#ea0029] text-white rounded-xl font-bold text-sm px-4 py-3 shadow-lg shadow-[#ea0029]/30 hover:bg-[#a3001c] transition-all active:scale-95 flex items-center justify-center gap-2">
          <Plus className="w-5 h-5" />
          Apply for Leave
        </button>
        <div className="flex justify-between mt-2">
          <a className="flex items-center gap-2 text-gray-600 dark:text-gray-400 hover:text-[#1b1b1b] dark:hover:text-white p-2 hover:bg-black/5 dark:hover:bg-white/5 rounded-lg transition-colors" href="#">
            <Settings className="w-4 h-4" />
            <span className="text-[11px] font-bold">Settings</span>
          </a>
          <a className="flex items-center gap-2 text-gray-600 dark:text-gray-400 hover:text-[#1b1b1b] dark:hover:text-white p-2 hover:bg-black/5 dark:hover:bg-white/5 rounded-lg transition-colors" href="#">
            <HelpCircle className="w-4 h-4" />
            <span className="text-[11px] font-bold">Help Center</span>
          </a>
        </div>
      </div>
    </nav>
  );
}
