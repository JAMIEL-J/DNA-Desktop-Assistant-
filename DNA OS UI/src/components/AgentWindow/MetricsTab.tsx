import React from 'react';
import { Activity, Cpu, HardDrive, Wifi, ArrowDownUp } from 'lucide-react';
import { AgentProcess } from '../../types';
import { renderSparklineSvg } from '../../utils/telemetryEngine';

interface MetricsTabProps {
  agent: AgentProcess;
}

export const MetricsTab: React.FC<MetricsTabProps> = ({ agent }) => {
  const { metricsHistory } = agent;

  return (
    <div className="flex flex-col h-full bg-[#050507] text-zinc-300 font-mono text-xs overflow-hidden">
      {/* Header */}
      <div className="p-3 bg-[#0a0a0d] border-b border-zinc-900 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Activity className="w-4 h-4 text-blue-400" />
          <span className="font-semibold text-zinc-200">Process Telemetry & Resource Monitors</span>
        </div>
        <span className="text-[11px] text-zinc-500">PID: {agent.pid}</span>
      </div>

      {/* Metrics Sparkline Cards Grid */}
      <div className="flex-1 overflow-y-auto p-4 grid grid-cols-1 md:grid-cols-2 gap-4 bg-[#07070a]">
        {/* CPU Sparkline */}
        <div className="p-4 bg-[#0b0b0e] border border-zinc-900 rounded space-y-3">
          <div className="flex items-center justify-between">
            <span className="font-bold text-zinc-200 flex items-center gap-2">
              <Cpu className="w-4 h-4 text-orange-400" /> CPU Core Utilization
            </span>
            <span className="text-sm font-bold text-orange-400">{agent.cpuUsagePercent}%</span>
          </div>

          <div
            className="p-3 bg-[#020204] border border-zinc-900 rounded flex items-center justify-center h-28"
            dangerouslySetInnerHTML={{
              __html: renderSparklineSvg(metricsHistory.cpuUsage, '#f97316', 280, 70) || '',
            }}
          />

          <div className="flex justify-between text-[10px] text-zinc-500">
            <span>6 min ago ({metricsHistory.cpuUsage[0]}%)</span>
            <span>Current ({agent.cpuUsagePercent}%)</span>
          </div>
        </div>

        {/* Memory Sparkline */}
        <div className="p-4 bg-[#0b0b0e] border border-zinc-900 rounded space-y-3">
          <div className="flex items-center justify-between">
            <span className="font-bold text-zinc-200 flex items-center gap-2">
              <HardDrive className="w-4 h-4 text-purple-400" /> Memory RSS Allocation
            </span>
            <span className="text-sm font-bold text-purple-400">{agent.memoryUsageMb} MB</span>
          </div>

          <div
            className="p-3 bg-[#020204] border border-zinc-900 rounded flex items-center justify-center h-28"
            dangerouslySetInnerHTML={{
              __html: renderSparklineSvg(metricsHistory.memoryUsage, '#a855f7', 280, 70) || '',
            }}
          />

          <div className="flex justify-between text-[10px] text-zinc-500">
            <span>Min ({Math.min(...metricsHistory.memoryUsage)} MB)</span>
            <span>Max ({Math.max(...metricsHistory.memoryUsage)} MB)</span>
          </div>
        </div>

        {/* I/O Rate Sparkline */}
        <div className="p-4 bg-[#0b0b0e] border border-zinc-900 rounded space-y-3">
          <div className="flex items-center justify-between">
            <span className="font-bold text-zinc-200 flex items-center gap-2">
              <ArrowDownUp className="w-4 h-4 text-emerald-400" /> Storage I/O Operations / sec
            </span>
            <span className="text-sm font-bold text-emerald-400">
              {metricsHistory.ioRate[metricsHistory.ioRate.length - 1]} ops
            </span>
          </div>

          <div
            className="p-3 bg-[#020204] border border-zinc-900 rounded flex items-center justify-center h-28"
            dangerouslySetInnerHTML={{
              __html: renderSparklineSvg(metricsHistory.ioRate, '#22c55e', 280, 70) || '',
            }}
          />
        </div>

        {/* Network Throughput Sparkline */}
        <div className="p-4 bg-[#0b0b0e] border border-zinc-900 rounded space-y-3">
          <div className="flex items-center justify-between">
            <span className="font-bold text-zinc-200 flex items-center gap-2">
              <Wifi className="w-4 h-4 text-cyan-400" /> Network Throughput
            </span>
            <span className="text-sm font-bold text-cyan-400">
              {metricsHistory.networkRate[metricsHistory.networkRate.length - 1]} KB/s
            </span>
          </div>

          <div
            className="p-3 bg-[#020204] border border-zinc-900 rounded flex items-center justify-center h-28"
            dangerouslySetInnerHTML={{
              __html: renderSparklineSvg(metricsHistory.networkRate, '#06b6d4', 280, 70) || '',
            }}
          />
        </div>
      </div>
    </div>
  );
};
