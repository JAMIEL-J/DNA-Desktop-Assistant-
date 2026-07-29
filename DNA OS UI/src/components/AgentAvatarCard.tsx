import React, { useState } from 'react';
import { AgentProcess, AgentRole } from '../types';
import { ROLE_COLORS } from '../data/initialAgents';
import { Cpu, HardDrive, Terminal, Shield, Sparkles, Activity, CheckCircle2, RotateCcw, ExternalLink, Code2, Search, Calendar, FileText, BarChart3, ShieldAlert, Cpu as CpuIcon } from 'lucide-react';
import { motion } from 'motion/react';

interface AgentAvatarCardProps {
  agent: AgentProcess;
  onSelectAgent?: (id: string) => void;
  onExecutePrompt?: (agentId: string, prompt: string) => void;
  isCompact?: boolean;
}

const ROLE_ICONS: Record<AgentRole, React.ReactNode> = {
  Research: <Search className="w-4 h-4 text-blue-400" />,
  Planner: <Calendar className="w-4 h-4 text-purple-400" />,
  Developer: <Code2 className="w-4 h-4 text-orange-400" />,
  QA: <ShieldAlert className="w-4 h-4 text-red-400" />,
  Writer: <FileText className="w-4 h-4 text-emerald-400" />,
  Analyst: <BarChart3 className="w-4 h-4 text-cyan-400" />,
};

const AVATAR_VISORS: Record<AgentRole, { bg: string; accent: string; label: string; svgGradient: string }> = {
  Research: {
    bg: 'from-blue-900/40 via-blue-950/80 to-[#0B0B0B]',
    accent: '#3b82f6',
    label: 'NEURAL RESEARCHER',
    svgGradient: 'url(#grad-blue)',
  },
  Planner: {
    bg: 'from-purple-900/40 via-purple-950/80 to-[#0B0B0B]',
    accent: '#a855f7',
    label: 'TEMPORAL STRATEGIST',
    svgGradient: 'url(#grad-purple)',
  },
  Developer: {
    bg: 'from-orange-900/40 via-orange-950/80 to-[#0B0B0B]',
    accent: '#f97316',
    label: 'KERNEL ENGINE ARCHITECT',
    svgGradient: 'url(#grad-orange)',
  },
  QA: {
    bg: 'from-red-900/40 via-red-950/80 to-[#0B0B0B]',
    accent: '#ef4444',
    label: 'CHAOS AUDITOR',
    svgGradient: 'url(#grad-red)',
  },
  Writer: {
    bg: 'from-emerald-900/40 via-emerald-950/80 to-[#0B0B0B]',
    accent: '#22c55e',
    label: 'SPEC ARCHIVIST',
    svgGradient: 'url(#grad-emerald)',
  },
  Analyst: {
    bg: 'from-cyan-900/40 via-cyan-950/80 to-[#0B0B0B]',
    accent: '#06b6d4',
    label: 'TELEMETRY PRISM',
    svgGradient: 'url(#grad-cyan)',
  },
};

