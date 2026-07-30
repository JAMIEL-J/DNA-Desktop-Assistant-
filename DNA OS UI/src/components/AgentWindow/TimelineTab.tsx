import React, { useState } from 'react';
import { Clock, CheckCircle2, CircleDashed, AlertTriangle, Play, FastForward } from 'lucide-react';
import { AgentProcess, TimelineStep } from '../../types';

interface TimelineTabProps {
  agent: AgentProcess;
}

export const TimelineTab: React.FC<TimelineTabProps> = ({ agent }) => {
  const [scrubIndex, setScrubIndex] = useState<number>(agent.timeline.length - 1);
  const [selectedStep, setSelectedStep] = useState<TimelineStep | null>(
    agent.timeline[agent.timeline.length - 1] || null
  );

  const activeStep = agent.timeline[scrubIndex] || selectedStep;

  const totalDurationMs = agent.timeline.reduce((acc, s) => acc + s.durationMs, 0);

  return (
    <div className="flex flex-col h-full bg-[#050507] text-zinc-300 font-mono text-xs overflow-hidden">
      {/* Timeline Header & Scrubber */}
      <div className="p-3 bg-[#0a0a0d] border-b border-zinc-900 space-y-2">
        <div className="flex items-center justify-between text-xs">
          <div className="flex items-center gap-2">
            <Clock className="w-4 h-4 text-purple-400" />
            <span className="font-semibold text-zinc-200">Execution Timeline Scrubbing</span>
          </div>
          <span className="text-[11px] text-zinc-500">
            Total Steps: {agent.timeline.length} | Cumulative: {totalDurationMs}ms
          </span>
        </div>

        {/* Timeline Slider Scrubber */}
        <div className="space-y-1">
          <input
            type="range"
            min={0}
            max={Math.max(0, agent.timeline.length - 1)}
            value={scrubIndex}
            onChange={(e) => {
              const idx = parseInt(e.target.value, 10);
              setScrubIndex(idx);
              setSelectedStep(agent.timeline[idx]);
            }}
            className="w-full accent-purple-500 bg-zinc-800 h-1.5 rounded cursor-pointer"
          />
          <div className="flex justify-between text-[10px] text-zinc-500">
            <span>Start [0ms]</span>
            <span>Current: Step {scrubIndex + 1}/{agent.timeline.length}</span>
            <span>Latest [{totalDurationMs}ms]</span>
          </div>
        </div>
      </div>

      {/* Main Split: Steps List & Selected Detail Inspection */}
      <div className="flex-1 grid grid-cols-1 md:grid-cols-2 overflow-hidden divide-y md:divide-y-0 md:divide-x divide-zinc-900">
        {/* Left: Step Nodes List */}
        <div className="overflow-y-auto p-3 space-y-3 bg-[#07070a]">
          {(agent.timeline || []).map((step, idx) => {
            const isScrubbed = idx === scrubIndex;
            return (
              <div
                key={step.id}
                onClick={() => {
                  setScrubIndex(idx);
                  setSelectedStep(step);
                }}
                className={`p-2.5 rounded border transition cursor-pointer ${
                  isScrubbed
                    ? 'bg-purple-950/30 border-purple-500/50 text-zinc-100'
                    : 'bg-[#0b0b0e] border-zinc-900 text-zinc-400 hover:border-zinc-800'
                }`}
              >
                <div className="flex items-center justify-between gap-2 mb-1">
                  <div className="flex items-center gap-2">
                    {step.status === 'completed' && <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />}
                    {step.status === 'in_progress' && <CircleDashed className="w-3.5 h-3.5 text-amber-400 animate-spin" />}
                    {step.status === 'failed' && <AlertTriangle className="w-3.5 h-3.5 text-red-400" />}
                    {step.status === 'pending' && <CircleDashed className="w-3.5 h-3.5 text-zinc-600" />}
                    <span className="font-semibold text-xs text-zinc-200">Step {idx + 1}: {step.title}</span>
                  </div>
                  <span className="text-[10px] text-zinc-500">{step.durationMs}ms</span>
                </div>
                <p className="text-[11px] text-zinc-400 line-clamp-2">{step.description}</p>
                <div className="mt-1.5 flex items-center justify-between text-[10px] text-zinc-500">
                  <span>Timestamp: {step.timestamp}</span>
                  <span className="uppercase text-[9px] px-1 py-0.2 bg-zinc-800 rounded">{step.status}</span>
                </div>
              </div>
            );
          })}
        </div>

        {/* Right: Step Inspector Detail */}
        <div className="p-3 overflow-y-auto space-y-3 bg-[#050507]">
          {activeStep ? (
            <>
              <div className="border-b border-zinc-800/80 pb-2">
                <span className="text-[10px] uppercase tracking-wider text-purple-400 font-bold">Inspecting Timeline Node</span>
                <h3 className="text-sm font-bold text-zinc-100 mt-0.5">{activeStep.title}</h3>
                <span className="text-[10px] text-zinc-500">Executed at {activeStep.timestamp} ({activeStep.durationMs} ms)</span>
              </div>

              <div>
                <span className="text-[10px] uppercase text-zinc-500 font-bold">Step Description</span>
                <p className="text-xs text-zinc-300 mt-1 leading-relaxed bg-[#0a0a0d] p-2 rounded border border-zinc-900">
                  {activeStep.description}
                </p>
              </div>

              <div>
                <span className="text-[10px] uppercase text-zinc-500 font-bold">Execution Status</span>
                <div className="mt-1 flex items-center gap-2">
                  <span className={`px-2 py-0.5 rounded text-[11px] font-bold uppercase ${
                    activeStep.status === 'completed' ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/30' :
                    activeStep.status === 'in_progress' ? 'bg-amber-500/10 text-amber-400 border border-amber-500/30' :
                    'bg-zinc-800 text-zinc-400'
                  }`}>
                    {activeStep.status}
                  </span>
                  <span className="text-[11px] text-zinc-500">Execution delta: +{activeStep.durationMs}ms</span>
                </div>
              </div>

              {activeStep.outputPreview && (
                <div>
                  <span className="text-[10px] uppercase text-zinc-500 font-bold">Output Artifact Preview</span>
                  <pre className="mt-1 p-2 bg-[#020203] border border-zinc-900 rounded text-[11px] text-emerald-400/90 overflow-x-auto whitespace-pre-wrap">
                    {activeStep.outputPreview}
                  </pre>
                </div>
              )}
            </>
          ) : (
            <div className="text-center text-zinc-600 py-12">Select a timeline step to inspect</div>
          )}
        </div>
      </div>
    </div>
  );
};
