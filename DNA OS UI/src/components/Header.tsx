import React, { useState, useEffect } from 'react';
import { 
  Terminal, 
  Search, 
  Plus, 
  LayoutGrid, 
  Cpu, 
  Clock, 
  ShieldCheck, 
  Maximize2, 
  Command, 
  RefreshCw,
  Sparkles,
  Zap,
  Users
} from 'lucide-react';
import { LayoutMode } from '../types';

interface HeaderProps {
  onOpenCommandPalette: () => void;
  onOpenUniversalSearch: () => void;
  onOpenNewAgentModal: () => void;
  currentLayout: LayoutMode;
  onChangeLayout: (layout: LayoutMode) => void;
  activeAgentsCount: number;
  totalAgentsCount: number;
  onResetWorkspace: () => void;
  onToggleNeuralGlobe: () => void;
  isNeuralGlobeActive: boolean;
  onTriggerBootSequence?: () => void;
  onOpenAvatarRoster?: () => void;
}

export const Header: React.FC<HeaderProps> = ({
  onOpenCommandPalette,
  onOpenUniversalSearch,
  onOpenNewAgentModal,
  currentLayout,
  onChangeLayout,
  activeAgentsCount,
  totalAgentsCount,
  onResetWorkspace,
  onToggleNeuralGlobe,
  isNeuralGlobeActive,
  onTriggerBootSequence,
  onOpenAvatarRoster,
}) => {
  const [timeString, setTimeString] = useState('');
  const [uptime, setUptime] = useState(84920);

  useEffect(() => {
    const update = () => {
      setTimeString(new Date().toLocaleTimeString('en-US', { hour12: false }));
      setUptime((u) => u + 1);
    };
    update();
    const timer = setInterval(update, 1000);
    return () => clearInterval(timer);
  }, []);

  const formatUptime = (sec: number) => {
    const hrs = Math.floor(sec / 3600);
    const mins = Math.floor((sec % 3600) / 60);
    return `${hrs}h ${mins}m`;
  };

  return (
    <header className="h-10 bg-[#0B0B0B] border-b border-[#1A1A1A] px-3 flex items-center justify-between select-none font-sans text-xs z-30">
      {/* Left: Branding & Kernel Specs */}
      <div className="flex items-center gap-3">
        <div className="flex items-center gap-2">
          <div className="w-5 h-5 rounded bg-gradient-to-br from-[#B983FF] to-[#4D96FF] flex items-center justify-center font-black text-black text-[11px] shadow-sm">
            M
          </div>
          <span className="font-bold text-xs tracking-tight text-[#D1D1D1] flex items-center gap-1.5 font-sans">
            MATRIX-OS <span className="text-[#555555] font-mono">//</span> <span className="text-[#B983FF] font-mono">KERNEL v4.2.0</span>
          </span>
        </div>

        <div className="h-3 w-px bg-[#1A1A1A] hidden sm:block"></div>

        {/* System Status Indicators */}
        <div className="hidden md:flex items-center gap-3 text-[10px] font-mono">
          <span className="flex items-center gap-1.5 text-[#7DCE13] font-semibold">
            <span className="w-2 h-2 rounded-full bg-[#7DCE13] animate-pulse"></span>
            SYSTEM SECURE
          </span>
          <span className="text-[#1A1A1A]">|</span>
          <span className="text-[#555555] flex items-center gap-1">
            <Zap className="w-3 h-3 text-[#FF9F45]" />
            SWARM: <strong className="text-[#D1D1D1]">{activeAgentsCount}/{totalAgentsCount} RUNNING</strong>
          </span>
        </div>
      </div>

      {/* Center: Command Palette Trigger & Universal Search */}
      <div className="flex items-center gap-2 max-w-md w-full mx-2">
        <button
          onClick={onOpenCommandPalette}
          className="flex-1 h-7 flex items-center justify-between bg-[#050505] hover:bg-[#111111] border border-[#1A1A1A] text-[#555555] hover:text-[#D1D1D1] px-3 rounded text-[11px] font-sans transition"
        >
          <div className="flex items-center gap-2">
            <Command className="w-3 h-3 text-[#B983FF]" />
            <span>Command Palette...</span>
          </div>
          <kbd className="text-[9px] font-mono bg-[#111111] border border-[#1A1A1A] px-1 py-0.2 rounded text-[#555555]">
            CTRL+SHIFT+P
          </kbd>
        </button>

        <button
          onClick={onOpenUniversalSearch}
          className="w-7 h-7 flex items-center justify-center bg-[#050505] hover:bg-[#111111] border border-[#1A1A1A] text-[#555555] hover:text-[#D1D1D1] rounded transition"
          title="Universal Search Logs & Memory"
        >
          <Search className="w-3.5 h-3.5" />
        </button>
      </div>

      {/* Right: Layout Preset Picker, Spawn Agent & Clock */}
      <div className="flex items-center gap-2">
        {/* Layout Mode Selector */}
        <div className="hidden lg:flex items-center bg-[#050505] border border-[#1A1A1A] rounded h-7 p-0.5 text-[10px] font-sans">
          <button
            onClick={() => onChangeLayout('2x2_GRID')}
            className={`px-2 h-full flex items-center justify-center rounded transition ${currentLayout === '2x2_GRID' ? 'bg-[#111111] text-[#B983FF] font-bold border border-[#1A1A1A]' : 'text-[#555555] hover:text-[#D1D1D1]'}`}
            title="2x2 Quad Grid"
          >
            2x2
          </button>
          <button
            onClick={() => onChangeLayout('3_COLUMN')}
            className={`px-2 h-full flex items-center justify-center rounded transition ${currentLayout === '3_COLUMN' ? 'bg-[#111111] text-[#B983FF] font-bold border border-[#1A1A1A]' : 'text-[#555555] hover:text-[#D1D1D1]'}`}
            title="3 Column Swarm"
          >
            3-Col
          </button>
          <button
            onClick={() => onChangeLayout('SPLIT_MAIN')}
            className={`px-2 h-full flex items-center justify-center rounded transition ${currentLayout === 'SPLIT_MAIN' ? 'bg-[#111111] text-[#B983FF] font-bold border border-[#1A1A1A]' : 'text-[#555555] hover:text-[#D1D1D1]'}`}
            title="Split Main Focus"
          >
            Split
          </button>
        </div>

        {/* Neural Globe Toggle Button */}
        <button
          onClick={onToggleNeuralGlobe}
          className={`h-7 flex items-center gap-1.5 px-2.5 rounded text-[11px] font-sans font-semibold border transition ${
            isNeuralGlobeActive
              ? 'bg-[#B983FF]/20 text-[#B983FF] border-[#B983FF]/60 shadow-[0_0_10px_rgba(185,131,255,0.25)]'
              : 'bg-[#050505] hover:bg-[#111111] text-[#555555] hover:text-[#D1D1D1] border-[#1A1A1A]'
          }`}
          title="Toggle Neural Core Globe (Voice & Cursor Interactive)"
        >
          <Sparkles className={`w-3 h-3 ${isNeuralGlobeActive ? 'text-[#B983FF] animate-pulse' : 'text-[#4D96FF]'}`} />
          <span className="hidden md:inline">Neural Core</span>
        </button>

        {/* Swarm Avatar Cards Roster Button */}
        {onOpenAvatarRoster && (
          <button
            onClick={onOpenAvatarRoster}
            className="h-7 flex items-center gap-1.5 px-2 bg-[#050505] hover:bg-[#111111] border border-[#1A1A1A] hover:border-[#B983FF]/50 text-[#888888] hover:text-[#D1D1D1] rounded text-[11px] transition"
            title="Inspect 6-Agent Avatar Cards"
          >
            <Users className="w-3.5 h-3.5 text-[#B983FF]" />
            <span className="hidden lg:inline">Avatar Cards</span>
          </button>
        )}

        {/* Trigger Swarm Initial Response Animation Sequence */}
        {onTriggerBootSequence && (
          <button
            onClick={onTriggerBootSequence}
            className="h-7 flex items-center gap-1 px-2 bg-[#050505] hover:bg-[#111111] border border-[#1A1A1A] text-[#888888] hover:text-[#B983FF] rounded text-[11px] transition"
            title="Replay Initial 6-Agent Swarm Response Sequence"
          >
            <Zap className="w-3 h-3 text-[#FF9F45]" />
            <span className="hidden xl:inline">Swarm Boot</span>
          </button>
        )}

        {/* Spawn Agent Button */}
        <button
          onClick={onOpenNewAgentModal}
          className="h-7 flex items-center gap-1 px-2.5 bg-[#B983FF]/15 hover:bg-[#B983FF]/25 border border-[#B983FF]/40 text-[#B983FF] font-sans font-semibold rounded text-[11px] transition"
        >
          <Plus className="w-3.5 h-3.5" />
          <span className="hidden sm:inline">Spawn Agent</span>
        </button>

        {/* Reset Workspace */}
        <button
          onClick={onResetWorkspace}
          className="w-7 h-7 flex items-center justify-center bg-[#050505] hover:bg-[#111111] border border-[#1A1A1A] text-[#555555] hover:text-[#D1D1D1] rounded transition"
          title="Reset Default Layout"
        >
          <RefreshCw className="w-3.5 h-3.5" />
        </button>

        {/* Clock & Uptime */}
        <div className="hidden xl:flex items-center gap-2 text-[10px] font-mono text-[#555555] bg-[#050505] border border-[#1A1A1A] px-2 h-7 rounded">
          <Clock className="w-3 h-3 text-[#4D96FF]" />
          <span className="text-[#D1D1D1]">{timeString}</span>
          <span className="text-[#1A1A1A]">|</span>
          <span>UP: {formatUptime(uptime)}</span>
        </div>
      </div>
    </header>
  );
};
