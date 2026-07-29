import React, { useState, useEffect, useRef } from 'react';
import { Terminal, Send, ArrowDown, Copy, Check, Trash2 } from 'lucide-react';
import { AgentProcess, LogEntry } from '../../types';

interface TerminalTabProps {
  agent: AgentProcess;
  onExecuteDirective: (prompt: string) => void;
  onClearLogs: () => void;
}

export const TerminalTab: React.FC<TerminalTabProps> = ({
  agent,
  onExecuteDirective,
  onClearLogs,
}) => {
  const [commandInput, setCommandInput] = useState('');
  const [copied, setCopied] = useState(false);
  const [autoScroll, setAutoScroll] = useState(true);
  const terminalEndRef = useRef<HTMLDivElement>(null);
  const terminalContainerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (autoScroll) {
      terminalEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }
  }, [agent.logs, autoScroll]);

  const handleScroll = () => {
    if (!terminalContainerRef.current) return;
    const { scrollTop, scrollHeight, clientHeight } = terminalContainerRef.current;
    const isAtBottom = scrollHeight - scrollTop - clientHeight < 40;
    setAutoScroll(isAtBottom);
  };

  const handleFormSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!commandInput.trim()) return;
    const cmd = commandInput.trim();
    if (cmd.toLowerCase() === 'clear') {
      onClearLogs();
    } else {
      onExecuteDirective(cmd);
    }
    setCommandInput('');
  };

  const handleCopyLogs = () => {
    const fullLogText = agent.logs.map((l) => `[${l.timestamp}] ${l.message}`).join('\n');
    navigator.clipboard.writeText(fullLogText);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const getLogLevelClass = (level: LogEntry['level']) => {
    switch (level) {
      case 'success':
        return 'text-[#7DCE13]';
      case 'warn':
        return 'text-[#FF9F45]';
      case 'error':
        return 'text-[#FF4B4B] font-bold';
      case 'debug':
        return 'text-[#B983FF]';
      case 'system':
        return 'text-[#4D96FF] font-medium';
      default:
        return 'text-[#D1D1D1]';
    }
  };

  return (
    <div className="flex flex-col h-full bg-[#050505] text-[#D1D1D1] font-mono text-xs select-text relative">
      {/* Terminal Bar */}
      <div className="flex items-center justify-between px-2.5 py-1 bg-[#0B0B0B] border-b border-[#1A1A1A] text-[10px] text-[#555555]">
        <div className="flex items-center gap-1.5">
          <Terminal className="w-3 h-3 text-[#B983FF]" />
          <span className="text-[#D1D1D1]">bash - {agent.name.toLowerCase()}@matrix:~</span>
          <span className="text-[#1A1A1A]">|</span>
          <span>{agent.logs.length} lines</span>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={handleCopyLogs}
            className="flex items-center gap-1 hover:text-[#D1D1D1] transition text-[10px]"
            title="Copy Logs"
          >
            {copied ? <Check className="w-3 h-3 text-[#7DCE13]" /> : <Copy className="w-3 h-3" />}
            <span>{copied ? 'Copied' : 'Copy'}</span>
          </button>
          <button
            onClick={onClearLogs}
            className="flex items-center gap-1 hover:text-[#FF4B4B] transition text-[10px]"
            title="Clear Terminal"
          >
            <Trash2 className="w-3 h-3" />
            <span>Clear</span>
          </button>
        </div>
      </div>

      {/* Terminal Stream Area */}
      <div
        ref={terminalContainerRef}
        onScroll={handleScroll}
        className="flex-1 overflow-y-auto p-2.5 space-y-1 font-mono leading-relaxed bg-[#050505]"
      >
        <div className="text-[#555555] pb-1.5 border-b border-[#1A1A1A] mb-1.5 text-[10px]">
          Process PID [{agent.pid}] initialized for task: {agent.activeTask}
        </div>

        {agent.logs.map((log) => (
          <div key={log.id} className="flex items-start gap-2 hover:bg-[#111111] px-1 py-0.2 rounded text-[11px]">
            <span className="text-[#555555] shrink-0 text-[10px]">[{log.timestamp}]</span>
            <span className={`break-all ${getLogLevelClass(log.level)}`}>
              {log.message}
            </span>
          </div>
        ))}

        {/* Live streaming cursor */}
        {agent.status === 'Running' && (
          <div className="flex items-center gap-2 text-[#555555] pt-0.5">
            <span className="w-1.5 h-3.5 bg-[#B983FF] animate-pulse inline-block"></span>
            <span className="text-[9px] uppercase tracking-widest text-[#555555]">Awaiting directive...</span>
          </div>
        )}

        <div ref={terminalEndRef} />
      </div>

      {!autoScroll && (
        <button
          onClick={() => {
            setAutoScroll(true);
            terminalEndRef.current?.scrollIntoView({ behavior: 'smooth' });
          }}
          className="absolute bottom-10 right-3 bg-[#111111] text-[#D1D1D1] border border-[#1A1A1A] px-2 py-0.5 rounded text-[10px] flex items-center gap-1 shadow-md hover:bg-[#1A1A1A]"
        >
          <ArrowDown className="w-3 h-3" /> Bottom
        </button>
      )}

      {/* Directives Input Prompt */}
      <form onSubmit={handleFormSubmit} className="flex items-center bg-[#0B0B0B] border-t border-[#1A1A1A] px-2.5 py-1 gap-2">
        <span className="text-[#B983FF] font-bold text-[11px]">$</span>
        <input
          type="text"
          value={commandInput}
          onChange={(e) => setCommandInput(e.target.value)}
          placeholder={`Execute directive (e.g., 'scan code', 'clear')...`}
          className="flex-1 bg-transparent text-[#D1D1D1] placeholder-[#555555] focus:outline-none font-mono text-xs"
        />
        <button
          type="submit"
          className="p-1 text-[#555555] hover:text-[#7DCE13] transition"
          title="Execute Directive"
        >
          <Send className="w-3 h-3" />
        </button>
      </form>
    </div>
  );
};
