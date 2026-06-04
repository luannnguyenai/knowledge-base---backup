import { ReactNode } from 'react';
import { ShieldCheck, CheckCircle2, Clock, Bot, Book, FileText, Database, ChevronRight, ThumbsUp, ThumbsDown, Copy, Flag } from 'lucide-react';
import { Message, Citation } from '../../types';
import { TypewriterText } from '../ui/TypewriterText';

interface MessageItemProps {
  key?: string | number;
  msg: Message;
  handleCitationClick: (citation: Citation) => void;
  handleFeedbackClick: (messageId: string, type: 'like' | 'dislike') => void;
  handleReportClick: (messageId: string) => void;
  handleCopy: (messageId: string, content: string | ReactNode) => void;
  submitFeedback: (messageId: string) => void;
  setFeedbackText: (messageId: string, text: string) => void;
  copiedId: string | null;
  scrollToBottom: () => void;
}

export function MessageItem({
  msg,
  handleCitationClick,
  handleFeedbackClick,
  handleReportClick,
  handleCopy,
  submitFeedback,
  setFeedbackText,
  copiedId,
  scrollToBottom
}: MessageItemProps) {
  if (msg.role === 'user') {
    return (
      <div className="flex justify-end w-full">
        <div className="flex flex-col items-end gap-1.5 max-w-[85%]">
          <div className="bg-black/10 dark:bg-white/10 backdrop-blur-md text-[#1b1b1b] dark:text-white rounded-2xl rounded-tr-sm px-5 py-3.5 border border-black/10 dark:border-white/10 shadow-sm whitespace-pre-wrap">
            <p className="text-sm md:text-base font-medium leading-relaxed">
              {msg.content}
            </p>
          </div>
          {msg.timestamp && (
            <span className="text-[10px] text-gray-600 dark:text-gray-400 font-bold px-1 uppercase tracking-wider">
              {msg.timestamp}
            </span>
          )}
        </div>
      </div>
    );
  }

  return (
    <div className="flex justify-start w-full">
      <div className="w-8 h-8 rounded-full bg-black/10 dark:bg-white/10 backdrop-blur-md flex-shrink-0 flex items-center justify-center text-[#ea0029] shadow-sm mt-1 mr-3 border border-black/10 dark:border-white/10">
        <Bot className="w-4 h-4" />
      </div>
      
      <div className="flex flex-col items-start gap-1.5 max-w-[95%] md:max-w-[85%] w-full">
        <div className="w-full bg-white/[0.04] backdrop-blur-xl border border-black/10 dark:border-white/10 shadow-sm rounded-2xl rounded-tl-sm overflow-hidden flex flex-col relative group">
          <div className="px-5 py-3 border-b border-black/10 dark:border-white/10 flex items-center justify-between bg-white/[0.02]">
            <div className="flex items-center gap-3">
              <span className="bg-[#ea0029]/10 border border-[#ea0029]/20 text-[#ea0029] text-[10px] font-bold px-2.5 py-1 rounded-full flex items-center gap-1.5 uppercase tracking-wider">
                <ShieldCheck className="w-3.5 h-3.5" />
                HR Agent
              </span>
              <div className="w-1 h-1 rounded-full bg-outline hidden sm:block"></div>
              <span className="hidden sm:flex text-[10px] text-emerald-400 font-bold items-center gap-1 bg-emerald-400/10 px-2 py-0.5 rounded border border-emerald-400/20 uppercase tracking-wider">
                <CheckCircle2 className="w-3.5 h-3.5" />
                Độ tin: Cao
              </span>
            </div>
            <div className="flex items-center gap-1.5 text-gray-600 dark:text-gray-400 text-[10px] font-bold uppercase tracking-wider">
              <Clock className="w-3.5 h-3.5" />
              Hiệu lực 2026
            </div>
          </div>
        
          <div className="px-5 py-4">
            <div className="text-sm md:text-base text-[#1b1b1b] dark:text-white leading-relaxed font-normal whitespace-pre-wrap">
              {typeof msg.content === 'string' ? (
                <TypewriterText content={msg.content} onTyping={scrollToBottom} />
              ) : (
                msg.content
              )}
            </div>
          </div>
          
          {msg.citations && msg.citations.length > 0 && (
            <div className="px-5 pb-4">
              <h4 className="text-[10px] font-bold text-gray-600 dark:text-gray-400 uppercase mb-2 flex items-center gap-1.5 tracking-widest">
                <Book className="w-4 h-4" /> Nguồn trích dẫn
              </h4>
              <div className="flex flex-col gap-2">
                {msg.citations.map(citation => (
                  <button 
                    key={citation.id}
                    onClick={() => handleCitationClick(citation)}
                    className="flex items-center justify-between p-2.5 bg-black/5 dark:bg-white/5 rounded-xl border border-black/10 dark:border-white/10 hover:border-black/30 dark:border-white/30 hover:bg-black/20 transition-all text-left w-full group/cite"
                  >
                    <div className="flex items-center gap-3 overflow-hidden">
                      {citation.type === 'document' ? (
                        <FileText className="text-[#ea0029] w-4 h-4 flex-shrink-0" />
                      ) : (
                        <Database className="text-gray-600 dark:text-gray-400 w-4 h-4 flex-shrink-0" />
                      )}
                      <span className="text-xs text-[#1b1b1b] dark:text-white truncate font-semibold">{citation.title}</span>
                    </div>
                    {citation.type === 'document' && (
                      <ChevronRight className="w-4 h-4 text-gray-600 dark:text-gray-400 group-hover/cite:text-[#ea0029] transition-colors flex-shrink-0" />
                    )}
                  </button>
                ))}
              </div>
            </div>
          )}
          
          {(msg.actions || msg.citations) && <div className="h-px bg-outline-variant mx-5"></div>}
          
          {msg.actions && msg.actions.length > 0 && (
            <div className="px-5 py-4 flex flex-wrap items-center gap-3">
              {msg.actions.map(action => {
                const Icon = action.icon;
                return (
                  <button 
                    key={action.id}
                    className={`${
                      action.primary 
                        ? 'bg-[#ea0029] hover:opacity-90 text-white border-transparent shadow-sm' 
                        : 'bg-transparent border-[#ea0029]/80 text-[#1b1b1b] dark:text-white hover:bg-black/5 dark:hover:bg-white/5'
                    } border font-bold text-xs px-4 py-2 rounded-xl transition-all active:scale-95 flex items-center gap-2`}
                  >
                    <Icon className="w-4 h-4" />
                    {action.label}
                  </button>
                );
              })}
            </div>
          )}
          
          <div className="px-5 py-2.5 bg-white/[0.02] border-t border-black/10 dark:border-white/10 flex items-center justify-between">
            <div className="flex items-center gap-1">
              <span className="text-[10px] uppercase tracking-wider text-gray-600 dark:text-gray-400 font-bold mr-2">Hữu ích?</span>
              <button 
                onClick={() => handleFeedbackClick(msg.id, 'like')}
                className={`p-1.5 rounded-lg transition-colors ${msg.feedback === 'like' ? 'text-[#ea0029] bg-[#ea0029]/10' : 'text-gray-600 dark:text-gray-400 hover:text-[#1b1b1b] dark:hover:text-white hover:bg-black/5 dark:hover:bg-white/5'}`}
              >
                <ThumbsUp className="w-4 h-4" />
              </button>
              <button 
                onClick={() => handleFeedbackClick(msg.id, 'dislike')}
                className={`p-1.5 rounded-lg transition-colors ${msg.feedback === 'dislike' ? 'text-[#ea0029] bg-[#ea0029]/10' : 'text-gray-600 dark:text-gray-400 hover:text-[#1b1b1b] dark:hover:text-white hover:bg-black/5 dark:hover:bg-white/5'}`}
              >
                <ThumbsDown className="w-4 h-4" />
              </button>
            </div>
            <div className="flex items-center gap-1">
              <button 
                onClick={() => handleCopy(msg.id, msg.content)}
                className={`p-1.5 rounded-lg transition-colors flex items-center gap-1.5 text-[10px] font-bold uppercase tracking-wider ${copiedId === msg.id ? 'text-emerald-400 bg-emerald-400/10' : 'text-gray-600 dark:text-gray-400 hover:text-[#1b1b1b] dark:hover:text-white hover:bg-black/5 dark:hover:bg-white/5'}`}
              >
                {copiedId === msg.id ? <CheckCircle2 className="w-4 h-4" /> : <Copy className="w-4 h-4" />} 
                <span className="hidden sm:inline">{copiedId === msg.id ? 'Đã chép' : 'Sao chép'}</span>
              </button>
              <button 
                onClick={() => handleReportClick(msg.id)}
                className={`p-1.5 rounded-lg transition-colors flex items-center gap-1.5 text-[10px] font-bold uppercase tracking-wider ${msg.reported ? 'text-[#ea0029]' : 'text-gray-600 dark:text-gray-400 hover:text-[#ea0029] hover:bg-black/5 dark:hover:bg-white/5'}`}
              >
                <Flag className="w-4 h-4" /> <span className="hidden sm:inline">{msg.reported ? 'Đã báo' : 'Báo sai'}</span>
              </button>
            </div>
          </div>
          
          {msg.showFeedbackInput && (
            <div className="px-5 py-3 bg-black/20 border-t border-black/10 dark:border-white/10 flex flex-col gap-2 transition-all">
              <span className="text-[11px] text-gray-600 dark:text-gray-400 font-bold tracking-wide">Cho chúng tôi biết thêm chi tiết để cải thiện:</span>
              <div className="flex gap-2">
                <input 
                  type="text" 
                  className="flex-1 bg-white/[0.04] backdrop-blur-xl border border-black/10 dark:border-white/10 rounded-lg px-3 py-1.5 text-xs text-[#1b1b1b] dark:text-white placeholder:text-gray-600 dark:text-gray-400 focus:outline-none focus:border-black/30 dark:border-white/30 focus:ring-1 focus:ring-black/30 dark:ring-white/30"
                  placeholder="Phản hồi của bạn..."
                  autoFocus
                  onChange={(e) => setFeedbackText(msg.id, e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter') submitFeedback(msg.id);
                  }}
                  value={msg.feedbackText || ''}
                />
                <button 
                  onClick={() => submitFeedback(msg.id)}
                  className="bg-gray-100 dark:bg-[#1a1a1a] text-[#1b1b1b] dark:text-white px-3 py-1.5 rounded-lg text-[11px] font-bold uppercase tracking-wider hover:opacity-90 transition-opacity"
                >
                  Gửi
                </button>
              </div>
            </div>
          )}
        </div>
        {msg.timestamp && (
          <span className="text-[10px] text-gray-600 dark:text-gray-400 font-bold px-1 uppercase tracking-wider mb-1">
            {msg.timestamp}
          </span>
        )}
      </div>
    </div>
  );
}
