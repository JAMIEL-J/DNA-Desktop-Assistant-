import React, { useState } from 'react';
import { Terminal, Send, ChevronUp, ChevronDown, Trash2, ShieldAlert, Cpu, Activity, Radio } from 'lucide-react';
import { GlobalEvent } from '../types';

interface BottomConsoleProps {
  events: GlobalEvent[];
  onBroadcastCommand: (cmd: string) => void;
  onClearEvents: () => void;
  isCollapsed: boolean;
  onToggleCollapse: () => void;
}

export const BottomConsole: React.FC<BottomConsoleProps> = ({
  events,
  onBroadcastCommand,
  onClearEvents,
  isCollapsed,
  onToggleCollapse,
}) => {
  const [broadcastInput, setBroadcastInput] = useState('');

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!broadcastInput.trim()) return;
    onBroadcastCommand(broadcastInput.trim());
    setBroadcastInput('');
  };

  if (isCollapsed) {
    return (
      <div className="h-7 bg-[#0B0B0B] border-t border-[#1A1A1A] px-3 flex items-center justify-between select-none font-mono text-xs z-30">
        <div className="flex items-center gap-2 text-[#555555] text-[11px]">
          <button
            onClick={onToggleCollapse}
            className="flex items-center gap-1 hover:text-[#D1D1D1] transition"
          >
            <ChevronUp className="w-3.5 h-3.5 text-[#B983FF]" />
            <Terminal className="w-3.5 h-3.5 text-[#555555]" />
            <span className="font-bold text-[#D1D1D1]">Global System Event Bus</span>
          </button>
          <span className="text-[#1A1A1A]">|</span>
          <span className="text-[#555555] text-[10px] truncate max-w-xl">
            Latest: {events[events.length - 1]?.message || 'All systems nominal'}
          </span>
        </div>

        <button
          onClick={onToggleCollapse}
          className="text-[#555555] hover:text-[#D1D1D1] text-[10px] flex items-center gap-1"
        >
          Expand Panel <ChevronUp className="w-3 h-3" />
        </button>
      </div>
    );
  }

  return (
    <div className="h-44 bg-[#050505] border-t border-[#1A1A1A] flex flex-col font-mono text-xs select-none z-30">
      {/* Console Header Bar */}
      <div className="h-7 bg-[#0B0B0B] border-b border-[#1A1A1A] px-3 flex items-center justify-between text-[11px] text-[#555555]">
        <div className="flex items-center gap-2">
          <Radio className="w-3.5 h-3.5 text-[#B983FF] animate-pulse" />
          <span className="font-bold text-[#D1D1D1]">Global Swarm Broadcast Console & Event Bus</span>
          <span className="text-[#1A1A1A]">|</span>
          <span>{events.length} system events</span>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={onClearEvents}
            className="flex items-center gap-1 hover:text-[#FF4B4B] transition text-[10px]"
          >
            <Trash2 className="w-3 h-3" /> Clear Bus
          </button>
          <button
            onClick={onToggleCollapse}
            className="p-1 hover:bg-[#1A1A1A] text-[#555555] hover:text-[#D1D1D1] rounded"
            title="Minimize Console"
          >
            <ChevronDown className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Events Stream Feed */}
      <div className="flex-1 overflow-y-auto p-2.5 space-y-1 bg-[#050505] select-text">
        {events.map((ev) => (
          <div key={ev.id} className="flex items-start gap-2 hover:bg-[#111111] px-1 py-0.5 rounded text-[11px]">
            <span className="text-[#555555] shrink-0">[{ev.timestamp}]</span>
            <span className="px-1 py-0.2 rounded text-[9px] font-bold uppercase bg-[#1A1A1A] text-[#B983FF] shrink-0">
              {ev.sourceAgent}
            </span>
            <span className={`break-all ${
              ev.level === 'warn' ? 'text-[#FF9F45]' :
              ev.level === 'error' ? 'text-[#FF4B4B] font-bold' :
              ev.level === 'broadcast' ? 'text-[#B983FF] font-semibold' :
              'text-[#D1D1D1]'
            }`}>
              {ev.message}
            </span>
          </div>
        ))}
      </div>

      {/* Broadcast Command Prompt Input */}
      <form onSubmit={handleSubmit} className="h-8 bg-[#0B0B0B] border-t border-[#1A1A1A] px-3 flex items-center gap-2">
        <span className="text-[#B983FF] font-bold">agentos-bus&gt;</span>
        <input
          type="text"
          value={broadcastInput}
          onChange={(e) => setBroadcastInput(e.target.value)}
          placeholder={`Broadcast command to all agents (e.g. 'pause all', 'status', 'restart all', 'sync memory')...`}
          className="flex-1 bg-transparent text-[#D1D1D1] placeholder-[#555555] focus:outline-none font-mono text-xs"
        />
        <button
          type="submit"
          className="p-1 text-[#B983FF] hover:text-[#D1D1D1] transition"
          title="Broadcast"
        >
          <Send className="w-3.5 h-3.5" />
        </button>
      </form>
    </div>
  );
};
