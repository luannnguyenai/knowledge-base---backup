import { Paperclip, Send } from 'lucide-react';

interface ChatInputProps {
  inputValue: string;
  setInputValue: (value: string) => void;
  handleSendMessage: () => void;
}

export function ChatInput({ inputValue, setInputValue, handleSendMessage }: ChatInputProps) {
  return (
    <div className="w-full px-4 md:px-12 lg:px-16 xl:px-24 pb-6 shrink-0 z-10 pt-2 bg-gradient-to-t from-[#0a0a0a] to-transparent">
      <div className="relative bg-[#151515]/80 backdrop-blur-xl border border-black/10 dark:border-white/10 shadow-2xl rounded-2xl flex items-end p-2 focus-within:border-black/30 dark:border-white/30 focus-within:ring-1 focus-within:ring-black/30 dark:ring-white/30 transition-all overflow-hidden group">
        <button className="p-2 text-gray-500 dark:text-gray-500 hover:text-[#1b1b1b] dark:hover:text-white transition-colors flex-shrink-0 mb-0.5" title="Đính kèm file">
          <Paperclip className="w-5 h-5" />
        </button>
        <textarea 
          value={inputValue}
          onChange={(e) => setInputValue(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
              e.preventDefault();
              handleSendMessage();
            }
          }}
          className="flex-1 max-h-32 bg-transparent border-none focus:ring-0 resize-none py-2.5 px-2 text-sm text-[#1b1b1b] dark:text-white placeholder:text-gray-500 dark:text-gray-500 outline-none" 
          placeholder="Nhập câu hỏi về nhân sự..." 
          rows={1} 
          style={{ minHeight: '40px' }}
        />
        <button 
          onClick={handleSendMessage}
          disabled={!inputValue.trim()}
          className="p-2 m-0.5 bg-[#ea0029] text-white rounded-xl hover:bg-[#d40026] disabled:opacity-50 disabled:hover:opacity-50 transition-colors flex-shrink-0 shadow-lg shadow-[#ea0029]/30" 
          title="Gửi"
        >
          <Send className="w-4 h-4" />
        </button>
      </div>
      <div className="text-center mt-3 text-[10px] font-bold text-gray-500 dark:text-gray-500 uppercase tracking-widest">
        AI có thể mắc lỗi. Vui lòng kiểm tra lại thông tin quan trọng.
      </div>
    </div>
  );
}