export const AgentAvatarCard: React.FC<AgentAvatarCardProps> = ({
  agent,
  onSelectAgent,
  onExecutePrompt,
  isCompact = false,
}) => {
  const [isFlipped, setIsFlipped] = useState(false);
  const roleStyle = ROLE_COLORS[agent.role] || ROLE_COLORS.Research;
  const visorStyle = AVATAR_VISORS[agent.role] || AVATAR_VISORS.Research;

  const handleCardClick = () => {
    if (onSelectAgent) {
      onSelectAgent(agent.id);
    }
  };

  return (
    <div
      className={`relative group perspective-1000 select-none ${
        isCompact ? 'w-full max-w-xs' : 'w-full max-w-sm'
      }`}
    >
      <motion.div
        whileHover={{ scale: 1.02, y: -4 }}
        transition={{ duration: 0.2 }}
        className="w-full bg-[#0B0B0B] border border-[#1A1A1A] rounded-2xl overflow-hidden shadow-xl relative transition-all duration-300"
        style={{
          boxShadow: `0 0 25px ${roleStyle.hex}18, 0 0 1px ${roleStyle.hex}66`,
          borderColor: `${roleStyle.hex}44`,
        }}
      >
        {/* Top Header Identity Ribbon */}
        <div className="flex items-center justify-between px-3.5 py-2.5 bg-[#050505] border-b border-[#1A1A1A]">
          <div className="flex items-center gap-2 min-w-0">
            <span
              className="w-2.5 h-2.5 rounded-full animate-pulse shrink-0"
              style={{ backgroundColor: roleStyle.hex }}
            />
            <span className="font-bold text-xs text-[#D1D1D1] truncate">{agent.name}</span>
            <span
              className="px-1.5 py-0.2 text-[9px] font-bold uppercase rounded border shrink-0"
              style={{
                backgroundColor: `${roleStyle.hex}18`,
                color: roleStyle.hex,
                borderColor: `${roleStyle.hex}44`,
              }}
            >
              {agent.role}
            </span>
          </div>

          <button
            onClick={(e) => {
              e.stopPropagation();
              setIsFlipped(!isFlipped);
            }}
            className="text-[10px] font-mono text-[#666666] hover:text-[#B983FF] hover:bg-[#111111] px-2 py-0.5 rounded border border-transparent hover:border-[#222222] transition flex items-center gap-1"
            title="Flip to view process specifications & prompt"
          >
            <RotateCcw className="w-3 h-3" />
            <span>{isFlipped ? 'Card Front' : 'Inspect'}</span>
          </button>
        </div>

        {/* Card Front View */}
        {!isFlipped ? (
          <div className="p-4 flex flex-col gap-3">
            {/* Cybernetic Sci-Fi Avatar Graphic Header */}
            <div
              className={`relative h-28 rounded-xl bg-gradient-to-br ${visorStyle.bg} border border-[#1A1A1A] flex items-center justify-between px-4 overflow-hidden group-hover:border-[${roleStyle.hex}]/40 transition-colors`}
            >
              {/* Animated Matrix Grid Overlay */}
              <div
                className="absolute inset-0 opacity-15 pointer-events-none"
                style={{
                  backgroundImage: `radial-gradient(${roleStyle.hex} 1px, transparent 0)`,
                  backgroundSize: '12px 12px',
                }}
              />

              {/* Avatar Headshot Cyber graphic */}
              <div className="relative z-10 flex items-center gap-3">
                <div
                  className="relative w-16 h-16 rounded-xl flex items-center justify-center border-2 shadow-xl overflow-hidden bg-[#050505]"
                  style={{ borderColor: roleStyle.hex, boxShadow: `0 0 15px ${roleStyle.hex}44` }}
                >
                  {/* Cybernetic Neural SVG Graphic Portrait */}
                  <svg className="w-12 h-12" viewBox="0 0 100 100" fill="none" xmlns="http://www.w3.org/2000/svg">
                    <defs>
                      <linearGradient id={`grad-${agent.role}`} x1="0%" y1="0%" x2="100%" y2="100%">
                        <stop offset="0%" stopColor={roleStyle.hex} stopOpacity="1" />
                        <stop offset="100%" stopColor="#0B0B0B" stopOpacity="0.8" />
                      </linearGradient>
                    </defs>

                    {/* Cyber Helmet/Visor Shape */}
                    <circle cx="50" cy="42" r="28" fill={`url(#grad-${agent.role})`} opacity="0.3" />
                    <rect x="25" y="32" width="50" height="18" rx="9" fill={roleStyle.hex} opacity="0.85" />
                    <rect x="30" y="36" width="40" height="10" rx="5" fill="#0B0B0B" opacity="0.9" />

                    {/* Glowing Optics Eyes */}
                    <circle cx="42" cy="41" r="3" fill={roleStyle.hex} />
                    <circle cx="58" cy="41" r="3" fill={roleStyle.hex} />

                    {/* Circuit Lines */}
                    <path d="M50 14V28M22 41H12M78 41H88M34 68L50 82L66 68" stroke={roleStyle.hex} strokeWidth="3" strokeLinecap="round" opacity="0.8" />
                    <circle cx="50" cy="82" r="4" fill={roleStyle.hex} />
                  </svg>

                  {/* Online Status Pulse Ring */}
                  <span
                    className="absolute bottom-1 right-1 w-3 h-3 rounded-full border-2 border-[#0B0B0B] bg-[#7DCE13] animate-pulse"
                  />
                </div>

                <div className="min-w-0">
                  <div className="text-[10px] font-mono text-[#888888] tracking-widest uppercase">
                    {visorStyle.label}
                  </div>
                  <div className="text-sm font-bold text-[#FFFFFF] tracking-tight truncate">
                    {agent.name}
                  </div>
                  <div className="text-[10px] font-mono text-[#666666] flex items-center gap-1.5 mt-0.5">
                    <span>PID {agent.pid}</span>
                    <span>&bull;</span>
                    <span className="text-[#B983FF] font-semibold">{agent.transparency.modelUsed.split('-')[1] || 'gemini'}</span>
                  </div>
                </div>
              </div>

              {/* Top Right Mini Telemetry Gauge */}
              <div className="relative z-10 flex flex-col items-end gap-1 font-mono text-[10px]">
                <span className="flex items-center gap-1 text-[#D1D1D1] bg-[#050505]/80 px-2 py-0.5 rounded border border-[#1A1A1A]">
                  <Cpu className="w-3 h-3 text-[#B983FF]" />
                  <span>{agent.cpuUsagePercent}%</span>
                </span>
                <span className="flex items-center gap-1 text-[#888888] bg-[#050505]/80 px-2 py-0.5 rounded border border-[#1A1A1A]">
                  <HardDrive className="w-3 h-3 text-[#4D96FF]" />
                  <span>{agent.memoryUsageMb}MB</span>
                </span>
              </div>
            </div>

            {/* Active Task Box */}
            <div className="bg-[#050505] border border-[#1A1A1A] rounded-xl p-3 flex flex-col gap-1 text-xs">
              <span className="text-[10px] font-bold text-[#555555] uppercase tracking-wider flex items-center gap-1">
                <Activity className="w-3 h-3 text-[#7DCE13]" />
                CURRENT SUBROUTINE:
              </span>
              <p className="text-[#CCCCCC] font-sans text-[11px] line-clamp-2 leading-relaxed">
                {agent.activeTask}
              </p>
            </div>

            {/* Skill Badges */}
            <div className="flex flex-wrap gap-1.5">
              {(agent.skillBadges || ['Vector Search', 'RAG Engine', 'Distributed Consensus', 'Async RPC']).map((badge, idx) => (
                <span
                  key={idx}
                  className="px-2 py-0.5 text-[9px] font-mono rounded-md bg-[#111111] border border-[#1A1A1A] text-[#888888]"
                >
                  #{badge}
                </span>
              ))}
            </div>

            {/* Bottom Actions Row */}
            <div className="pt-1 flex items-center gap-2">
              <button
                onClick={handleCardClick}
                className="flex-1 h-8 bg-[#111111] hover:bg-[#1A1A1A] border border-[#1A1A1A] hover:border-[#333333] text-[#D1D1D1] text-xs font-semibold rounded-lg transition flex items-center justify-center gap-1.5"
              >
                <span>Focus Process Window</span>
                <ExternalLink className="w-3.5 h-3.5 text-[#B983FF]" />
              </button>
            </div>
          </div>
        ) : (
          /* Card Back View - Deep Specs & Prompt */
          <div className="p-4 flex flex-col gap-3 min-h-[260px] bg-[#050505] text-xs">
            <div className="flex items-center justify-between border-b border-[#1A1A1A] pb-2">
              <span className="font-bold text-[#B983FF] flex items-center gap-1.5 text-xs">
                <Sparkles className="w-3.5 h-3.5" />
                PROCESS SPECIFICATIONS
              </span>
              <span className="text-[10px] font-mono text-[#555555]">PID {agent.pid}</span>
            </div>

            {/* Transparency Reason Summary */}
            <div className="space-y-1.5">
              <span className="text-[10px] font-bold text-[#555555] uppercase tracking-wider">
                CORE ARCHITECTURE REASONING:
              </span>
              <ul className="space-y-1 text-[11px] text-[#A0A0A0] font-sans">
                {agent.transparency.reasoningSummary.slice(0, 3).map((r, i) => (
                  <li key={i} className="flex items-start gap-1.5">
                    <span className="text-[#7DCE13] mt-0.5">&bull;</span>
                    <span>{r}</span>
                  </li>
                ))}
              </ul>
            </div>

            {/* Execution Stats */}
            <div className="grid grid-cols-2 gap-2 bg-[#0B0B0B] border border-[#1A1A1A] p-2.5 rounded-xl font-mono text-[10px]">
              <div>
                <span className="text-[#555555] block">CONFIDENCE:</span>
                <span className="text-[#7DCE13] font-bold text-xs">{agent.transparency.confidenceScore}%</span>
              </div>
              <div>
                <span className="text-[#555555] block">TOKENS:</span>
                <span className="text-[#D1D1D1] font-bold text-xs">{agent.transparency.tokensConsumed.toLocaleString()}</span>
              </div>
              <div>
                <span className="text-[#555555] block">LATENCY:</span>
                <span className="text-[#4D96FF] font-bold text-xs">{agent.transparency.executionDurationMs}ms</span>
              </div>
              <div>
                <span className="text-[#555555] block">DEPENDENCIES:</span>
                <span className="text-[#B983FF] font-bold text-xs">{agent.transparency.dependencies.length} node(s)</span>
              </div>
            </div>

            <button
              onClick={handleCardClick}
              className="mt-auto h-8 bg-[#B983FF]/15 hover:bg-[#B983FF]/25 border border-[#B983FF]/40 text-[#B983FF] text-xs font-bold rounded-lg transition flex items-center justify-center gap-1.5"
            >
              <Terminal className="w-3.5 h-3.5" />
              <span>Launch Terminal Tab</span>
            </button>
          </div>
        )}
      </motion.div>
    </div>
  );
};
