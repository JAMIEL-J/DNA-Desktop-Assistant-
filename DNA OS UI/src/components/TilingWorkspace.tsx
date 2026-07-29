import React from 'react';
import { AgentProcess, LayoutMode } from '../types';
import { AgentWindowContainer } from './AgentWindow/AgentWindowContainer';
import { NeuralGlobe } from './NeuralGlobe';
import { SwarmBootAnimation } from './SwarmBootAnimation';
import { Sparkles, X } from 'lucide-react';

interface TilingWorkspaceProps {
  agents: AgentProcess[];
  layoutMode: LayoutMode;
  isNeuralGlobeActive: boolean;
  isBootSequenceActive?: boolean;
  onToggleNeuralGlobe: () => void;
  onCompleteBootSequence?: () => void;
  onUpdateAgent: (agent: AgentProcess) => void;
  onCloseAgent: (id: string) => void;
  onSplitHorizontal: (id: string) => void;
  onSplitVertical: (id: string) => void;
  onCloneAgent: (id: string) => void;
  onExecuteDirective: (agentId: string, prompt: string) => void;
  onClearAgentLogs: (agentId: string) => void;
}

export const TilingWorkspace: React.FC<TilingWorkspaceProps> = ({
  agents,
  layoutMode,
  isNeuralGlobeActive,
  isBootSequenceActive,
  onToggleNeuralGlobe,
  onCompleteBootSequence,
  onUpdateAgent,
  onCloseAgent,
  onSplitHorizontal,
  onSplitVertical,
  onCloneAgent,
  onExecuteDirective,
  onClearAgentLogs,
}) => {
  if (agents.length === 0) {
    return (
      <div className="flex-1 bg-[#050505] flex flex-col items-center justify-center font-sans text-[#555555] p-6 text-center select-none relative">
        {/* Interactive Centerpiece Neural Globe */}
        <div className="mb-2 cursor-pointer hover:scale-105 transition-transform" onClick={onToggleNeuralGlobe} title="Click to Expand Full Workspace View">
          <NeuralGlobe width={320} height={320} />
        </div>
        <div className="text-xs font-bold text-[#D1D1D1] flex items-center gap-1.5">
          <Sparkles className="w-3.5 h-3.5 text-[#B983FF]" />
          <span>MATRIX NEURAL CORE ACTIVE</span>
        </div>
        <button
          onClick={onToggleNeuralGlobe}
          className="mt-2 px-3 py-1 bg-[#111111] hover:bg-[#1A1A1A] border border-[#1A1A1A] text-[#B983FF] hover:text-[#D1D1D1] rounded text-[11px] font-sans font-medium transition flex items-center gap-1.5"
        >
          <span>Expand Full Workspace Window</span>
        </button>
        <p className="text-[11px] text-[#555555] max-w-sm mt-2 font-sans">
          Move cursor or speak to interact with neural synapses. Click &quot;Spawn Agent&quot; or press <kbd className="px-1 py-0.2 bg-[#111111] border border-[#1A1A1A] rounded text-[#888888] font-mono">CTRL+SHIFT+P</kbd> to launch terminal processes.
        </p>
      </div>
    );
  }

  // Layout Grid Calculation
  const getLayoutGridClass = () => {
    switch (layoutMode) {
      case '2x2_GRID':
        return 'grid grid-cols-1 md:grid-cols-2 grid-rows-2 gap-2 h-full';
      case '3_COLUMN':
        return 'grid grid-cols-1 md:grid-cols-3 grid-rows-2 gap-2 h-full';
      case 'SPLIT_MAIN':
        return 'grid grid-cols-1 lg:grid-cols-3 gap-2 h-full';
      case 'SINGLE_FOCUS':
        return 'grid grid-cols-1 gap-2 h-full';
      default:
        return 'grid grid-cols-1 md:grid-cols-2 gap-2 h-full';
    }
  };

  return (
    <main
      className="flex-1 bg-[#050505] p-2 overflow-hidden relative select-none"
      style={{
        backgroundImage: 'radial-gradient(circle at 50% 50%, rgba(255,255,255,0.012) 1px, transparent 0)',
        backgroundSize: '20px 20px',
      }}
    >
      {/* 6-Agent Initial Boot/Response Animation Overlay */}
      {isBootSequenceActive && onCompleteBootSequence && (
        <SwarmBootAnimation agents={agents} onComplete={onCompleteBootSequence} />
      )}

      {/* Overlay Neural Globe Core Panel when activated - Expanded inside Workspace Window */}
      {isNeuralGlobeActive && (
        <div className="absolute inset-0 z-30 bg-[#050505]/95 backdrop-blur-2xl flex flex-col items-center justify-center overflow-hidden font-sans">
          {/* Top Control Bar */}
          <div className="absolute top-3 right-3 z-50 flex items-center gap-3">
            <div className="hidden sm:flex items-center gap-2 px-3 py-1 bg-[#0B0B0B] border border-[#1A1A1A] rounded-full text-[11px] text-[#B983FF] font-medium">
              <Sparkles className="w-3.5 h-3.5 animate-pulse" />
              <span>Full Workspace Neural Core</span>
            </div>

            <button
              onClick={onToggleNeuralGlobe}
              className="px-3 py-1.5 bg-[#111111] hover:bg-[#1A1A1A] border border-[#1A1A1A] text-[#888888] hover:text-[#D1D1D1] rounded-lg text-xs font-sans font-medium transition flex items-center gap-1.5 shadow-2xl"
              title="Close Workspace Expansion"
            >
              <X className="w-4 h-4 text-[#FF4B4B]" />
              <span>Close View</span>
            </button>
          </div>

          {/* Full Workspace Window Neural Globe Canvas */}
          <NeuralGlobe isFullScreen={true} />
        </div>
      )}

      <div className={`${getLayoutGridClass()} overflow-hidden`}>
        {agents.map((agent, idx) => {
          // In SPLIT_MAIN layout, first agent gets 2 cols, others get 1
          const flexColSpan =
            layoutMode === 'SPLIT_MAIN' && idx === 0 ? 'lg:col-span-2' : '';

          return (
            <div key={agent.id} className={`h-full min-h-[220px] overflow-hidden ${flexColSpan}`}>
              <AgentWindowContainer
                agent={agent}
                onUpdateAgent={onUpdateAgent}
                onClose={() => onCloseAgent(agent.id)}
                onSplitHorizontal={() => onSplitHorizontal(agent.id)}
                onSplitVertical={() => onSplitVertical(agent.id)}
                onClone={() => onCloneAgent(agent.id)}
                onExecuteDirective={(p) => onExecuteDirective(agent.id, p)}
                onClearLogs={() => onClearAgentLogs(agent.id)}
              />
            </div>
          );
        })}
      </div>
    </main>
  );
};
