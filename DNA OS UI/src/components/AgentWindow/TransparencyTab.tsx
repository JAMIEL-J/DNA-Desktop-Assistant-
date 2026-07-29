import React from 'react';
import { ShieldCheck, HelpCircle, CheckCircle, Cpu, Zap, Layers, AlertCircle, FileText } from 'lucide-react';
import { AgentProcess } from '../../types';

interface TransparencyTabProps {
  agent: AgentProcess;
}

export const TransparencyTab: React.FC<TransparencyTabProps> = ({ agent }) => {
  const { transparency } = agent;

  return (
    <div className="flex flex-col h-full bg-[#050507] text-zinc-300 font-mono text-xs overflow-hidden">
      {/* Transparency Header */}
      <div className="p-3 bg-[#0a0a0d] border-b border-zinc-900 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <ShieldCheck className="w-4 h-4 text-emerald-400" />
          <span className="font-semibold text-zinc-200">Autonomous Reasoning & Audit Transparency Matrix</span>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-[10px] text-emerald-400 bg-emerald-950/40 border border-emerald-500/30 px-2 py-0.5 rounded font-bold">
            Confidence Score: {transparency.confidenceScore}%
          </span>
        </div>
      </div>

      {/* Main Audit Grid */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4 bg-[#07070a]">
        {/* Top Metric Cards */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          <div className="p-3 bg-[#0b0b0e] border border-zinc-900 rounded space-y-1">
            <span className="text-[10px] uppercase text-zinc-500 font-bold">Execution Duration</span>
            <div className="text-sm font-bold text-zinc-100">{transparency.executionDurationMs} ms</div>
          </div>
          <div className="p-3 bg-[#0b0b0e] border border-zinc-900 rounded space-y-1">
            <span className="text-[10px] uppercase text-zinc-500 font-bold">AI Model Kernel</span>
            <div className="text-sm font-bold text-purple-400 truncate">{transparency.modelUsed}</div>
          </div>
          <div className="p-3 bg-[#0b0b0e] border border-zinc-900 rounded space-y-1">
            <span className="text-[10px] uppercase text-zinc-500 font-bold">Tokens Consumed</span>
            <div className="text-sm font-bold text-amber-400">{transparency.tokensConsumed.toLocaleString()}</div>
          </div>
          <div className="p-3 bg-[#0b0b0e] border border-zinc-900 rounded space-y-1">
            <span className="text-[10px] uppercase text-zinc-500 font-bold">Audit Verification</span>
            <div className="text-sm font-bold text-emerald-400 flex items-center gap-1">
              <CheckCircle className="w-3.5 h-3.5" /> PASSED
            </div>
          </div>
        </div>

        {/* What Happened / Why It Happened */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          <div className="p-3.5 bg-[#0b0b0e] border border-zinc-900 rounded space-y-1.5">
            <div className="flex items-center gap-2 text-zinc-200 font-bold text-xs">
              <FileText className="w-4 h-4 text-blue-400" />
              <span>What Happened</span>
            </div>
            <p className="text-xs text-zinc-300 leading-relaxed bg-[#050507] p-2.5 rounded border border-zinc-900">
              {transparency.whatHappened}
            </p>
          </div>

          <div className="p-3.5 bg-[#0b0b0e] border border-zinc-900 rounded space-y-1.5">
            <div className="flex items-center gap-2 text-zinc-200 font-bold text-xs">
              <HelpCircle className="w-4 h-4 text-purple-400" />
              <span>Why It Happened</span>
            </div>
            <p className="text-xs text-zinc-300 leading-relaxed bg-[#050507] p-2.5 rounded border border-zinc-900">
              {transparency.whyItHappened}
            </p>
          </div>
        </div>

        {/* Reasoning Summary Checklist */}
        <div className="p-3.5 bg-[#0b0b0e] border border-zinc-900 rounded space-y-2">
          <span className="text-xs font-bold text-zinc-200 flex items-center gap-2">
            <Zap className="w-4 h-4 text-amber-400" /> Reasoning Step Breakdown
          </span>
          <div className="space-y-1.5">
            {transparency.reasoningSummary.map((step, idx) => (
              <div key={idx} className="flex items-start gap-2 text-xs text-zinc-300 bg-[#050507] p-2 rounded border border-zinc-900">
                <span className="text-purple-400 font-bold shrink-0">0{idx + 1}.</span>
                <span>{step}</span>
              </div>
            ))}
          </div>
        </div>

        {/* Dependencies */}
        <div className="p-3.5 bg-[#0b0b0e] border border-zinc-900 rounded space-y-2">
          <span className="text-xs font-bold text-zinc-200 flex items-center gap-2">
            <Layers className="w-4 h-4 text-cyan-400" /> Context Dependencies
          </span>
          <div className="flex flex-wrap gap-2">
            {transparency.dependencies.map((dep, idx) => (
              <span key={idx} className="px-2.5 py-1 bg-[#050507] border border-zinc-800 rounded text-xs text-zinc-300 font-mono">
                {dep}
              </span>
            ))}
          </div>
        </div>

        {/* Raw Inputs & Outputs */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          <div>
            <span className="text-[10px] uppercase text-zinc-500 font-bold">Input Payload</span>
            <pre className="mt-1 p-2.5 bg-[#020204] border border-zinc-900 rounded text-zinc-300 text-[11px] overflow-x-auto whitespace-pre-wrap">
              {transparency.inputPayload}
            </pre>
          </div>

          <div>
            <span className="text-[10px] uppercase text-zinc-500 font-bold">Output Result</span>
            <pre className="mt-1 p-2.5 bg-[#020204] border border-zinc-900 rounded text-emerald-400 text-[11px] overflow-x-auto whitespace-pre-wrap">
              {transparency.outputResult}
            </pre>
          </div>
        </div>
      </div>
    </div>
  );
};
