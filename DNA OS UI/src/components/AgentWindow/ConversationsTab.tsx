import React, { useState } from 'react';
import { GitCommit, GitBranch, ChevronDown, ChevronRight, Hash, Terminal, Cpu } from 'lucide-react';
import { AgentProcess, GitCommitConversation } from '../../types';
import { ROLE_COLORS } from '../../data/initialAgents';

interface ConversationsTabProps {
  agent: AgentProcess;
}

export const ConversationsTab: React.FC<ConversationsTabProps> = ({ agent }) => {
  const [expandedCommits, setExpandedCommits] = useState<Record<string, boolean>>({});

  const toggleCommit = (hash: string) => {
    setExpandedCommits((prev) => ({ ...prev, [hash]: !prev[hash] }));
  };

  return (
    <div className="flex flex-col h-full bg-[#050507] text-zinc-300 font-mono text-xs overflow-hidden">
      {/* Git History Header */}
      <div className="p-3 bg-[#0a0a0d] border-b border-zinc-900 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <GitBranch className="w-4 h-4 text-emerald-400" />
          <span className="font-semibold text-zinc-200">Git Execution Commit History</span>
          <span className="text-[11px] text-zinc-500">(main branch - {agent.conversations.length} commits)</span>
        </div>
        <span className="text-[10px] text-zinc-500">Agent: {agent.name}</span>
      </div>

      {/* Commits List */}
      <div className="flex-1 overflow-y-auto p-3 space-y-3 bg-[#07070a]">
        {agent.conversations.map((commit) => {
          const isExpanded = !!expandedCommits[commit.commitHash];
          const roleStyle = ROLE_COLORS[commit.agentRole] || ROLE_COLORS.Developer;

          return (
            <div
              key={commit.commitHash}
              className="bg-[#0b0b0e] border border-zinc-900 rounded overflow-hidden hover:border-zinc-800 transition"
            >
              {/* Commit Summary Bar */}
              <div
                onClick={() => toggleCommit(commit.commitHash)}
                className="p-3 flex items-center justify-between gap-2 cursor-pointer hover:bg-zinc-900/40 select-none"
              >
                <div className="flex items-center gap-2 min-w-0">
                  <button className="text-zinc-500 hover:text-zinc-200">
                    {isExpanded ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
                  </button>
                  <span className="px-1.5 py-0.5 rounded bg-zinc-800 text-zinc-300 font-bold text-[11px] font-mono flex items-center gap-0.5 shrink-0">
                    <Hash className="w-3 h-3 text-emerald-400" /> {commit.commitHash}
                  </span>
                  <span className="font-medium text-zinc-100 text-xs truncate">{commit.summary}</span>
                </div>

                <div className="flex items-center gap-2 shrink-0 text-[10px] text-zinc-500">
                  <span className={`px-1.5 py-0.2 rounded uppercase ${roleStyle.bg} ${roleStyle.text} border ${roleStyle.border}`}>
                    {commit.author}
                  </span>
                  <span>{commit.timestamp}</span>
                </div>
              </div>

              {/* Expandable Reasoning & Diff Details */}
              {isExpanded && (
                <div className="p-3 bg-[#040406] border-t border-zinc-900 space-y-3 text-xs">
                  <div className="flex items-center justify-between text-[10px] text-zinc-500 pb-2 border-b border-zinc-900">
                    <span>Execution ID: <strong className="text-zinc-300">{commit.executionId}</strong></span>
                    {commit.parentHash && <span>Parent: <strong className="text-zinc-400">{commit.parentHash}</strong></span>}
                  </div>

                  <div>
                    <span className="text-[10px] uppercase text-zinc-500 font-bold">Reasoning Prompt</span>
                    <p className="mt-1 p-2 bg-[#09090c] rounded border border-zinc-900 text-zinc-300 leading-relaxed font-mono">
                      {commit.reasoningPrompt}
                    </p>
                  </div>

                  <div>
                    <span className="text-[10px] uppercase text-purple-400 font-bold">Expanded Reasoning Rationale</span>
                    <p className="mt-1 p-2 bg-[#09090c] rounded border border-zinc-900 text-zinc-300 leading-relaxed">
                      {commit.reasoningExplanation}
                    </p>
                  </div>

                  <div>
                    <span className="text-[10px] uppercase text-emerald-400 font-bold">Diff & Impact Summary</span>
                    <pre className="mt-1 p-2 bg-[#020204] rounded border border-zinc-900 text-emerald-400 font-mono text-[11px]">
                      {commit.diffSummary}
                    </pre>
                  </div>

                  {/* Input / Output Payloads */}
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-2 text-[11px]">
                    <div>
                      <span className="text-[10px] uppercase text-zinc-500 font-bold">Inputs</span>
                      <pre className="p-2 bg-[#020204] rounded border border-zinc-900 text-zinc-400 overflow-x-auto">
                        {JSON.stringify(commit.inputs, null, 2)}
                      </pre>
                    </div>
                    <div>
                      <span className="text-[10px] uppercase text-zinc-500 font-bold">Outputs</span>
                      <pre className="p-2 bg-[#020204] rounded border border-zinc-900 text-zinc-400 overflow-x-auto">
                        {JSON.stringify(commit.outputs, null, 2)}
                      </pre>
                    </div>
                  </div>
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
};
