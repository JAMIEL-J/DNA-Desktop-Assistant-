import React, { useState } from 'react';
import { Search, Terminal, Database, FileCode, GitCommit, X } from 'lucide-react';
import { AgentProcess } from '../types';

interface UniversalSearchModalProps {
  isOpen: boolean;
  onClose: () => void;
  agents: AgentProcess[];
  onSelectAgentTab: (agentId: string, tab: any) => void;
}

export const UniversalSearchModal: React.FC<UniversalSearchModalProps> = ({
  isOpen,
  onClose,
  agents,
  onSelectAgentTab,
}) => {
  const [query, setQuery] = useState('');

  if (!isOpen) return null;

  const results: {
    id: string;
    type: 'log' | 'memory' | 'file' | 'commit';
    agentName: string;
    agentId: string;
    title: string;
    snippet: string;
    tabTarget: string;
  }[] = [];

  if (query.trim().length >= 2) {
    const q = query.toLowerCase();

    agents.forEach((ag) => {
      // Logs
      ag.logs.forEach((log) => {
        if (log.message.toLowerCase().includes(q)) {
          results.push({
            id: `log-${log.id}`,
            type: 'log',
            agentName: ag.name,
            agentId: ag.id,
            title: `[${log.timestamp}] Terminal Log`,
            snippet: log.message,
            tabTarget: 'Terminal',
          });
        }
      });

      // Memory
      ag.memory.forEach((mem) => {
        if (mem.key.toLowerCase().includes(q) || mem.value.toLowerCase().includes(q)) {
          results.push({
            id: `mem-${mem.id}`,
            type: 'memory',
            agentName: ag.name,
            agentId: ag.id,
            title: `Memory Vector Key: ${mem.key}`,
            snippet: mem.value,
            tabTarget: 'Memory',
          });
        }
      });

      // Files
      ag.files.forEach((file) => {
        if (file.path.toLowerCase().includes(q) || file.content.toLowerCase().includes(q)) {
          results.push({
            id: `file-${file.id}`,
            type: 'file',
            agentName: ag.name,
            agentId: ag.id,
            title: `Code File: ${file.path}`,
            snippet: file.content.slice(0, 100),
            tabTarget: 'Files',
          });
        }
      });

      // Commits
      ag.conversations.forEach((commit) => {
        if (
          commit.summary.toLowerCase().includes(q) ||
          commit.reasoningExplanation.toLowerCase().includes(q)
        ) {
          results.push({
            id: `commit-${commit.commitHash}`,
            type: 'commit',
            agentName: ag.name,
            agentId: ag.id,
            title: `Git Commit [${commit.commitHash}]: ${commit.summary}`,
            snippet: commit.reasoningExplanation,
            tabTarget: 'Conversations',
          });
        }
      });
    });
  }

  return (
    <div className="fixed inset-0 bg-black/80 backdrop-blur-sm z-50 flex items-start justify-center pt-20 p-4 font-mono select-none">
      <div className="bg-[#0a0a0e] border border-zinc-800 rounded-lg w-full max-w-2xl shadow-2xl overflow-hidden flex flex-col">
        {/* Input Header */}
        <div className="p-3 bg-[#0d0d12] border-b border-zinc-800 flex items-center gap-2">
          <Search className="w-4 h-4 text-cyan-400 shrink-0" />
          <input
            type="text"
            placeholder="Universal search across all agent logs, vector memories, files, and git commits..."
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            className="flex-1 bg-transparent text-zinc-100 placeholder-zinc-500 focus:outline-none text-xs"
            autoFocus
          />
          <button onClick={onClose} className="p-1 text-zinc-500 hover:text-zinc-200">
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Results List */}
        <div className="max-h-96 overflow-y-auto p-3 space-y-2 bg-[#050507]">
          {query.trim().length < 2 ? (
            <div className="text-center text-zinc-600 py-12 text-xs">
              Type at least 2 characters to search across all agent processes...
            </div>
          ) : results.length > 0 ? (
            results.slice(0, 30).map((res) => (
              <div
                key={res.id}
                onClick={() => {
                  onSelectAgentTab(res.agentId, res.tabTarget);
                  onClose();
                }}
                className="p-2.5 bg-[#09090c] border border-zinc-900 rounded hover:border-cyan-500/50 cursor-pointer transition space-y-1"
              >
                <div className="flex items-center justify-between text-xs">
                  <div className="flex items-center gap-2">
                    {res.type === 'log' && <Terminal className="w-3.5 h-3.5 text-blue-400" />}
                    {res.type === 'memory' && <Database className="w-3.5 h-3.5 text-cyan-400" />}
                    {res.type === 'file' && <FileCode className="w-3.5 h-3.5 text-orange-400" />}
                    {res.type === 'commit' && <GitCommit className="w-3.5 h-3.5 text-emerald-400" />}
                    <span className="font-bold text-zinc-200">{res.title}</span>
                  </div>
                  <span className="text-[10px] text-purple-300 font-bold bg-purple-950/40 px-1.5 py-0.2 rounded border border-purple-500/30">
                    {res.agentName}
                  </span>
                </div>
                <p className="text-[11px] text-zinc-400 truncate">{res.snippet}</p>
              </div>
            ))
          ) : (
            <div className="text-center text-zinc-600 py-12 text-xs">
              No matching records found for query &quot;{query}&quot;
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
