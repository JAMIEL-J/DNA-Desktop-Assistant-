import React, { useRef, useEffect } from 'react';
import { AgentProcess, AgentStatus, WindowTab } from '../../types';
import { AgentWindowHeader } from './AgentWindowHeader';
import { TerminalTab } from './TerminalTab';
import { TimelineTab } from './TimelineTab';
import { MemoryTab } from './MemoryTab';
import { FilesTab } from './FilesTab';
import { ConversationsTab } from './ConversationsTab';
import { ExecutionGraphTab } from './ExecutionGraphTab';
import { TransparencyTab } from './TransparencyTab';
import { MetricsTab } from './MetricsTab';
import { animateWindowSpawn } from '../../utils/gsapHelper';

interface AgentWindowContainerProps {
  agent: AgentProcess;
  onUpdateAgent: (updated: AgentProcess) => void;
  onClose: () => void;
  onSplitHorizontal: () => void;
  onSplitVertical: () => void;
  onClone: () => void;
  onExecuteDirective: (prompt: string) => void;
  onClearLogs: () => void;
}

export const AgentWindowContainer: React.FC<AgentWindowContainerProps> = ({
  agent,
  onUpdateAgent,
  onClose,
  onSplitHorizontal,
  onSplitVertical,
  onClone,
  onExecuteDirective,
  onClearLogs,
}) => {
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    animateWindowSpawn(containerRef.current);
  }, []);

  const handleTabChange = (tab: WindowTab) => {
    onUpdateAgent({ ...agent, activeTab: tab });
  };

  const handleStatusChange = (status: AgentStatus) => {
    onUpdateAgent({ ...agent, status });
  };

  const handleToggleMaximize = () => {
    onUpdateAgent({ ...agent, isMaximized: !agent.isMaximized });
  };

  const handleToggleMinimize = () => {
    onUpdateAgent({ ...agent, isMinimized: !agent.isMinimized });
  };

  const handleTogglePin = () => {
    onUpdateAgent({ ...agent, isPinned: !agent.isPinned });
  };

  const handleExportLogs = () => {
    const text = agent.logs.map((l) => `[${l.timestamp}] [${l.level.toUpperCase()}] ${l.message}`).join('\n');
    const blob = new Blob([text], { type: 'text/plain;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `${agent.name.toLowerCase()}_terminal_logs.log`;
    link.click();
    URL.revokeObjectURL(url);
  };

  if (agent.isMinimized) {
    return (
      <div className="bg-[#0b0b0e] border border-zinc-800 rounded p-2 flex items-center justify-between text-xs font-mono text-zinc-300">
        <div className="flex items-center gap-2">
          <span className="w-2 h-2 rounded-full" style={{ backgroundColor: agent.borderHex }}></span>
          <span className="font-bold">{agent.name}</span>
          <span className="text-zinc-500">[{agent.status}]</span>
        </div>
        <button
          onClick={handleToggleMinimize}
          className="text-zinc-400 hover:text-zinc-100 px-2 py-0.5 rounded bg-zinc-800 text-[10px]"
        >
          Restore
        </button>
      </div>
    );
  }

  return (
    <div
      ref={containerRef}
      className={`flex flex-col rounded-lg border overflow-hidden shadow-2xl transition-colors duration-200 ${
        agent.isMaximized ? 'fixed inset-2 z-50 bg-[#050507]' : 'h-full bg-[#050507]'
      }`}
      style={{
        borderColor: `${agent.borderHex}40`,
        boxShadow: `0 10px 30px -10px ${agent.borderHex}20`,
      }}
    >
      {/* Title Bar & Tabs */}
      <AgentWindowHeader
        agent={agent}
        onTabChange={handleTabChange}
        onStatusChange={handleStatusChange}
        onToggleMaximize={handleToggleMaximize}
        onToggleMinimize={handleToggleMinimize}
        onClose={onClose}
        onSplitHorizontal={onSplitHorizontal}
        onSplitVertical={onSplitVertical}
        onClone={onClone}
        onExportLogs={handleExportLogs}
        onTogglePin={handleTogglePin}
      />

      {/* Tab View Component Body */}
      <div className="flex-1 overflow-hidden relative">
        {agent.activeTab === 'Terminal' && (
          <TerminalTab
            agent={agent}
            onExecuteDirective={onExecuteDirective}
            onClearLogs={onClearLogs}
          />
        )}
        {agent.activeTab === 'Timeline' && <TimelineTab agent={agent} />}
        {agent.activeTab === 'Memory' && <MemoryTab agent={agent} />}
        {agent.activeTab === 'Files' && <FilesTab agent={agent} />}
        {agent.activeTab === 'Conversations' && <ConversationsTab agent={agent} />}
        {agent.activeTab === 'Execution Graph' && <ExecutionGraphTab agent={agent} />}
        {agent.activeTab === 'Transparency' && <TransparencyTab agent={agent} />}
        {agent.activeTab === 'Metrics' && <MetricsTab agent={agent} />}
      </div>
    </div>
  );
};
