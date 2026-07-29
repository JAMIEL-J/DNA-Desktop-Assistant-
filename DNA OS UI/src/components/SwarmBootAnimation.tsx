import React, { useState, useEffect } from 'react';
import { AgentProcess, AgentRole } from '../types';
import { ROLE_COLORS } from '../data/initialAgents';
import { Sparkles, Terminal, Activity, Cpu, CheckCircle2, FastForward, Play, ShieldAlert, FileText, BarChart3, Code2, Search, Calendar } from 'lucide-react';
import { motion, AnimatePresence } from 'motion/react';

interface SwarmBootAnimationProps {
  agents: AgentProcess[];
  onComplete: () => void;
}

interface AgentReportData {
  agentId: string;
  reportMessage: string;
  icon: React.ReactNode;
  telemetry: string;
}

const REPORT_MESSAGES: Record<string, { message: string; icon: React.ReactNode; telemetry: string }> = {
  'agent-research-01': {
    message: 'Atlas-Research initialized. Scanned 42 distributed consensus papers into Milvus vector store.',
    icon: <Search className="w-5 h-5 text-blue-400" />,
    telemetry: 'VECTOR MATCH: 96.2% | MILVUS gRPC: OK',
  },
  'agent-planner-02': {
    message: 'Chronos-Planner initialized. Decomposed requirements into 6-stage topological DAG execution plan.',
    icon: <Calendar className="w-5 h-5 text-purple-400" />,
    telemetry: 'CRITICAL PATH: 4.2s | DAG TASKS: 6',
  },
  'agent-developer-03': {
    message: 'Nexus-Developer initialized. Compiled Tokio-based Rust Raft RPC daemon with 0 compiler warnings.',
    icon: <Code2 className="w-5 h-5 text-orange-400" />,
    telemetry: 'CARGO BUILD: RELEASE | BINARY: 11.4MB',
  },
  'agent-qa-04': {
    message: 'Vigil-QA initialized. Passed 1,000 split-brain network partition chaos fuzz assertions.',
    icon: <ShieldAlert className="w-5 h-5 text-red-400" />,
    telemetry: 'CHAOS COVERAGE: 94.8% | SAFETY: 100%',
  },
  'agent-writer-05': {
    message: 'Scribe-Writer initialized. Published OpenAPI 3.1 specifications and RAFT_ARCHITECTURE.md docs.',
    icon: <FileText className="w-5 h-5 text-emerald-400" />,
    telemetry: 'AST DOCS: VALIDATED | SPEC: OPENAPI v3.1',
  },
  'agent-analyst-06': {
    message: 'Prism-Analyst initialized. Telemetry aggregated across all cluster nodes. Efficiency at 99.4%.',
    icon: <BarChart3 className="w-5 h-5 text-cyan-400" />,
    telemetry: 'CLUSTER HEALTH: OPTIMAL | COST RATIO: 99.4%',
  },
};

