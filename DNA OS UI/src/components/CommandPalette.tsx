import React, { useState, useEffect, useRef } from 'react';
import { Command, Terminal, Plus, Play, Pause, RefreshCw, LayoutGrid, Search, X } from 'lucide-react';
import { AgentProcess, LayoutMode } from '../types';

interface CommandPaletteProps {
  isOpen: boolean;
  onClose: () => void;
  agents: AgentProcess[];
  onSelectAgent: (id: string) => void;
  onOpenNewAgentModal: () => void;
  onChangeLayout: (layout: LayoutMode) => void;
  onPauseAll: () => void;
  onResumeAll: () => void;
  onResetWorkspace: () => void;
}

export const CommandPalette: React.FC<CommandPaletteProps> = ({
  isOpen,
  onClose,
  agents,
  onSelectAgent,
  onOpenNewAgentModal,
  onChangeLayout,
  onPauseAll,
  onResumeAll,
  onResetWorkspace,
}) => {
  const [query, setQuery] = useState('');
  const [selectedIndex, setSelectedIndex] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (isOpen) {
      setTimeout(() => inputRef.current?.focus(), 50);
    }
  }, [isOpen]);

  if (!isOpen) return null;

  const actions = [
    {
      id: 'cmd-spawn',
      title: 'Spawn New AI Agent Process',
      category: 'Actions',
      icon: <Plus className="w-4 h-4 text-purple-400" />,
      handler: () => {
        onOpenNewAgentModal();
        onClose();
      },
    },
    {
      id: 'cmd-pause-all',
      title: 'Pause All Agent Terminals',
      category: 'Controls',
      icon: <Pause className="w-4 h-4 text-amber-400" />,
      handler: () => {
        onPauseAll();
        onClose();
      },
    },
    {
      id: 'cmd-resume-all',
      title: 'Resume All Agent Terminals',
      category: 'Controls',
      icon: <Play className="w-4 h-4 text-emerald-400" />,
      handler: () => {
        onResumeAll();
        onClose();
      },
    },
    {
      id: 'cmd-layout-2x2',
      title: 'Switch Layout: 2x2 Quad Grid',
      category: 'Layouts',
      icon: <LayoutGrid className="w-4 h-4 text-blue-400" />,
      handler: () => {
        onChangeLayout('2x2_GRID');
        onClose();
      },
    },
    {
      id: 'cmd-layout-3col',
      title: 'Switch Layout: 3-Column Swarm',
      category: 'Layouts',
      icon: <LayoutGrid className="w-4 h-4 text-cyan-400" />,
      handler: () => {
        onChangeLayout('3_COLUMN');
        onClose();
      },
    },
    {
      id: 'cmd-reset',
      title: 'Reset Default Workspace Tiling',
      category: 'System',
      icon: <RefreshCw className="w-4 h-4 text-red-400" />,
      handler: () => {
        onResetWorkspace();
        onClose();
      },
    },
    ...agents.map((ag) => ({
      id: `agent-focus-${ag.id}`,
      title: `Focus Agent Terminal: ${ag.name} (${ag.role})`,
      category: 'Agents',
      icon: <Terminal className="w-4 h-4 text-purple-400" />,
      handler: () => {
        onSelectAgent(ag.id);
        onClose();
      },
    })),
  ];

  const filtered = actions.filter((a) =>
    a.title.toLowerCase().includes(query.toLowerCase()) ||
    a.category.toLowerCase().includes(query.toLowerCase())
  );

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'ArrowDown') {
      e.preventDefault();
      setSelectedIndex((prev) => (prev + 1) % Math.max(1, filtered.length));
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      setSelectedIndex((prev) => (prev - 1 + filtered.length) % Math.max(1, filtered.length));
    } else if (e.key === 'Enter') {
      e.preventDefault();
      if (filtered[selectedIndex]) {
        filtered[selectedIndex].handler();
      }
    } else if (e.key === 'Escape') {
      onClose();
    }
  };

  return (
    <div className="fixed inset-0 bg-black/80 backdrop-blur-sm z-50 flex items-start justify-center pt-20 p-4 font-mono select-none">
      <div className="bg-[#0a0a0e] border border-zinc-800 rounded-lg w-full max-w-xl shadow-2xl overflow-hidden flex flex-col">
        {/* Input Header */}
        <div className="p-3 bg-[#0d0d12] border-b border-zinc-800 flex items-center gap-2">
          <Command className="w-4 h-4 text-purple-400 shrink-0" />
          <input
            ref={inputRef}
            type="text"
            placeholder="Type a command or search agent processes..."
            value={query}
            onChange={(e) => {
              setQuery(e.target.value);
              setSelectedIndex(0);
            }}
            onKeyDown={handleKeyDown}
            className="flex-1 bg-transparent text-zinc-100 placeholder-zinc-500 focus:outline-none text-xs"
          />
          <button onClick={onClose} className="p-1 text-zinc-500 hover:text-zinc-200">
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Filtered Action List */}
        <div className="max-h-80 overflow-y-auto p-2 space-y-1">
          {filtered.length > 0 ? (
            filtered.map((item, idx) => {
              const isSelected = idx === selectedIndex;
              return (
                <div
                  key={item.id}
                  onClick={item.handler}
                  onMouseEnter={() => setSelectedIndex(idx)}
                  className={`p-2.5 rounded border transition cursor-pointer flex items-center justify-between text-xs ${
                    isSelected
                      ? 'bg-purple-950/40 border-purple-500/60 text-zinc-100 font-bold'
                      : 'bg-[#060608] border-zinc-900 text-zinc-400 hover:border-zinc-800'
                  }`}
                >
                  <div className="flex items-center gap-2">
                    {item.icon}
                    <span>{item.title}</span>
                  </div>
                  <span className="text-[10px] text-zinc-500 uppercase px-1.5 py-0.2 bg-zinc-800 rounded">
                    {item.category}
                  </span>
                </div>
              );
            })
          ) : (
            <div className="text-center text-zinc-600 py-8 text-xs">No matching actions found</div>
          )}
        </div>

        {/* Footer Navigation Hints */}
        <div className="p-2 bg-[#060608] border-t border-zinc-800/80 text-[10px] text-zinc-500 flex justify-between">
          <span>
            Use <kbd className="px-1 bg-zinc-800 rounded">↑</kbd>{' '}
            <kbd className="px-1 bg-zinc-800 rounded">↓</kbd> to navigate
          </span>
          <span>
            Press <kbd className="px-1 bg-zinc-800 rounded">Enter</kbd> to execute
          </span>
        </div>
      </div>
    </div>
  );
};
