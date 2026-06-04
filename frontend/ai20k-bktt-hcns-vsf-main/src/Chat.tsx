import { useState, useRef, useEffect, ReactNode } from 'react';
import { FileEdit, BarChart2 } from 'lucide-react';
import { AnimatePresence } from 'motion/react';

import { Message, Citation } from './types';
import { ChatInput } from './components/chat/ChatInput';
import { SourcePanel } from './components/chat/SourcePanel';
import { MessageItem } from './components/chat/MessageItem';

const MOCK_MESSAGES: Message[] = [
  {
    id: 'm1',
    role: 'user',
    content: 'Năm nay tôi còn bao nhiêu ngày phép, và xin nghỉ 5 ngày tháng sau thế nào?',
    timestamp: '09:41 AM'
  },
  {
    id: 'm2',
    role: 'agent',
    timestamp: '09:41 AM',
    content: (
      <>
        Bạn còn <strong className="font-bold text-vinfast-red text-base">8 ngày phép năm</strong> trong tổng số 12 ngày (2026). Đã dùng 4 ngày. 
        <br/><br/>
        Để xin nghỉ 5 ngày tháng sau, bạn có thể tạo đơn nghỉ phép trực tiếp trên hệ thống. Trưởng bộ phận sẽ nhận được thông báo để duyệt. Phép không dùng hết được chuyển tối đa 5 ngày sang Q1 năm sau.
      </>
    ),
    citations: [
      { id: 'c1', title: 'Chính sách nghỉ phép 2026 - Mục 2.1', type: 'document' },
      { id: 'c2', title: 'Số dư phép cá nhân (HRIS) - Realtime', type: 'data' }
    ],
    actions: [
      { id: 'a1', label: 'Nộp đơn nghỉ phép', icon: FileEdit, primary: true },
      { id: 'a2', label: 'Xem bảng công', icon: BarChart2 }
    ]
  }
];

export default function Chat() {
  const [messages, setMessages] = useState<Message[]>(MOCK_MESSAGES);
  const [inputValue, setInputValue] = useState('');
  const [isPanelOpen, setIsPanelOpen] = useState(false);
  const [activeCitation, setActiveCitation] = useState<Citation | null>(null);
  const [copiedId, setCopiedId] = useState<string | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleSendMessage = () => {
    if (!inputValue.trim()) return;

    const now = new Date();
    const timeString = now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

    const newMessage: Message = {
      id: Date.now().toString(),
      role: 'user',
      content: inputValue,
      timestamp: timeString,
    };

    setMessages([...messages, newMessage]);
    setInputValue('');

    // Simulate agent response
    setTimeout(() => {
      const loadingId = (Date.now() + 1).toString();
      const responseMessage: Message = {
        id: loadingId,
        role: 'agent',
        content: 'Thiết lập kết nối với hệ thống HRIS...',
        timestamp: timeString,
      };
      setMessages(prev => [...prev, responseMessage]);

      setTimeout(() => {
        const finalResponse: Message = {
          id: (Date.now() + 2).toString(),
          role: 'agent',
          content: 'Dựa theo chính sách nhân sự hiện hành, quy trình xử lý yêu cầu của bạn sẽ được giải quyết qua hệ thống HRIS nội bộ. Khi tạo đơn, hệ thống sẽ tự động gởi email thông báo đến Trưởng phòng ban. Thời gian tối đa để duyệt đơn là 24 giờ làm việc. Bạn có muốn tôi hướng dẫn chi tiết từng bước nộp đơn không?',
          timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        };
        setMessages(prev => [...prev.filter(m => m.id !== loadingId), finalResponse]);
      }, 2500);
    }, 500);
  };

  const handleCitationClick = (citation: Citation) => {
    setActiveCitation(citation);
    setIsPanelOpen(true);
  };

  const handleFeedbackClick = (messageId: string, type: 'like' | 'dislike') => {
    setMessages(prev => prev.map(m => m.id === messageId ? { ...m, feedback: type, showFeedbackInput: type === 'dislike' } : m));
  };
  
  const handleReportClick = (messageId: string) => {
    setMessages(prev => prev.map(m => m.id === messageId ? { ...m, showFeedbackInput: true } : m));
  };

  const submitFeedback = (messageId: string) => {
    setMessages(prev => prev.map(m => m.id === messageId ? { ...m, showFeedbackInput: false, reported: true } : m));
  };

  const setFeedbackText = (messageId: string, text: string) => {
    setMessages(prev => prev.map(m => m.id === messageId ? { ...m, feedbackText: text } : m));
  };

  const handleCopy = (messageId: string, content: string | ReactNode) => {
    const textToCopy = typeof content === 'string' ? content : 'Nội dung đã được sao chép';
    navigator.clipboard.writeText(textToCopy).catch(() => {});
    setCopiedId(messageId);
    setTimeout(() => setCopiedId(null), 2000);
  };

  return (
    <>
      <main className="flex-1 flex flex-col relative overflow-hidden bg-transparent">
        {/* Messages Scroll Area */}
        <div className="w-full flex-1 overflow-y-auto px-4 md:px-12 lg:px-16 xl:px-24 flex flex-col gap-6 pt-8 pb-4 scroll-smooth">
          {messages.map((msg) => (
            <MessageItem
              key={msg.id}
              msg={msg}
              handleCitationClick={handleCitationClick}
              handleFeedbackClick={handleFeedbackClick}
              handleReportClick={handleReportClick}
              handleCopy={handleCopy}
              submitFeedback={submitFeedback}
              setFeedbackText={setFeedbackText}
              copiedId={copiedId}
              scrollToBottom={scrollToBottom}
            />
          ))}
          <div ref={messagesEndRef} />
        </div>
        
        <ChatInput 
          inputValue={inputValue}
          setInputValue={setInputValue}
          handleSendMessage={handleSendMessage}
        />
      </main>

      <AnimatePresence>
        {isPanelOpen && (
          <SourcePanel 
            activeCitation={activeCitation}
            setIsPanelOpen={setIsPanelOpen}
          />
        )}
      </AnimatePresence>
    </>
  );
}
