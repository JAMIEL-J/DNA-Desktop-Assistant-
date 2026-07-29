import React, { useState } from 'react';
import { 
  FolderTree, 
  Terminal, 
  Bookmark, 
  Layers, 
  FileCode, 
  Pin, 
  ChevronRight, 
  ChevronDown, 
  Activity, 
  ShieldCheck, 
  Play, 
  Pause, 
  Plus, 
  SlidersHorizontal,
  Compass,
  LayoutGrid
} from 'lucide-react';
import { AgentProcess, WorkspacePreset } from '../types';
import { ROLE_COLORS, INITIAL_PRESETS } from '../data/initialAgents';

interface LeftSidebarProps {
  agents: AgentProcess[];
  focusedAgentId: string | null;
  onSelectAgent: (id: string) => void;
  onTogglePinAgent: (id: string) => void;
  onApplyPreset: (preset: WorkspacePreset) => void;
  onOpenNewAgentModal: () => void;
  isCollapsed: boolean;
  onToggleCollapse: () => void;
}

export const LeftSidebar: React.FC<LeftSidebarProps> = ({
  agents,
  focusedAgentId,
  onSelectAgent,
  onTogglePinAgent,
  onApplyPreset,
  onOpenNewAgentModal,
  isCollapsed,
  onToggleCollapse,
}) => {
  const [activeTab, setActiveTab] = useState<'agents' | 'presets' | 'files' | 'mission'>('agents');
  const [expandedSection, setExpandedSection] = useState<Record<string, boolean>>({
    mission: true,
    agents: true,
    presets: true,
    files: true,
  });

  const toggleSection = (sec: string) => {
    setExpandedSection((prev) => ({ ...prev, [sec]: !prev[sec] }));
  };

  if (isCollapsed) {
    return (
      <aside className="w-10 bg-[#080808] border-r border-[#1A1A1A] flex flex-col items-center py-2 space-y-3 select-none text-[#555555]">
        <button
          onClick={onToggleCollapse}
          className="p-1.5 hover:bg-[#1A1A1A] text-[#D1D1D1] rounded transition"
          title="Expand Sidebar"
        >
          <ChevronRight className="w-4 h-4" />
        </button>

        <div className="w-6 h-px bg-[#1A1A1A] my-1"></div>

        {agents.map((ag) => (
          <button
            key={ag.id}
            onClick={() => onSelectAgent(ag.id)}
            className={`w-6 h-6 rounded flex items-center justify-center font-mono font-bold text-[10px] transition border ${
              focusedAgentId === ag.id ? 'border-[#B983FF] bg-[#B983FF]/20 text-[#B983FF]' : 'border-[#1A1A1A] hover:border-[#333333] text-[#555555]'
            }`}
            title={`${ag.name} (${ag.role})`}
            style={{ color: ag.borderHex }}
          >
            {ag.name.slice(0, 2).toUpperCase()}
          </button>
        ))}
      </aside>
    );
  }

  return (
    <aside className="w-64 bg-[#080808] border-r border-[#1A1A1A] flex flex-col h-full select-none font-mono text-xs z-20">
      {/* Sidebar Header Navigation Tabs */}
      <div className="flex items-center justify-between p-2 border-b border-[#1A1A1A] bg-[#0B0B0B]">
        <div className="flex items-center gap-1">
          <button
            onClick={() => setActiveTab('agents')}
            className={`px-2 py-1 rounded text-[11px] font-medium transition ${
              activeTab === 'agents' ? 'bg-[#1A1A1A] text-[#D1D1D1] border border-[#333333]' : 'text-[#555555] hover:text-[#D1D1D1]'
            }`}
          >
            Agents ({agents.length})
          </button>
          <button
            onClick={() => setActiveTab('presets')}
            className={`px-2 py-1 rounded text-[11px] font-medium transition ${
              activeTab === 'presets' ? 'bg-[#1A1A1A] text-[#D1D1D1] border border-[#333333]' : 'text-[#555555] hover:text-[#D1D1D1]'
            }`}
          >
            Presets
          </button>
          <button
            onClick={() => setActiveTab('files')}
            className={`px-2 py-1 rounded text-[11px] font-medium transition ${
              activeTab === 'files' ? 'bg-[#1A1A1A] text-[#D1D1D1] border border-[#333333]' : 'text-[#555555] hover:text-[#D1D1D1]'
            }`}
          >
            Workspace
          </button>
        </div>

        <button
          onClick={onToggleCollapse}
          className="p-1 hover:bg-[#1A1A1A] text-[#555555] hover:text-[#D1D1D1] rounded"
          title="Collapse Sidebar"
        >
          <SlidersHorizontal className="w-3.5 h-3.5" />
        </button>
      </div>

      {/* Main Content Area */}
      <div className="flex-1 overflow-y-auto p-2 space-y-4">
        {activeTab === 'agents' && (
          <div className="space-y-3">
            {/* Mission Explorer Section */}
            <div>
              <button
                onClick={() => toggleSection('mission')}
                className="w-full flex items-center justify-between text-[11px] font-bold text-zinc-400 hover:text-zinc-200 py-1"
              >
                <div className="flex items-center gap-1.5">
                  <Compass className="w-3.5 h-3.5 text-purple-400" />
                  <span className="uppercase tracking-wider text-[10px]">Active Swarm Mission</span>
                </div>
                {expandedSection.mission ? <ChevronDown className="w-3 h-3" /> : <ChevronRight className="w-3 h-3" />}
              </button>

              {expandedSection.mission && (
                <div className="mt-1 p-2 bg-[#0a0a0d] border border-zinc-900 rounded space-y-1.5">
                  <span className="font-bold text-zinc-200 text-[11px]">Mission #9012: Raft Consensus Engine</span>
                  <p className="text-[10px] text-zinc-400 leading-normal">
                    Autonomous cluster implementation, chaos fuzzing, and latency benchmarking.
                  </p>
                  <div className="flex items-center justify-between pt-1 text-[10px] text-zinc-500 border-t border-zinc-900">
                    <span>Target: x86_64 Rust Daemon</span>
                    <span className="text-emerald-400 font-bold">96.8% COMPLETE</span>
                  </div>
                </div>
              )}
            </div>

            {/* Running Agents List */}
            <div>
              <div className="flex items-center justify-between py-1">
                <button
                  onClick={() => toggleSection('agents')}
                  className="flex items-center gap-1.5 text-[10px] uppercase font-bold text-zinc-400 hover:text-zinc-200 tracking-wider"
                >
                  <Terminal className="w-3.5 h-3.5 text-blue-400" />
                  <span>Running Terminal Processes</span>
                </button>
                <button
                  onClick={onOpenNewAgentModal}
                  className="p-1 hover:bg-zinc-800 text-purple-400 rounded"
                  title="Spawn Agent"
                >
                  <Plus className="w-3.5 h-3.5" />
                </button>
              </div>

              {expandedSection.agents && (
                <div className="space-y-1 mt-1">
                  {agents.map((agent) => {
                    const isFocused = focusedAgentId === agent.id;
                    const roleStyle = ROLE_COLORS[agent.role] || ROLE_COLORS.Developer;

                    return (
                      <div
                        key={agent.id}
                        onClick={() => onSelectAgent(agent.id)}
                        className={`p-2 rounded border transition cursor-pointer flex items-center justify-between ${
                          isFocused
                            ? 'bg-purple-950/30 border-purple-500/60 text-zinc-100 font-medium'
                            : 'bg-[#09090c] border-zinc-900/80 text-zinc-400 hover:border-zinc-800 hover:text-zinc-200'
                        }`}
                      >
                        <div className="flex items-center gap-2 truncate">
                          <span className="w-2 h-2 rounded-full shrink-0" style={{ backgroundColor: agent.borderHex }}></span>
                          <div className="truncate">
                            <div className="flex items-center gap-1.5">
                              <span className="font-bold text-xs truncate">{agent.name}</span>
                              <span className={`px-1 text-[9px] uppercase rounded ${roleStyle.bg} ${roleStyle.text}`}>
                                {agent.role}
                              </span>
                            </div>
                            <span className="text-[10px] text-zinc-500 truncate block">
                              CPU {agent.cpuUsagePercent}% | {agent.memoryUsageMb}MB
                            </span>
                          </div>
                        </div>

                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            onTogglePinAgent(agent.id);
                          }}
                          className={`p-1 hover:bg-zinc-800 rounded text-zinc-500 ${agent.isPinned ? 'text-amber-400' : ''}`}
                          title="Pin Agent Window"
                        >
                          <Pin className="w-3 h-3" />
                        </button>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          </div>
        )}

        {activeTab === 'presets' && (
          <div className="space-y-2">
            <span className="text-[10px] uppercase font-bold text-zinc-500 tracking-wider">
              Workspace Preset Layouts
            </span>
            {INITIAL_PRESETS.map((preset) => (
              <div
                key={preset.id}
                onClick={() => onApplyPreset(preset)}
                className="p-2.5 bg-[#09090c] border border-zinc-900 rounded hover:border-purple-500/50 cursor-pointer transition space-y-1"
              >
                <div className="flex items-center justify-between">
                  <span className="font-bold text-zinc-200 text-xs">{preset.name}</span>
                  <span className="text-[10px] px-1.5 py-0.2 bg-zinc-800 text-purple-300 rounded">
                    {preset.layout}
                  </span>
                </div>
                <p className="text-[10px] text-zinc-400">{preset.description}</p>
              </div>
            ))}
          </div>
        )}

        {activeTab === 'files' && (
          <div className="space-y-2">
            <span className="text-[10px] uppercase font-bold text-zinc-500 tracking-wider">
              Root Project File Tree
            </span>
            <div className="p-2 bg-[#09090c] border border-zinc-900 rounded space-y-1 font-mono text-[11px] text-zinc-300">
              <div className="flex items-center gap-1.5 text-amber-400 font-bold">
                <FolderTree className="w-3.5 h-3.5" /> /workspace/
              </div>
              <div className="pl-3 space-y-1 text-zinc-400 border-l border-zinc-800 ml-1">
                <div>📁 dev/raft_engine/src/node.rs</div>
                <div>📁 research/consensus_paper_matrix.json</div>
                <div>📁 planner/task_dag.yaml</div>
                <div>📁 qa/chaos_test_report.json</div>
                <div>📁 docs/RAFT_ARCHITECTURE.md</div>
                <div>📁 analyst/benchmark_telemetry.csv</div>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Footer System Audit Note */}
      <div className="p-2 border-t border-zinc-800/80 bg-[#050507] text-[10px] text-zinc-500 flex items-center justify-between">
        <span className="flex items-center gap-1">
          <ShieldCheck className="w-3 h-3 text-emerald-400" /> AUDIT LOG: SECURE
        </span>
        <span>PID 8000</span>
      </div>
    </aside>
  );
};