export const SwarmBootAnimation: React.FC<SwarmBootAnimationProps> = ({
  agents,
  onComplete,
}) => {
  const [currentIndex, setCurrentIndex] = useState(0);
  const [dockedIds, setDockedIds] = useState<string[]>([]);
  const [typedMessage, setTypedMessage] = useState('');
  const [isTyping, setIsTyping] = useState(true);

  const currentAgent = agents[currentIndex] || agents[0];
  const reportInfo = currentAgent ? REPORT_MESSAGES[currentAgent.id] || {
    message: `${currentAgent.name} online. System initialized and awaiting task execution.`,
    icon: <Activity className="w-5 h-5 text-purple-400" />,
    telemetry: 'STATUS: ACTIVE | KERNEL: READY',
  } : null;

  const roleStyle = currentAgent ? ROLE_COLORS[currentAgent.role as AgentRole] || ROLE_COLORS.Research : ROLE_COLORS.Research;

  // Typewriter effect for current agent message
  useEffect(() => {
    if (!reportInfo) return;
    setTypedMessage('');
    setIsTyping(true);

    let charIdx = 0;
    const fullText = reportInfo.message;

    const interval = setInterval(() => {
      if (charIdx < fullText.length) {
        setTypedMessage(fullText.slice(0, charIdx + 1));
        charIdx++;
      } else {
        setIsTyping(false);
        clearInterval(interval);
      }
    }, 22);

    return () => clearInterval(interval);
  }, [currentIndex, reportInfo]);

  // Auto-advance agent reporting sequence
  useEffect(() => {
    const timer = setTimeout(() => {
      if (currentIndex < agents.length - 1) {
        if (currentAgent) {
          setDockedIds((prev) => [...prev, currentAgent.id]);
        }
        setCurrentIndex((prev) => prev + 1);
      } else {
        // All 6 agents reported!
        if (currentAgent) {
          setDockedIds((prev) => [...prev, currentAgent.id]);
        }
        setTimeout(() => {
          onComplete();
        }, 800);
      }
    }, 2800);

    return () => clearTimeout(timer);
  }, [currentIndex, agents, currentAgent, onComplete]);

  const handleNextAgent = () => {
    if (currentIndex < agents.length - 1) {
      if (currentAgent) {
        setDockedIds((prev) => [...prev, currentAgent.id]);
      }
      setCurrentIndex((prev) => prev + 1);
    } else {
      onComplete();
    }
  };

  const handleSkipAll = () => {
    onComplete();
  };

  return (
    <div className="absolute inset-0 z-40 bg-[#050505]/90 backdrop-blur-xl flex flex-col items-center justify-center p-6 overflow-hidden select-none font-sans">
      {/* Top Banner Control */}
      <div className="absolute top-4 left-6 right-6 flex items-center justify-between z-50">
        <div className="flex items-center gap-2 text-xs font-semibold text-[#B983FF] tracking-wider uppercase">
          <Sparkles className="w-4 h-4 animate-pulse" />
          <span>SWARM BOOT SEQUENCE &bull; AGENT {currentIndex + 1} OF {agents.length} REPORTING</span>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={handleNextAgent}
            className="px-3 py-1 bg-[#111111] hover:bg-[#1A1A1A] border border-[#1A1A1A] text-[#D1D1D1] rounded text-xs transition flex items-center gap-1.5"
          >
            <span>Next Agent</span>
            <Play className="w-3 h-3 fill-current" />
          </button>

          <button
            onClick={handleSkipAll}
            className="px-3 py-1 bg-[#1A1A1A] hover:bg-[#222222] border border-[#333333] text-[#888888] hover:text-[#D1D1D1] rounded text-xs transition flex items-center gap-1.5"
          >
            <span>Skip Sequence</span>
            <FastForward className="w-3 h-3" />
          </button>
        </div>
      </div>

      {/* Center Animated Profile Card */}
      <AnimatePresence mode="wait">
        {currentAgent && (
          <motion.div
            key={currentAgent.id}
            initial={{ opacity: 0, scale: 0.85, y: 30 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.7, y: -40, x: (currentIndex % 2 === 0 ? -120 : 120) }}
            transition={{ duration: 0.45, ease: [0.16, 1, 0.3, 1] }}
            className="w-full max-w-xl bg-[#0B0B0B] border border-[#1A1A1A] rounded-2xl p-6 shadow-2xl relative overflow-hidden"
            style={{
              boxShadow: `0 0 40px ${roleStyle.hex}22, 0 0 1px ${roleStyle.hex}88`,
              borderColor: `${roleStyle.hex}55`,
            }}
          >
            {/* Top Agent Identity Bar */}
            <div className="flex items-center justify-between border-b border-[#1A1A1A] pb-4 mb-4">
              <div className="flex items-center gap-3">
                {/* Cybernetic Neural Avatar Graphic Portrait */}
                <div
                  className="relative w-14 h-14 rounded-xl flex items-center justify-center border-2 shadow-xl overflow-hidden bg-[#050505] shrink-0"
                  style={{ borderColor: roleStyle.hex, boxShadow: `0 0 20px ${roleStyle.hex}44` }}
                >
                  <svg className="w-10 h-10" viewBox="0 0 100 100" fill="none" xmlns="http://www.w3.org/2000/svg">
                    <circle cx="50" cy="42" r="28" fill={roleStyle.hex} opacity="0.3" />
                    <rect x="25" y="32" width="50" height="18" rx="9" fill={roleStyle.hex} opacity="0.85" />
                    <rect x="30" y="36" width="40" height="10" rx="5" fill="#0B0B0B" opacity="0.9" />
                    <circle cx="42" cy="41" r="3" fill={roleStyle.hex} />
                    <circle cx="58" cy="41" r="3" fill={roleStyle.hex} />
                    <path d="M50 14V28M22 41H12M78 41H88M34 68L50 82L66 68" stroke={roleStyle.hex} strokeWidth="3" strokeLinecap="round" opacity="0.8" />
                    <circle cx="50" cy="82" r="4" fill={roleStyle.hex} />
                  </svg>
                  <span className="absolute bottom-1 right-1 w-2.5 h-2.5 rounded-full border border-[#0B0B0B] bg-[#7DCE13] animate-pulse" />
                </div>

                <div>
                  <div className="flex items-center gap-2">
                    <span className="text-base font-bold text-[#D1D1D1] tracking-tight">{currentAgent.name}</span>
                    <span
                      className="px-2 py-0.5 text-[10px] font-bold uppercase rounded border"
                      style={{ backgroundColor: `${roleStyle.hex}20`, color: roleStyle.hex, borderColor: `${roleStyle.hex}50` }}
                    >
                      {currentAgent.role}
                    </span>
                  </div>

                  <div className="text-[11px] font-mono text-[#666666] flex items-center gap-2 mt-0.5">
                    <span>PID: {currentAgent.pid}</span>
                    <span>&bull;</span>
                    <span className="text-[#7DCE13] flex items-center gap-1 font-semibold">
                      <span className="w-1.5 h-1.5 rounded-full bg-[#7DCE13] animate-pulse"></span>
                      ONLINE &amp; REPORTING
                    </span>
                  </div>
                </div>
              </div>

              {/* Live Waveform Audio Indicator */}
              <div className="flex items-center gap-1 h-6 px-2.5 bg-[#050505] border border-[#1A1A1A] rounded-lg">
                {[40, 80, 50, 90, 60, 100, 70, 30].map((h, i) => (
                  <div
                    key={i}
                    className="w-1 bg-[#B983FF] rounded-full animate-pulse"
                    style={{
                      height: `${isTyping ? h : 20}%`,
                      animationDelay: `${i * 0.1}s`,
                      backgroundColor: roleStyle.hex,
                    }}
                  />
                ))}
              </div>
            </div>

            {/* Typewriter Voice Terminal Report Output */}
            <div className="bg-[#050505] border border-[#1A1A1A] rounded-xl p-4 font-mono text-xs text-[#CCCCCC] min-h-[85px] relative">
              <div className="flex items-center justify-between text-[10px] text-[#555555] mb-2 font-bold uppercase">
                <span className="flex items-center gap-1.5 text-[#B983FF]">
                  <Terminal className="w-3 h-3" />
                  RESPONSE TRANSMISSION
                </span>
                <span className="text-[#7DCE13] flex items-center gap-1">
                  <CheckCircle2 className="w-3 h-3" /> VERIFIED
                </span>
              </div>

              <p className="leading-relaxed">
                {typedMessage}
                {isTyping && <span className="inline-block w-2 h-3 bg-[#B983FF] ml-1 animate-pulse" />}
              </p>
            </div>

            {/* Telemetry Status Footer */}
            <div className="mt-4 flex items-center justify-between text-[11px] font-mono text-[#666666] pt-2 border-t border-[#111111]">
              <div className="flex items-center gap-2">
                <Cpu className="w-3.5 h-3.5 text-[#555555]" />
                <span>{reportInfo?.telemetry}</span>
              </div>

              <div className="text-[10px] text-[#888888] font-sans italic">
                Docking to workspace tile...
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Docked Agents Progress Bar Icons at Bottom */}
      <div className="absolute bottom-6 flex items-center gap-3 bg-[#0B0B0B] border border-[#1A1A1A] px-4 py-2 rounded-full shadow-xl">
        <span className="text-[10px] font-bold text-[#555555] uppercase tracking-wider mr-1">SWARM DOCK:</span>
        {agents.map((ag, i) => {
          const isCurrent = i === currentIndex;
          const isDocked = dockedIds.includes(ag.id);
          const agRoleStyle = ROLE_COLORS[ag.role as AgentRole] || ROLE_COLORS.Research;

          return (
            <div
              key={ag.id}
              className={`flex items-center gap-1.5 px-2.5 py-1 rounded-full border text-[11px] font-medium transition-all ${
                isCurrent
                  ? 'bg-[#111111] text-[#D1D1D1] border-[#B983FF] scale-105 shadow-[0_0_10px_rgba(185,131,255,0.3)]'
                  : isDocked
                  ? 'bg-[#050505] text-[#888888] border-[#222222]'
                  : 'bg-[#050505] text-[#444444] border-[#111111] opacity-40'
              }`}
            >
              <span
                className="w-2 h-2 rounded-full"
                style={{ backgroundColor: agRoleStyle.hex }}
              />
              <span className="hidden sm:inline">{ag.name.split('-')[0]}</span>
              {isDocked && <CheckCircle2 className="w-3 h-3 text-[#7DCE13]" />}
            </div>
          );
        })}
      </div>
    </div>
  );
};
