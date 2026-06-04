import { KeyRound, Mail, Lock, EyeOff, ShieldCheck, Moon, Sun } from 'lucide-react';
import { useTheme } from './ThemeProvider';

export default function Login({ onLogin }: { onLogin: () => void }) {
  const { theme, toggleTheme } = useTheme();

  return (
    <div className="flex w-full min-h-screen relative text-[#1b1b1b] dark:text-white">
      <div className="mesh-bg pointer-events-none"></div>

      {/* Left Column: Login Form */}
      <div className="w-full lg:w-5/12 xl:w-[480px] flex flex-col justify-center px-6 md:px-16 py-12 relative z-10 bg-white/[0.03] backdrop-blur-[16px] border-r border-black/10 dark:border-white/10 overflow-y-auto">
        
        <div className="flex-1 flex flex-col justify-center max-w-[380px] mx-auto w-full my-auto">
          {/* Brand Header */}
          <div className="mb-10 flex items-center justify-between">
            <div className="flex items-center gap-4">
              <div className="w-11 h-11 rounded-xl bg-gradient-to-tr from-[#ea0029] to-[#a3001c] flex items-center justify-center shadow-lg shadow-[#ea0029]/20 shrink-0">
                <span className="text-white font-bold text-lg">VF</span>
              </div>
              <img
                alt="Vinsmart Future"
                className="h-9 w-auto object-contain brightness-0 dark:invert opacity-90"
                src="https://lh3.googleusercontent.com/aida-public/AB6AXuDzi-N9RnqP52swXsaOrd2HWG3cgNEFmjFiHBAEbuFnNqcAR7LhBTtwRcref_yQaxHdAs-qfII-AdXxIQQyZiZlRLUINfH9tLWJgAw-rmen7cQpWbyb3ofyB5c9IuE7JDQl5RqFMEAlHrN0fXYOyef0cH4SYRDSkeCQb3pLKgkZ4FkYGsZn1mjwYnWHhaShdt7msL6SWjQkb-dcdsh1VSUs4tuU5sw6HN5qTMlPkerEL0Yl5HywTRkZq-GkO-T0kYvb-ndfFz24EmPF"
              />
            </div>
            
            <button
              onClick={toggleTheme}
              className="transition-colors p-2 rounded-full text-gray-600 dark:text-gray-400 hover:text-[#1b1b1b] dark:hover:text-white hover:bg-black/10 dark:hover:bg-white/10 hover:scale-110 active:scale-95"
              title="Toggle theme"
            >
              {theme === 'dark' ? <Sun className="w-5 h-5" /> : <Moon className="w-5 h-5" />}
            </button>
          </div>

          <h1 className="text-[32px] md:text-[36px] font-bold text-[#1b1b1b] dark:text-white mb-2 leading-tight">
            Sign in to your account
          </h1>
          <p className="text-sm text-gray-600 dark:text-gray-400 font-normal mb-8">
            Secure access to enterprise policies, benefits, and support.
          </p>

          {/* SSO Action */}
          <button 
            type="button" 
            onClick={onLogin}
            className="w-full flex items-center justify-center gap-3 bg-black/5 dark:bg-white/5 text-[#1b1b1b] dark:text-white font-medium text-sm py-3 px-4 rounded-xl hover:bg-black/10 dark:bg-white/10 transition-all duration-200 border border-black/10 dark:border-white/10 focus:outline-none focus:ring-1 focus:ring-black/30 dark:ring-white/30"
          >
            <KeyRound className="w-[18px] h-[18px] text-gray-600 dark:text-gray-400 opacity-80" />
            Sign in with SSO
          </button>

          {/* Divider */}
          <div className="relative flex items-center py-8">
            <div className="flex-grow border-t border-black/10 dark:border-white/10"></div>
            <span className="flex-shrink-0 mx-4 text-[10px] font-bold uppercase tracking-widest text-gray-500 dark:text-gray-500">
              or continue with email
            </span>
            <div className="flex-grow border-t border-black/10 dark:border-white/10"></div>
          </div>

          {/* Credentials Form */}
          <form className="space-y-5" onSubmit={(e) => { e.preventDefault(); onLogin(); }}>
            
            {/* Email Input */}
            <div className="space-y-2 group">
              <label 
                htmlFor="email"
                className="text-[10px] font-bold uppercase tracking-widest text-gray-600 dark:text-gray-400 group-focus-within:text-[#1b1b1b] dark:group-focus-within:text-white transition-colors"
              >
                Corporate Email
              </label>
              <div className="relative flex items-center bg-black/5 dark:bg-white/5 border border-black/10 dark:border-white/10 rounded-xl transition-all focus-within:ring-1 focus-within:ring-black/20 dark:ring-white/20 focus-within:border-black/20 dark:border-white/20">
                <Mail className="w-5 h-5 absolute left-3.5 text-gray-500 dark:text-gray-500 group-focus-within:text-[#1b1b1b] dark:group-focus-within:text-white transition-colors opacity-70" />
                <input
                  id="email"
                  type="email"
                  placeholder="employee@vinfast.com"
                  className="w-full py-2.5 pl-11 pr-4 bg-transparent outline-none placeholder:text-gray-500 dark:text-gray-500 text-[#1b1b1b] dark:text-white text-sm focus:ring-0"
                />
              </div>
            </div>

            {/* Password Input */}
            <div className="space-y-2 group">
              <label 
                htmlFor="password"
                className="text-[10px] font-bold uppercase tracking-widest text-gray-600 dark:text-gray-400 group-focus-within:text-[#1b1b1b] dark:group-focus-within:text-white transition-colors"
              >
                Password
              </label>
              <div className="relative flex items-center bg-black/5 dark:bg-white/5 border border-black/10 dark:border-white/10 rounded-xl transition-all focus-within:ring-1 focus-within:ring-black/20 dark:ring-white/20 focus-within:border-black/20 dark:border-white/20">
                <Lock className="w-5 h-5 absolute left-3.5 text-gray-500 dark:text-gray-500 group-focus-within:text-[#1b1b1b] dark:group-focus-within:text-white transition-colors opacity-70" />
                <input
                  id="password"
                  type="password"
                  placeholder="••••••••"
                  className="w-full py-2.5 pl-11 pr-11 bg-transparent outline-none placeholder:text-gray-500 dark:text-gray-500 text-[#1b1b1b] dark:text-white text-sm tracking-widest focus:ring-0"
                />
                <button
                  type="button"
                  className="absolute right-3 text-gray-500 dark:text-gray-500 hover:text-[#1b1b1b] dark:hover:text-white transition-colors focus:outline-none opacity-80"
                  aria-label="Toggle password visibility"
                >
                  <EyeOff className="w-4 h-4" />
                </button>
              </div>
            </div>

            {/* Utilities */}
            <div className="flex items-center justify-between pt-1 pb-4">
              <label className="flex items-center gap-2.5 cursor-pointer group">
                <input
                  type="checkbox"
                  className="w-4 h-4 rounded-[4px] border border-black/20 dark:border-white/20 text-[#ea0029] focus:ring-[#ea0029]/30 bg-black/5 dark:bg-white/5 cursor-pointer accent-[#ea0029] focus:ring-1 focus:outline-none"
                />
                <span className="text-xs font-medium text-gray-600 dark:text-gray-400 group-hover:text-[#1b1b1b] dark:hover:text-white transition-colors">
                  Remember me
                </span>
              </label>
              <a href="#" className="text-xs font-bold text-[#ea0029] hover:text-[#ff4d6d] hover:underline transition-colors tracking-wide">
                Forgot password?
              </a>
            </div>

            {/* Submit */}
            <button
              type="submit"
              className="w-full bg-[#ea0029] text-white font-bold text-sm py-3 px-4 rounded-xl shadow-lg shadow-[#ea0029]/40 hover:bg-[#d40026] active:scale-[0.98] transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-[#ea0029] focus:ring-offset-2 focus:ring-offset-transparent"
            >
              Sign In
            </button>
          </form>
        </div>

        {/* Footer Links */}
        <div className="w-full pt-8 pb-4 text-center">
          <p className="text-[11px] font-medium tracking-wide text-gray-500 dark:text-gray-500">
            Need help?{' '}
            <a href="#" className="text-gray-700 dark:text-gray-300 hover:text-[#1b1b1b] dark:hover:text-white hover:underline transition-colors font-bold">
              Contact IT Support
            </a>
          </p>
        </div>
      </div>

      {/* Right Column: Hero Image Container */}
      <div className="hidden lg:block lg:flex-1 relative overflow-hidden bg-transparent pointer-events-none">
        
        {/* Blended Background Image */}
        <div 
          className="absolute inset-0 w-full h-full bg-cover bg-center bg-no-repeat opacity-40 mix-blend-screen"
          style={{ 
            backgroundImage: "url('https://lh3.googleusercontent.com/aida-public/AB6AXuBTCzjScDsNAtv47jhQTvVVPxVcfIY3GpUj1DyoTQvS_8_tG2spHfpJhzlM-wUl7xzFeCeOWsyhlf904EWA_ndubGvEqfJpsdO2thuz8zHXINXUfjoNjsKkaL6Uy9YozLaE6kuhOU6LVNWfFQg37COVmGhUkk_MV7HOH_oRcac6hZ6ABb97xOgZr9VvgHpKDZUtOxB-0an7t1iCbo7YQc2WTB2BGPuK7gxxtWnCG-xysFLHk4AhigHCGB85vBIB0guoqd6UicTho4WJ')"
          }}
        >
        </div>
        
        {/* Soft atmospheric gradients */}
        <div className="absolute inset-0 bg-gradient-to-r from-[#f9f9f9] dark:from-[#0a0a0a] via-transparent to-transparent z-10 pointer-events-none opacity-80"></div>
        <div className="absolute inset-0 bg-gradient-to-t from-[#f9f9f9]/90 dark:from-[#0a0a0a]/90 via-transparent to-[#f9f9f9]/20 dark:to-[#0a0a0a]/20 z-10 pointer-events-none"></div>

        {/* Floating Security Module Component */}
        <div className="absolute bottom-12 right-12 z-20 max-w-sm w-full pointer-events-auto">
          <div className="glass-card p-5 group hover:border-black/30 dark:border-white/30 transition-all duration-300 shadow-xl shadow-black/20">
            <div className="flex items-start gap-4">
              <div className="w-10 h-10 rounded-lg bg-[#ea0029]/20 flex flex-shrink-0 items-center justify-center border border-[#ea0029]/30 group-hover:bg-[#ea0029]/30 transition-colors">
                <ShieldCheck className="w-5 h-5 text-[#ffb3ae]" />
              </div>
              <div>
                <h3 className="text-sm font-bold text-[#1b1b1b] dark:text-white mb-1.5 tracking-tight">
                  Enterprise Security
                </h3>
                <p className="text-[11px] font-normal leading-relaxed text-gray-600 dark:text-gray-400">
                  This portal is restricted to authorized VinFast personnel. All activities are monitored and logged to ensure data integrity.
                </p>
              </div>
            </div>
          </div>
        </div>
        
      </div>
    </div>
  );
}
