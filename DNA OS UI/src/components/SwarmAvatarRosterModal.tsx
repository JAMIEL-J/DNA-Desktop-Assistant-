import React, { useState } from 'react';
import { AgentProcess, AgentRole } from '../types';
import { AgentAvatarCard } from './AgentAvatarCard';
import { Sparkles, X, Users, Search, Play, Pause, RefreshCw, Zap, Shield, Cpu } from 'lucide-react';
import { motion, AnimatePresence } from 'motion/react';

interface SwarmAvatarRosterModalProps {
  isOpen: boolean;
  agents: AgentProcess[];
  onClose: () => void;
  onSelectAgent: (id: string) => void;
  onSpawnNewAgent: () => void;
}

export const SwarmAvatarRosterModal: React.FC<SwarmAvatarRosterModalProps> = ({
  isOpen,
  agents,
  onClose,
  onSelectAgent,
  onSpawnNewAgent,
}) => {
  const [filterRole, setFilterRole] = useState<string>('ALL');
  const [searchQuery, setSearchQuery] = useState('');

  if (!isOpen) return null;

  const roles: AgentRole[] = ['Research', 'Planner', 'Developer', 'QA', 'Writer', 'Analyst'];

  const filteredAgents = agents.filter((agent) => {
    const matchesRole = filterRole === 'ALL' || agent.role === filterRole;
    const matchesSearch =
      agent.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      agent.activeTask.toLowerCase().includes(searchQuery.toLowerCase()) ||
      agent.role.toLowerCase().includes(searchQuery.toLowerCase());
    return matchesRole && matchesSearch;
  });

  return (
    <AnimatePresence>
      <div className="fixed inset-0 z-50 bg-[#050505]/90 backdrop-blur-2xl flex items-center justify-center p-4 sm:p-6 overflow-hidden select-none font-sans">
        <motion.div
          initial={{ opacity: 0, scale: 0.95, y: 20 }}
          animate={{ opacity: 1, scale: 1, y: 0 }}
          exit={{ opacity: 0, scale: 0.95, y: 20 }}
          transition={{ duration: 0.25, ease: 'easeOut' }}
          className="w-full max-w-6xl h-[90vh] bg-[#0B0B0B] border border-[#1A1A1A] rounded-2xl shadow-2xl flex flex-col overflow-hidden"
        >
          {/* Header Bar */}
          <div className="px-6 py-4 bg-[#050505] border-b border-[#1A1A1A] flex flex-col md:flex-row md:items-center justify-between gap-4 shrink-0">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-[#B983FF]/10 border border-[#B983FF]/30 flex items-center justify-center text-[#B983FF]">
                <Users className="w-5 h-5" />
              </div>
              <div>
                <h2 className="text-base font-bold text-[#D1D1D1] flex items-center gap-2">
                  <span>SWARM NEURAL ROSTER</span>
                  <span className="px-2 py-0.5 bg-[#B983FF]/20 text-[#B983FF] text-[10px] font-mono rounded-full border border-[#B983FF]/40">
                    6 ACTIVE AVATAR CARDS
                  </span>
                </h2>
                <p className="text-xs text-[#666666] font-sans">
                  Inspect cybernetic process metrics, subroutines, and system prompts for each cluster agent.
                </p>
              </div>
            </div>

            <div className="flex items-center gap-2">
              <button
                onClick={onSpawnNewAgent}
                className="px-3.5 py-1.5 bg-[#B983FF]/15 hover:bg-[#B983FF]/25 border border-[#B983FF]/40 text-[#B983FF] font-semibold text-xs rounded-lg transition flex items-center gap-1.5"
              >
                <Zap className="w-3.5 h-3.5" />
                <span>Spawn Agent</span>
              </button>

              <button
                onClick={onClose}
                className="w-8 h-8 flex items-center justify-center bg-[#111111] hover:bg-[#1A1A1A] border border-[#1A1A1A] text-[#888888] hover:text-[#D1D1D1] rounded-lg transition"
                title="Close Roster"
              >
                <X className="w-4 h-4" />
              </button>
            </div>
          </div>

          {/* Search & Role Filter Tabs */}
          <div className="px-6 py-3 bg-[#080808] border-b border-[#1A1A1A] flex flex-col sm:flex-row sm:items-center justify-between gap-3 shrink-0">
            {/* Search Field */}
            <div className="relative flex-1 max-w-xs">
              <Search className="w-3.5 h-3.5 text-[#555555] absolute left-3 top-1/2 -translate-y-1/2" />
              <input
                type="text"
                placeholder="Search agent name or task..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full bg-[#050505] border border-[#1A1A1A] focus:border-[#B983FF] text-[#D1D1D1] pl-8 pr-3 py-1.5 rounded-lg text-xs outline-none transition"
              />
            </div>

            {/* Role Filter Chips */}
            <div className="flex items-center gap-1.5 overflow-x-auto pb-1 sm:pb-0 scrollbar-none">
              <button
                onClick={() => setFilterRole('ALL')}
                className={`px-3 py-1 rounded-lg text-xs font-semibold transition ${
                  filterRole === 'ALL'
                    ? 'bg-[#1A1A1A] text-[#B983FF] border border-[#333333]'
                    : 'bg-[#050505] text-[#666666] hover:text-[#D1D1D1] border border-[#1A1A1A]'
                }`}
              >
                All (6)
              </button>

              {roles.map((role) => (
                <button
                  key={role}
                  onClick={() => setFilterRole(role)}
                  className={`px-2.5 py-1 rounded-lg text-xs font-semibold transition ${
                    filterRole === role
                      ? 'bg-[#1A1A1A] text-[#B983FF] border border-[#333333]'
                      : 'bg-[#050505] text-[#666666] hover:text-[#D1D1D1] border border-[#1A1A1A]'
                  }`}
                >
                  {role}
                </button>
              ))}
            </div>
          </div>

          {/* Avatar Cards Grid */}
          <div className="flex-1 p-6 overflow-y-auto custom-scrollbar">
            {filteredAgents.length === 0 ? (
              <div className="h-full flex flex-col items-center justify-center text-center text-[#555555] font-sans">
                <Users className="w-8 h-8 mb-2 opacity-40 text-[#B983FF]" />
                <p className="text-xs">No agent avatar cards matched your search filter.</p>
              </div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                {filteredAgents.map((agent) => (
                  <AgentAvatarCard
                    key={agent.id}
                    agent={agent}
                    onSelectAgent={(id) => {
                      onSelectAgent(id);
                      onClose();
                    }}
                  />
                ))}
              </div>
            )}
          </div>

          {/* Footer Bar */}
          <div className="px-6 py-3 bg-[#050505] border-t border-[#1A1A1A] flex items-center justify-between text-xs font-mono text-[#555555] shrink-0">
            <div className="flex items-center gap-2">
              <Cpu className="w-3.5 h-3.5 text-[#7DCE13]" />
              <span>SYNAPSE MESH ONLINE &bull; 6 AGENT THREADS EXECUTING</span>
            </div>

            <button
              onClick={onClose}
              className="px-4 py-1.5 bg-[#111111] hover:bg-[#1A1A1A] border border-[#1A1A1A] text-[#D1D1D1] font-sans font-semibold text-xs rounded-lg transition"
            >
              Return to Workspace
            </button>
          </div>
        </motion.div>
      </div>
    </AnimatePresence>
  );
};
