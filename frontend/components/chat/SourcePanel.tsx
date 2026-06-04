"use client";

import { FileText, Calendar, Clock, ExternalLink, X } from 'lucide-react';
import { motion } from 'motion/react';
import { Citation } from '../../types';

interface SourcePanelProps {
  activeCitation: Citation | null;
  setIsPanelOpen: (isOpen: boolean) => void;
}

export function SourcePanel({ activeCitation, setIsPanelOpen }: SourcePanelProps) {
  return (
    <motion.aside 
      initial={{ width: 0, opacity: 0 }}
      animate={{ width: "auto", opacity: 1 }}
      exit={{ width: 0, opacity: 0 }}
      transition={{ duration: 0.2, ease: "easeOut" }}
      className="h-full bg-white/[0.04] backdrop-blur-xl border-l border-black/10 dark:border-white/10 flex flex-col z-50 shrink-0 absolute right-0 top-0 md:relative shadow-md overflow-hidden"
    >
      <div className="w-[320px] md:w-[380px] h-full flex flex-col shrink-0">
        <div className="h-16 px-5 border-b border-black/10 dark:border-white/10 flex items-center justify-between shrink-0 bg-white/[0.02]">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-[#ea0029]/10 border border-[#ea0029]/20 flex items-center justify-center text-[#ea0029]">
              <FileText className="w-4 h-4" />
            </div>
            <div>
              <h2 className="text-sm font-bold text-[#1b1b1b] dark:text-white">Panel Nguồn</h2>
              <p className="text-[10px] text-gray-600 dark:text-gray-400 font-bold uppercase tracking-widest truncate max-w-[150px] md:max-w-[200px]">
                {activeCitation?.title || 'Tài liệu'}
              </p>
            </div>
          </div>
          <button 
            onClick={() => setIsPanelOpen(false)}
            className="text-gray-600 dark:text-gray-400 hover:text-[#1b1b1b] dark:hover:text-white transition-colors p-1.5 rounded-full hover:bg-black/5 dark:bg-white/5"
          >
            <X className="w-5 h-5" />
          </button>
        </div>
        
        <div className="p-6 pb-2">
          <div className="mb-6 border-b border-black/10 dark:border-white/10 pb-5">
            <h1 className="text-lg font-bold text-[#1b1b1b] dark:text-white mb-3 leading-tight tracking-wide">Quy Định Nghỉ Phép Năm 2026</h1>
            <div className="flex gap-4 text-[10px] font-bold text-gray-600 dark:text-gray-400 uppercase tracking-widest">
              <span className="flex items-center gap-1.5"><Calendar className="w-3.5 h-3.5" /> Hiệu lực: 01/01/2026</span>
              <span className="flex items-center gap-1.5"><Clock className="w-3.5 h-3.5" /> Bản cập nhật: V.2</span>
            </div>
          </div>
        </div>
        
        <div className="flex-1 overflow-y-auto px-6 pb-6">
          <div className="text-sm text-gray-700 dark:text-gray-300 leading-relaxed space-y-6 font-normal">
            <section>
              <h3 className="text-sm font-bold text-[#1b1b1b] dark:text-white mb-2 tracking-wide">1. Mục đích và Phạm vi</h3>
              <p>Quy định này thiết lập các nguyên tắc và thủ tục liên quan đến việc nghỉ phép năm của toàn bộ nhân viên chính thức tại công ty, nhằm đảm bảo quyền lợi phúc lợi.</p>
            </section>
            
            <section className="bg-black/5 dark:bg-white/5 -mx-4 px-4 py-4 border-l-2 border-[#ea0029]">
              <div className="flex items-center justify-between mb-3">
                <h3 className="text-sm font-bold text-[#ea0029] tracking-wide">2.1. Tiêu chuẩn ngày phép năm</h3>
                <span className="bg-[#ea0029] text-white text-[9px] px-2 py-0.5 rounded-full font-bold uppercase tracking-widest shadow-sm">Trích dẫn</span>
              </div>
              <p>Mỗi nhân viên làm việc đủ 12 tháng trong một năm dương lịch được hưởng <strong className="text-[#ea0029] font-bold">12 ngày phép năm</strong> hưởng nguyên lương.</p>
              <ul className="list-disc pl-5 mt-3 space-y-2 text-gray-700 dark:text-gray-300 text-xs">
                <li>Nhân viên thử việc chưa được tính phép năm.</li>
                <li>Phép năm được cộng dồn theo từng tháng (1 ngày/tháng).</li>
              </ul>
            </section>
            
            <section>
              <h3 className="text-sm font-bold text-[#1b1b1b] dark:text-white mb-2 tracking-wide">2.2. Chuyển phép tồn</h3>
              <p>Phép năm không sử dụng hết được phép chuyển sang năm tiếp theo tối đa <strong className="font-bold text-[#ea0029]">05 ngày</strong>. Phải sử dụng trước ngày 31/03.</p>
            </section>
          </div>
        </div>
        
        <div className="p-5 border-t border-black/10 dark:border-white/10 shrink-0 bg-white/[0.02]">
          <button className="w-full py-3 bg-black/10 dark:bg-white/10 hover:bg-black/20 dark:bg-white/20 border border-black/10 dark:border-white/10 text-[#1b1b1b] dark:text-white font-bold text-sm rounded-xl transition-colors flex items-center justify-center gap-2 tracking-wide">
            <ExternalLink className="w-4 h-4 text-gray-600 dark:text-gray-400" />
            Mở toàn văn bản (PDF)
          </button>
        </div>
      </div>
    </motion.aside>
  );
}
