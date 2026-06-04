import { Sparkles, Rocket, AlertTriangle, XCircle, X, CheckCircle2, Check, LayoutGrid, Shield, Scale, TrendingUp } from 'lucide-react';

export default function Overview() {
  return (
    <div className="flex-1 overflow-y-auto p-4 md:p-6 lg:p-16 bg-transparent text-[#1b1b1b] dark:text-white">
      <div className="max-w-[1000px] mx-auto space-y-12 pb-12">
        {/* Hero Section */}
        <section className="relative rounded-xl overflow-hidden glass-card border border-black/10 dark:border-white/10 shadow-[0_4px_20px_rgba(0,0,0,0.05)] p-8 md:p-12 flex flex-col md:flex-row items-center justify-between border-l-4 border-l-[#ea0029] bg-gradient-to-br from-white to-surface-container-low">
          <div className="md:w-2/3 space-y-4 relative z-10">
            <div className="inline-flex items-center px-3 py-1 rounded-full bg-black/20-high text-[#1b1b1b] dark:text-white text-xs font-bold mb-2">
              <Sparkles className="w-4 h-4 mr-1 text-[#1b1b1b] dark:text-white" />
              AI-Powered
            </div>
            <h1 className="text-4xl md:text-5xl font-bold text-[#1b1b1b] dark:text-white leading-tight">HR Knowledge Base Assistant</h1>
            <p className="text-xl md:text-2xl text-[#ea0029] font-semibold">Trợ lý nhân sự nội bộ thông minh</p>
            <p className="text-lg text-gray-700 dark:text-gray-300 max-w-xl mt-4">
                Giải pháp AI tạo sinh (GenAI) chuyên biệt dành cho hệ thống nội bộ, giúp giải đáp nhanh chóng và chính xác các chính sách, quy định, phúc lợi và thủ tục nhân sự.
            </p>
            <div className="pt-4 flex flex-col sm:flex-row space-y-3 sm:space-y-0 sm:space-x-4">
              <button className="bg-[#ea0029] text-white px-8 py-3 rounded-lg font-bold flex items-center justify-center hover:opacity-90 transition-opacity shadow-md">
                <Rocket className="w-5 h-5 mr-2" /> Khám phá ngay
              </button>
              <button className="bg-transparent border-2 border-vinfast-red text-[#ea0029] px-8 py-3 rounded-lg font-bold hover:bg-black/10 dark:bg-white/10 backdrop-blur-md/5 transition-colors flex items-center justify-center">
                Xem tài liệu
              </button>
            </div>
          </div>
          <div className="hidden md:block w-1/3 pl-8 relative z-10">
            <div className="w-48 h-48 mx-auto rounded-full bg-gradient-to-tr from-vinfast-red to-orange-500 opacity-10 blur-2xl absolute right-10 top-10"></div>
            <img 
              alt="Corporate office concept" 
              className="relative z-10 rounded-xl shadow-lg border border-black/10 dark:border-white/10 object-cover h-64 w-full" 
              src="https://images.unsplash.com/photo-1497215728101-856f4ea42174?auto=format&fit=crop&q=80&w=600" 
            />
          </div>
        </section>

        {/* Problems & Solutions */}
        <section>
          <h2 className="text-2xl md:text-3xl font-bold text-[#1b1b1b] dark:text-white mb-8 flex items-center">
            <AlertTriangle className="w-8 h-8 mr-3 text-[#ea0029]" />
            Thách thức & Giải pháp
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
            {/* Pain points */}
            <div className="bg-black/10 dark:bg-white/10 backdrop-blur-md rounded-xl p-8 shadow-sm border border-black/10 dark:border-white/10">
              <h3 className="text-xl font-bold text-[#ea0029] mb-6 flex items-center border-b border-black/10 dark:border-white/10 pb-4">
                <XCircle className="w-6 h-6 mr-2" />
                Nỗi đau của nhân viên & HR
              </h3>
              <ul className="space-y-4 text-gray-700 dark:text-gray-300">
                <li className="flex items-start">
                  <X className="w-5 h-5 text-[#ea0029] mr-3 mt-0.5 shrink-0" />
                  <span className="text-[#1b1b1b] dark:text-white">Mất nhiều thời gian tìm kiếm thông tin trong các tài liệu dài hàng chục trang.</span>
                </li>
                <li className="flex items-start">
                  <X className="w-5 h-5 text-[#ea0029] mr-3 mt-0.5 shrink-0" />
                  <span className="text-[#1b1b1b] dark:text-white">Khó hiểu các thuật ngữ pháp lý và quy định phức tạp.</span>
                </li>
                <li className="flex items-start">
                  <X className="w-5 h-5 text-[#ea0029] mr-3 mt-0.5 shrink-0" />
                  <span className="text-[#1b1b1b] dark:text-white">Bộ phận HR quá tải với các câu hỏi lặp đi lặp lại hàng ngày.</span>
                </li>
                <li className="flex items-start">
                  <X className="w-5 h-5 text-[#ea0029] mr-3 mt-0.5 shrink-0" />
                  <span className="text-[#1b1b1b] dark:text-white">Thông tin đôi khi thiếu tính nhất quán khi tư vấn thủ công.</span>
                </li>
              </ul>
            </div>

            {/* Solutions */}
            <div className="bg-black/10 dark:bg-white/10 backdrop-blur-md rounded-xl p-8 shadow-sm border border-black/10 dark:border-white/10 relative overflow-hidden">
              <div className="absolute -right-6 -top-6 w-24 h-24 bg-emerald-400 opacity-5 rounded-full"></div>
              <h3 className="text-xl font-bold text-emerald-400 mb-6 flex items-center border-b border-black/10 dark:border-white/10 pb-4">
                <CheckCircle2 className="w-6 h-6 mr-2" />
                Giải pháp của HR Assistant
              </h3>
              <ul className="space-y-4 text-gray-700 dark:text-gray-300 relative z-10">
                <li className="flex items-start">
                  <Check className="w-5 h-5 text-emerald-400 mr-3 mt-0.5 shrink-0" />
                  <span className="text-[#1b1b1b] dark:text-white">Truy xuất câu trả lời chính xác, trích dẫn nguồn rõ ràng trong vài giây.</span>
                </li>
                <li className="flex items-start">
                  <Check className="w-5 h-5 text-emerald-400 mr-3 mt-0.5 shrink-0" />
                  <span className="text-[#1b1b1b] dark:text-white">Giải thích các chính sách phức tạp bằng ngôn ngữ tự nhiên, dễ hiểu.</span>
                </li>
                <li className="flex items-start">
                  <Check className="w-5 h-5 text-emerald-400 mr-3 mt-0.5 shrink-0" />
                  <span className="text-[#1b1b1b] dark:text-white">Tự động hóa hỗ trợ 24/7, giải phóng thời gian cho đội ngũ HR.</span>
                </li>
                <li className="flex items-start">
                  <Check className="w-5 h-5 text-emerald-400 mr-3 mt-0.5 shrink-0" />
                  <span className="text-[#1b1b1b] dark:text-white">Đảm bảo tính nhất quán dựa trên cơ sở tri thức nội bộ được phê duyệt.</span>
                </li>
              </ul>
            </div>
          </div>
        </section>

        {/* HR Domain Scope */}
        <section>
          <h2 className="text-2xl md:text-3xl font-bold text-[#1b1b1b] dark:text-white mb-8 flex items-center">
            <LayoutGrid className="w-8 h-8 mr-3 text-[#ea0029]" />
            Phạm vi hỗ trợ chuyên môn
          </h2>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
            <div className="bg-black/10 dark:bg-white/10 backdrop-blur-md rounded-xl p-6 border border-black/10 dark:border-white/10 shadow-sm hover:shadow-md transition-all group cursor-pointer hover:border-vinfast-red hover:-translate-y-1">
              <div className="w-12 h-12 bg-black/10 dark:bg-white/10 backdrop-blur-md/5 rounded-lg flex items-center justify-center mb-5 group-hover:bg-primary-container transition-colors">
                <span className="text-[#ea0029] font-bold">01</span>
              </div>
              <h4 className="font-bold text-lg text-[#1b1b1b] dark:text-white mb-2">Nghỉ phép</h4>
              <p className="text-sm text-gray-700 dark:text-gray-300 leading-relaxed">Quy định phép năm, nghỉ ốm, thai sản, nghỉ không lương và quy trình xin nghỉ.</p>
            </div>

            <div className="bg-black/10 dark:bg-white/10 backdrop-blur-md rounded-xl p-6 border border-black/10 dark:border-white/10 shadow-sm hover:shadow-md transition-all group cursor-pointer hover:border-vinfast-red hover:-translate-y-1">
              <div className="w-12 h-12 bg-black/10 dark:bg-white/10 backdrop-blur-md/5 rounded-lg flex items-center justify-center mb-5 group-hover:bg-primary-container transition-colors">
                <span className="text-[#ea0029] font-bold">02</span>
              </div>
              <h4 className="font-bold text-lg text-[#1b1b1b] dark:text-white mb-2">Lương & Phúc lợi</h4>
              <p className="text-sm text-gray-700 dark:text-gray-300 leading-relaxed">Chính sách lương thưởng, bảo hiểm, khám sức khỏe, phụ cấp và các đãi ngộ khác.</p>
            </div>

            <div className="bg-black/10 dark:bg-white/10 backdrop-blur-md rounded-xl p-6 border border-black/10 dark:border-white/10 shadow-sm hover:shadow-md transition-all group cursor-pointer hover:border-vinfast-red hover:-translate-y-1">
              <div className="w-12 h-12 bg-black/10 dark:bg-white/10 backdrop-blur-md/5 rounded-lg flex items-center justify-center mb-5 group-hover:bg-primary-container transition-colors">
                <span className="text-[#ea0029] font-bold">03</span>
              </div>
              <h4 className="font-bold text-lg text-[#1b1b1b] dark:text-white mb-2">Thủ tục</h4>
              <p className="text-sm text-gray-700 dark:text-gray-300 leading-relaxed">Quy trình onboarding, offboarding, đánh giá hiệu suất, điều chuyển công tác.</p>
            </div>

            <div className="bg-black/10 dark:bg-white/10 backdrop-blur-md rounded-xl p-6 border border-black/10 dark:border-white/10 shadow-sm hover:shadow-md transition-all group cursor-pointer hover:border-vinfast-red hover:-translate-y-1">
              <div className="w-12 h-12 bg-black/10 dark:bg-white/10 backdrop-blur-md/5 rounded-lg flex items-center justify-center mb-5 group-hover:bg-primary-container transition-colors">
                <span className="text-[#ea0029] font-bold">04</span>
              </div>
              <h4 className="font-bold text-lg text-[#1b1b1b] dark:text-white mb-2">Quy chế</h4>
              <p className="text-sm text-gray-700 dark:text-gray-300 leading-relaxed">Nội quy lao động, quy tắc ứng xử, bảo mật thông tin và văn hóa doanh nghiệp.</p>
            </div>
          </div>
        </section>

        {/* Strategic Benefits */}
        <section className="bg-black/5 dark:bg-white/5 border border-black/10 dark:border-white/10 rounded-2xl p-8 md:p-12 text-[#1b1b1b] dark:text-white relative overflow-hidden">
          <div className="absolute top-0 right-0 opacity-5 pointer-events-none">
            <svg height="300" viewBox="0 0 200 200" width="300" xmlns="http://www.w3.org/2000/svg">
              <path d="M45.7,-76.3C58.8,-69.3,68.7,-55.5,77,-40.8C85.3,-26.1,91.9,-10.5,90.2,4.4C88.5,19.3,78.5,33.5,67.7,46.1C56.9,58.7,45.3,69.7,31.3,76.6C17.3,83.5,0.9,86.3,-14.8,83.9C-30.5,81.5,-45.5,73.9,-58.5,62.8C-71.5,51.7,-82.5,37.1,-87.3,20.8C-92.1,4.5,-90.7,-13.5,-83.4,-29.4C-76.1,-45.3,-62.9,-59.1,-48.1,-65.7C-33.3,-72.3,-16.7,-71.7,-0.4,-71C15.9,-70.3,32.6,-83.3,45.7,-76.3Z" fill="#FFFFFF" transform="translate(100 100) scale(1.1)"></path>
            </svg>
          </div>
          <h2 className="text-3xl font-bold mb-10 relative z-10 text-[#1b1b1b] dark:text-white">Lợi ích Chiến lược</h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-10 relative z-10">
            <div className="space-y-4">
              <div className="w-12 h-12 rounded-full bg-[#ea0029]/20 border border-[#ea0029]/30 flex items-center justify-center mb-2">
                <Shield className="w-6 h-6 text-[#ea0029]" />
              </div>
              <h4 className="text-xl font-bold text-[#1b1b1b] dark:text-white">Bảo mật Dữ liệu (PII)</h4>
              <p className="text-sm text-gray-600 dark:text-gray-400 leading-relaxed">
                Xử lý dữ liệu nghiêm ngặt trong môi trường mạng nội bộ, ẩn danh hóa thông tin cá nhân trước khi phân tích. Đảm bảo tuân thủ tiêu chuẩn bảo mật.
              </p>
            </div>
            <div className="space-y-4">
              <div className="w-12 h-12 rounded-full bg-[#ea0029]/20 border border-[#ea0029]/30 flex items-center justify-center mb-2">
                <Scale className="w-6 h-6 text-[#ea0029]" />
              </div>
              <h4 className="text-xl font-bold text-[#1b1b1b] dark:text-white">Tuân thủ Quy định</h4>
              <p className="text-sm text-gray-600 dark:text-gray-400 leading-relaxed">
                Câu trả lời luôn được giới hạn trong phạm vi tài liệu đã phê duyệt (Grounding). Tránh hiện tượng ảo giác (Hallucination) của AI.
              </p>
            </div>
            <div className="space-y-4">
              <div className="w-12 h-12 rounded-full bg-[#ea0029]/20 border border-[#ea0029]/30 flex items-center justify-center mb-2">
                <TrendingUp className="w-6 h-6 text-[#ea0029]" />
              </div>
              <h4 className="text-xl font-bold text-[#1b1b1b] dark:text-white">Tối ưu ROI</h4>
              <p className="text-sm text-gray-600 dark:text-gray-400 leading-relaxed">
                Cắt giảm 40% thời gian HR phải trả lời các câu hỏi cơ bản, tập trung nguồn lực vào các công việc chiến lược. Tăng cường trải nghiệm nhân viên.
              </p>
            </div>
          </div>
        </section>
      </div>
    </div>
  );
}
