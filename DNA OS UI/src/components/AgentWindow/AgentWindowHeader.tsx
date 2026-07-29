import React from 'react';
import { 
  Play, 
  Pause, 
  RotateCcw, 
  Copy, 
  Maximize2, 
  Minimize2, 
  X, 
  Columns, 
  Rows, 
  Pin,
  FileText,
  Cpu,
  HardDrive
} from 'lucide-react';
import { AgentProcess, AgentStatus, WindowTab } from '../../types';
import { ROLE_COLORS } from '../../data/initialAgents';

interface AgentWindowHeaderProps {
  agent: AgentProcess;
  onTabChange: (tab: WindowTab) => void;
  onStatusChange: (status: AgentStatus) => void;
  onToggleMaximize: () => void;
  onToggleMinimize: () => void;
  onClose: () => void;
  onSplitHorizontal: () => void;
  onSplitVertical: () => void;
  onClone: () => void;
  onExportLogs: () => void;
  onTogglePin: () => void;
}

const PRIMARY_TABS: WindowTab[] = [
  'Terminal',
  'Memory',
  'Files',
  'Execution Graph',
  'Metrics',
];

export const AgentWindowHeader: React.FC<AgentWindowHeaderProps> = ({
  agent,
  onTabChange,
  onStatusChange,
  onToggleMaximize,
  onToggleMinimize,
  onClose,
  onSplitHorizontal,
  onSplitVertical,
  onClone,
  onExportLogs,
  onTogglePin,
}) => {
  const roleStyle = ROLE_COLORS[agent.role] || ROLE_COLORS.Developer;

  const getStatusBadge = (status: AgentStatus) => {
    switch (status) {
      case 'Running':
        return <span className="flex items-center gap-1 px-1.5 py-0.2 text-[9px] font-mono font-bold rounded bg-[#7DCE13]/10 text-[#7DCE13] border border-[#7DCE13]/30"><span className="w-1.5 h-1.5 rounded-full bg-[#7DCE13] animate-pulse"></span>RUNNING</span>;
      case 'Waiting':
        return <span className="flex items-center gap-1 px-1.5 py-0.2 text-[9px] font-mono font-bold rounded bg-[#FF9F45]/10 text-[#FF9F45] border border-[#FF9F45]/30"><span className="w-1.5 h-1.5 rounded-full bg-[#FF9F45]"></span>WAITING</span>;
      case 'Paused':
        return <span className="flex items-center gap-1 px-1.5 py-0.2 text-[9px] font-mono font-bold rounded bg-[#555555]/10 text-[#888888] border border-[#333333]"><span className="w-1.5 h-1.5 rounded-full bg-[#888888]"></span>PAUSED</span>;
      case 'Sleeping':
        return <span className="flex items-center gap-1 px-1.5 py-0.2 text-[9px] font-mono font-bold rounded bg-[#4D96FF]/10 text-[#4D96FF] border border-[#4D96FF]/30"><span className="w-1.5 h-1.5 rounded-full bg-[#4D96FF]"></span>SLEEPING</span>;
      case 'Failed':
      case 'Crashed':
        return <span className="flex items-center gap-1 px-1.5 py-0.2 text-[9px] font-mono font-bold rounded bg-[#FF4B4B]/10 text-[#FF4B4B] border border-[#FF4B4B]/30"><span className="w-1.5 h-1.5 rounded-full bg-[#FF4B4B]"></span>{status.toUpperCase()}</span>;
      default:
        return <span className="flex items-center gap-1 px-1.5 py-0.2 text-[9px] font-mono font-bold rounded bg-[#111111] text-[#888888] border border-[#1A1A1A]">{status}</span>;
    }
  };

  return (
    <div className="bg-[#0B0B0B] border-b border-[#1A1A1A] select-none font-sans">
      {/* Top Window Title Bar */}
      <div className="flex items-center justify-between px-2.5 py-1 gap-2 text-xs h-8">
        {/* Left Identity */}
        <div className="flex items-center gap-2 min-w-0">
          <div className="flex items-center gap-1.5">
            <span className="w-2 h-2 rounded-full inline-block shrink-0" style={{ backgroundColor: agent.borderHex }}></span>
            <span className="font-bold tracking-tight text-[#D1D1D1] text-[12px] truncate">{agent.name}</span>
            <span className={`px-1.5 py-0.2 text-[9px] font-semibold uppercase tracking-wider rounded border ${roleStyle.bg} ${roleStyle.text} ${roleStyle.border}`}>
              {agent.role}
            </span>
          </div>

          <div className="h-3 w-px bg-[#1A1A1A] hidden sm:block"></div>

          {getStatusBadge(agent.status)}

          {/* Compact Telemetry */}
          <div className="hidden xl:flex items-center gap-2.5 text-[10px] font-mono text-[#555555]">
            <span className="flex items-center gap-1">
              <Cpu className="w-3 h-3 text-[#555555]" />
              <span className="text-[#888888]">{agent.cpuUsagePercent}%</span>
            </span>
            <span className="flex items-center gap-1">
              <HardDrive className="w-3 h-3 text-[#555555]" />
              <span className="text-[#888888]">{agent.memoryUsageMb}M</span>
            </span>
          </div>
        </div>

        {/* Right Window Controls Bar */}
        <div className="flex items-center gap-0.5 shrink-0 text-[#666666]">
          {agent.status === 'Running' ? (
            <button
              onClick={() => onStatusChange('Paused')}
              title="Pause Agent Subroutine"
              className="w-6 h-6 flex items-center justify-center rounded hover:bg-[#1A1A1A] hover:text-[#FF9F45] transition"
            >
              <Pause className="w-3.5 h-3.5" />
            </button>
          ) : (
            <button
              onClick={() => onStatusChange('Running')}
              title="Resume Agent Subroutine"
              className="w-6 h-6 flex items-center justify-center rounded hover:bg-[#1A1A1A] hover:text-[#7DCE13] transition"
            >
              <Play className="w-3.5 h-3.5" />
            </button>
          )}

          <button
            onClick={() => onStatusChange('Restarting')}
            title="Restart Subroutine"
            className="w-6 h-6 flex items-center justify-center rounded hover:bg-[#1A1A1A] hover:text-[#4D96FF] transition"
          >
            <RotateCcw className="w-3.5 h-3.5" />
          </button>

          <button
            onClick={onClone}
            title="Clone Process Window"
            className="w-6 h-6 flex items-center justify-center rounded hover:bg-[#1A1A1A] hover:text-[#B983FF] transition"
          >
            <Copy className="w-3.5 h-3.5" />
          </button>

          <button
            onClick={onExportLogs}
            title="Export Terminal Logs"
            className="w-6 h-6 flex items-center justify-center rounded hover:bg-[#1A1A1A] hover:text-[#D1D1D1] transition"
          >
            <FileText className="w-3.5 h-3.5" />
          </button>

          <div className="h-3.5 w-px bg-[#1A1A1A] mx-1"></div>

          <button
            onClick={onSplitVertical}
            title="Split Pane Vertically"
            className="w-6 h-6 items-center justify-center rounded hover:bg-[#1A1A1A] hover:text-[#D1D1D1] transition hidden sm:flex"
          >
            <Columns className="w-3.5 h-3.5" />
          </button>

          <button
            onClick={onSplitHorizontal}
            title="Split Pane Horizontally"
            className="w-6 h-6 items-center justify-center rounded hover:bg-[#1A1A1A] hover:text-[#D1D1D1] transition hidden sm:flex"
          >
            <Rows className="w-3.5 h-3.5" />
          </button>

          <button
            onClick={onTogglePin}
            title={agent.isPinned ? "Unpin Window" : "Pin Window On Top"}
            className={`w-6 h-6 flex items-center justify-center rounded hover:bg-[#1A1A1A] transition ${agent.isPinned ? 'text-[#FF9F45] bg-[#FF9F45]/10' : 'hover:text-[#D1D1D1]'}`}
          >
            <Pin className="w-3.5 h-3.5" />
          </button>

          <div className="h-3.5 w-px bg-[#1A1A1A] mx-1"></div>

          <button
            onClick={onToggleMinimize}
            title="Minimize Window"
            className="w-6 h-6 flex items-center justify-center rounded hover:bg-[#1A1A1A] hover:text-[#D1D1D1] transition"
          >
            <Minimize2 className="w-3.5 h-3.5" />
          </button>

          <button
            onClick={onToggleMaximize}
            title={agent.isMaximized ? "Restore Window Size" : "Full Screen / Maximize Window"}
            className={`w-6 h-6 flex items-center justify-center rounded transition ${
              agent.isMaximized 
                ? 'bg-[#B983FF]/20 text-[#B983FF] border border-[#B983FF]/40' 
                : 'hover:bg-[#1A1A1A] hover:text-[#D1D1D1]'
            }`}
          >
            <Maximize2 className="w-3.5 h-3.5" />
          </button>

          <button
            onClick={onClose}
            title="Close & Terminate Process"
            className="w-6 h-6 flex items-center justify-center rounded hover:bg-[#FF4B4B]/20 hover:text-[#FF4B4B] transition"
          >
            <X className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>

      {/* Task & Tab Bar Unified Row */}
      <div className="flex items-center justify-between px-2.5 py-1 bg-[#050505] border-t border-[#1A1A1A] text-[11px] text-[#555555] h-7">
        <div className="flex items-center gap-1.5 truncate max-w-sm">
          <span className="text-[#444444] font-bold uppercase tracking-wider text-[9px]">TASK:</span>
          <span className="text-[#888888] font-medium truncate">{agent.activeTask}</span>
        </div>

        {/* Clean Minimal Tabs */}
        <div className="flex items-center gap-1">
          {PRIMARY_TABS.map((tab) => {
            const isActive = agent.activeTab === tab;
            return (
              <button
                key={tab}
                onClick={() => onTabChange(tab)}
                className={`px-2 py-0.5 text-[10px] font-sans font-medium transition rounded ${
                  isActive
                    ? 'bg-[#1A1A1A] text-[#B983FF] font-bold border border-[#333333]'
                    : 'text-[#555555] hover:text-[#D1D1D1] hover:bg-[#111111]'
                }`}
              >
                {tab}
              </button>
            );
          })}
        </div>
      </div>
    </div>
  );
};
