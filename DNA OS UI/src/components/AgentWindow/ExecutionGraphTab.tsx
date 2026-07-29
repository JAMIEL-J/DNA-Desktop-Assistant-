import React from 'react';
import { Network, ArrowRight, CheckCircle2, PlayCircle, Clock } from 'lucide-react';
import { AgentProcess } from '../../types';
import { ROLE_COLORS } from '../../data/initialAgents';

interface ExecutionGraphTabProps {
  agent: AgentProcess;
}

export const ExecutionGraphTab: React.FC<ExecutionGraphTabProps> = ({ agent }) => {
  return (
    <div className="flex flex-col h-full bg-[#050507] text-zinc-300 font-mono text-xs overflow-hidden">
      {/* Graph Header */}
      <div className="p-3 bg-[#0a0a0d] border-b border-zinc-900 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Network className="w-4 h-4 text-purple-400" />
          <span className="font-semibold text-zinc-200">Inter-Agent Execution DAG Graph</span>
        </div>
        <span className="text-[11px] text-zinc-500">
          Node Focus: <strong className="text-zinc-200">{agent.name}</strong>
        </span>
      </div>

      {/* Dependency Canvas Representation */}
      <div className="flex-1 p-6 overflow-auto bg-[#040406] flex items-center justify-center relative">
        <div className="flex flex-wrap items-center justify-center gap-6 max-w-3xl">
          {agent.dependencyNodes.map((node, index) => {
            const roleStyle = ROLE_COLORS[node.agentRole] || ROLE_COLORS.Developer;
            const isFocusNode = node.label === agent.name;

            return (
              <React.Fragment key={node.id}>
                {/* Node Box */}
                <div
                  className={`p-4 rounded-lg border flex flex-col gap-2 min-w-[200px] transition-all shadow-xl ${
                    isFocusNode
                      ? 'bg-[#0f0f15] border-purple-500 ring-2 ring-purple-500/30 text-zinc-100 scale-105'
                      : 'bg-[#09090c] border-zinc-800 text-zinc-400 hover:border-zinc-700'
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <span className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase ${roleStyle.bg} ${roleStyle.text} border ${roleStyle.border}`}>
                      {node.agentRole}
                    </span>
                    {node.status === 'completed' && <CheckCircle2 className="w-4 h-4 text-emerald-400" />}
                    {node.status === 'active' && <PlayCircle className="w-4 h-4 text-amber-400 animate-pulse" />}
                    {node.status === 'idle' && <Clock className="w-4 h-4 text-zinc-600" />}
                  </div>

                  <span className="font-bold text-sm text-zinc-100">{node.label}</span>

                  <div className="text-[10px] text-zinc-500 border-t border-zinc-800/80 pt-2 flex justify-between">
                    <span>Upstream: {node.upstreamIds.length}</span>
                    <span>Downstream: {node.downstreamIds.length}</span>
                  </div>
                </div>

                {/* Arrow Connector */}
                {index < agent.dependencyNodes.length - 1 && (
                  <div className="flex items-center text-zinc-600">
                    <ArrowRight className="w-5 h-5 text-purple-400/80 animate-pulse" />
                  </div>
                )}
              </React.Fragment>
            );
          })}
        </div>
      </div>
    </div>
  );
};
