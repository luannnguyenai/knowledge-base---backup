"use client";

import { Badge, Mail, Phone, Book, Users, Settings, CheckCircle2, XCircle, LogOut } from 'lucide-react';

interface ProfileProps {
  onLogout?: () => void;
}

export default function Profile({ onLogout }: ProfileProps) {
  return (
    <div className="flex-1 overflow-y-auto p-4 md:p-6 lg:p-12 text-[#1b1b1b] dark:text-white bg-transparent">
      <div className="max-w-[1100px] mx-auto w-full space-y-8 pb-12">
        {/* Header Section */}
        <div className="flex flex-col md:flex-row md:items-end justify-between gap-4">
          <div>
            <h2 className="text-3xl md:text-4xl font-bold tracking-tight text-[#1b1b1b] dark:text-white">User Profile</h2>
            <p className="text-gray-600 dark:text-gray-400 mt-2">Manage your account details and view access permissions.</p>
          </div>
          <div className="flex items-center gap-4 self-start md:self-auto">
            <button className="bg-transparent border border-black/20 dark:border-white/20 text-[#1b1b1b] dark:text-white px-6 py-2 rounded-lg font-bold hover:bg-black/10 dark:bg-white/10 transition-colors flex items-center justify-center">
              Edit Profile
            </button>
            {onLogout && (
              <button 
                onClick={onLogout}
                className="bg-[#ea0029] text-white px-6 py-2 rounded-lg font-bold hover:bg-[#c20022] transition-colors flex items-center justify-center gap-2"
              >
                <LogOut className="w-5 h-5" />
                Logout
              </button>
            )}
          </div>
        </div>

        {/* Profile Bento Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          
          {/* ID Card */}
          <div className="bg-black/5 dark:bg-white/5 backdrop-blur-md rounded-2xl p-8 border border-black/10 dark:border-white/10 shadow-sm relative overflow-hidden flex flex-col items-center text-center lg:col-span-1">
            <div className="absolute top-0 left-0 w-full h-1 bg-[#ea0029]"></div>
            
            <div className="w-24 h-24 rounded-full bg-black/10 dark:bg-white/10 mb-4 overflow-hidden border-2 border-black/20 dark:border-white/20 mt-2">
              <img 
                alt="Professional headshot" 
                className="w-full h-full object-cover" 
                src="https://images.unsplash.com/photo-1573496359142-b8d87734a5a2?auto=format&fit=crop&q=80&w=200&h=200" 
              />
            </div>
            
            <h3 className="text-xl font-bold text-[#1b1b1b] dark:text-white mb-1">Sarah Jenkins</h3>
            <p className="font-bold text-xs text-[#ea0029] mb-4 bg-[#ea0029]/10 px-3 py-1 rounded-md uppercase tracking-wider">EMP-84729</p>
            
            <div className="w-full border-t border-black/10 dark:border-white/10 pt-6 mt-2 space-y-4">
              <div className="flex justify-between items-center">
                <span className="text-gray-600 dark:text-gray-400 text-sm">Status</span>
                <span className="flex items-center gap-1.5 text-[#ea0029] font-bold text-xs uppercase tracking-wide">
                  <span className="w-2 h-2 rounded-full bg-[#ea0029]"></span> Active
                </span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-gray-600 dark:text-gray-400 text-sm">Joined</span>
                <span className="text-[#1b1b1b] dark:text-white font-medium text-sm">Mar 2021</span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-gray-600 dark:text-gray-400 text-sm">Location</span>
                <span className="text-[#1b1b1b] dark:text-white font-medium text-sm">Haiphong, VN</span>
              </div>
            </div>
          </div>

          {/* Role Details */}
          <div className="bg-black/5 dark:bg-white/5 backdrop-blur-md rounded-2xl p-8 border border-black/10 dark:border-white/10 shadow-sm lg:col-span-2">
            <h4 className="text-xl font-bold text-[#1b1b1b] dark:text-white mb-8 flex items-center gap-2">
              <Badge className="w-6 h-6 text-[#ea0029]" />
              Role Information
            </h4>
            
            <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
              <div>
                <label className="block font-bold text-xs text-gray-500 dark:text-gray-500 mb-2 uppercase tracking-wider">Department</label>
                <div className="text-lg text-[#1b1b1b] dark:text-white border-b border-black/10 dark:border-white/10 pb-3 font-medium">Software Engineering</div>
              </div>
              <div>
                <label className="block font-bold text-xs text-gray-500 dark:text-gray-500 mb-2 uppercase tracking-wider">Job Title</label>
                <div className="text-lg text-[#1b1b1b] dark:text-white border-b border-black/10 dark:border-white/10 pb-3 font-medium">Senior Software Engineer</div>
              </div>
              <div>
                <label className="block font-bold text-xs text-gray-500 dark:text-gray-500 mb-2 uppercase tracking-wider">Reports To</label>
                <div className="text-lg text-[#1b1b1b] dark:text-white border-b border-black/10 dark:border-white/10 pb-3 font-medium flex items-center gap-3">
                  <img 
                    alt="Manager avatar" 
                    className="w-8 h-8 rounded-full object-cover border border-black/20 dark:border-white/20" 
                    src="https://images.unsplash.com/photo-1472099645785-5658abf4ff4e?auto=format&fit=crop&q=80&w=100&h=100" 
                  />
                  Michael Chang (Director)
                </div>
              </div>
              <div>
                <label className="block font-bold text-xs text-gray-500 dark:text-gray-500 mb-2 uppercase tracking-wider">System Role</label>
                <div className="text-lg text-[#1b1b1b] dark:text-white border-b border-black/10 dark:border-white/10 pb-3 font-medium flex items-center">
                  <span className="bg-black/10 dark:bg-white/10 text-gray-800 dark:text-gray-200 px-3 py-1 rounded-md text-sm font-bold">Manager</span>
                </div>
              </div>
            </div>

            <div className="mt-8 pt-8 border-t border-black/10 dark:border-white/10">
              <h5 className="font-bold text-xs text-gray-500 dark:text-gray-500 mb-4 uppercase tracking-wider">Contact Information</h5>
              <div className="flex flex-col gap-4">
                <div className="flex items-center gap-3 text-gray-700 dark:text-gray-300 font-medium">
                  <Mail className="w-5 h-5 text-[#ea0029]" />
                  s.jenkins@vinfast.com
                </div>
                <div className="flex items-center gap-3 text-gray-700 dark:text-gray-300 font-medium">
                  <Phone className="w-5 h-5 text-[#ea0029]" />
                  +84 123 456 789
                </div>
              </div>
            </div>
          </div>

          {/* Access Permissions */}
          <div className="bg-black/5 dark:bg-white/5 backdrop-blur-md rounded-2xl p-8 border border-black/10 dark:border-white/10 shadow-sm lg:col-span-3">
            <div className="flex flex-col md:flex-row justify-between md:items-center gap-4 mb-8">
              <h4 className="text-xl font-bold text-[#1b1b1b] dark:text-white flex items-center gap-2">
                <Settings className="w-6 h-6 text-[#ea0029]" />
                Access Permissions & RBAC
              </h4>
              <span className="font-bold text-xs text-[#ea0029] bg-[#ea0029]/10 border border-[#ea0029]/20 px-4 py-2 rounded-full tracking-wide">
                Role: Manager Level 2
              </span>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              {/* Permission Group 1 */}
              <div className="bg-black/5 dark:bg-white/5 border border-black/10 dark:border-white/10 rounded-xl p-6 hover:bg-black/10 dark:bg-white/10 transition-colors">
                <div className="flex items-center gap-3 mb-6">
                  <Book className="w-6 h-6 text-[#ea0029]" />
                  <h5 className="font-bold text-lg text-[#1b1b1b] dark:text-white">Knowledge Base</h5>
                </div>
                <ul className="space-y-4 text-gray-700 dark:text-gray-300">
                  <li className="flex items-center gap-3">
                    <CheckCircle2 className="w-5 h-5 text-emerald-400" />
                    Global HR Policies
                  </li>
                  <li className="flex items-center gap-3">
                    <CheckCircle2 className="w-5 h-5 text-emerald-400" />
                    Engineering Dept Guidelines
                  </li>
                  <li className="flex items-center gap-3">
                    <CheckCircle2 className="w-5 h-5 text-emerald-400" />
                    Managerial Handbooks
                  </li>
                </ul>
              </div>

              {/* Permission Group 2 */}
              <div className="bg-black/5 dark:bg-white/5 border border-black/10 dark:border-white/10 rounded-xl p-6 hover:bg-black/10 dark:bg-white/10 transition-colors">
                <div className="flex items-center gap-3 mb-6">
                  <Users className="w-6 h-6 text-[#ea0029]" />
                  <h5 className="font-bold text-lg text-[#1b1b1b] dark:text-white">Team Management</h5>
                </div>
                <ul className="space-y-4 text-gray-700 dark:text-gray-300">
                  <li className="flex items-center gap-3">
                    <CheckCircle2 className="w-5 h-5 text-emerald-400" />
                    View Direct Reports&apos; Leave
                  </li>
                  <li className="flex items-center gap-3">
                    <CheckCircle2 className="w-5 h-5 text-emerald-400" />
                    Approve Leave Requests
                  </li>
                  <li className="flex items-center gap-3 opacity-50 text-gray-600 dark:text-gray-400">
                    <XCircle className="w-5 h-5" />
                    <span>Performance Reviews <span className="text-xs ml-1">(Locked)</span></span>
                  </li>
                </ul>
              </div>

              {/* Permission Group 3 */}
              <div className="bg-black/5 dark:bg-white/5 border border-black/10 dark:border-white/10 rounded-xl p-6 hover:bg-black/10 dark:bg-white/10 transition-colors">
                <div className="flex items-center gap-3 mb-6">
                  <Settings className="w-6 h-6 text-[#ea0029]" />
                  <h5 className="font-bold text-lg text-[#1b1b1b] dark:text-white">System Settings</h5>
                </div>
                <ul className="space-y-4 text-gray-700 dark:text-gray-300">
                  <li className="flex items-center gap-3">
                    <CheckCircle2 className="w-5 h-5 text-emerald-400" />
                    Personal Profile Edit
                  </li>
                  <li className="flex items-center gap-3 opacity-50 text-gray-600 dark:text-gray-400">
                    <XCircle className="w-5 h-5" />
                    <span>Department Settings <span className="text-xs ml-1">(Locked)</span></span>
                  </li>
                  <li className="flex items-center gap-3 opacity-50 text-gray-600 dark:text-gray-400">
                    <XCircle className="w-5 h-5" />
                    <span>Global Broadcasts <span className="text-xs ml-1">(Locked)</span></span>
                  </li>
                </ul>
              </div>
            </div>
          </div>

        </div>
      </div>
    </div>
  );
}
