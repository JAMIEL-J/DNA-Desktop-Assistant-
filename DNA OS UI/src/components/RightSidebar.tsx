import React, { useState } from 'react';
import { 
  Activity, 
  Cpu, 
  HardDrive, 
  Wifi, 
  Thermometer, 
  Layers, 
  ListTree, 
  Bell, 
  ChevronLeft, 
  ChevronRight, 
  ListOrdered,
  AlertCircle,
  CheckCircle2,
  Clock
} from 'lucide-react';
import { AgentProcess, ExecutionQueueTask, NotificationItem, SystemTelemetry } from '../types';
import { renderSparklineSvg, generateProcessTree } from '../utils/telemetryEngine';

interface RightSidebarProps {
  telemetry: SystemTelemetry;
  agents: AgentProcess[];
  executionQueue: ExecutionQueueTask[];
  notifications: NotificationItem[];
  isCollapsed: boolean;
  onToggleCollapse: () => void;
  onClearNotifications: () => void;
}

export const RightSidebar: React.FC<RightSidebarProps> = ({
  telemetry,
  agents,
  executionQueue,
  notifications,
  isCollapsed,
  onToggleCollapse,
  onClearNotifications,
}) => {
  const [activeTab, setActiveTab] = useState<'htop' | 'lifecycle' | 'queue' | 'alerts'>('htop');
  const processTree = generateProcessTree();

  const countByStatus = (status: string) => agents.filter((a) => a.status === status).length;

  if (isCollapsed) {
    return (
      <aside className="w-10 bg-[#080808] border-l border-[#1A1A1A] flex flex-col items-center py-2 space-y-3 select-none text-[#555555] font-mono">
        <button
          onClick={onToggleCollapse}
          className="p-1.5 hover:bg-[#1A1A1A] text-[#D1D1D1] rounded transition"
          title="Expand System Monitor"
        >
          <ChevronLeft className="w-4 h-4" />
        </button>

        <div className="w-6 h-px bg-[#1A1A1A] my-1"></div>

        <div className="text-[10px] text-[#FF9F45] font-bold rotate-90 my-2">
          CPU {telemetry.cpuUsageTotal}%
        </div>
        <div className="text-[10px] text-[#B983FF] font-bold rotate-90 my-2">
          RAM {telemetry.ramUsedGb}G
        </div>
      </aside>
    );
  }

  return (
    <aside className="w-72 bg-[#080808] border-l border-[#1A1A1A] flex flex-col h-full select-none font-mono text-xs z-20">
      {/* Sidebar Header Navigation */}
      <div className="flex items-center justify-between p-2 border-b border-[#1A1A1A] bg-[#0B0B0B]">
        <div className="flex items-center gap-1">
          <button
            onClick={() => setActiveTab('htop')}
            className={`px-2 py-1 rounded text-[10px] font-medium transition flex items-center gap-1 ${
              activeTab === 'htop' ? 'bg-[#1A1A1A] text-[#D1D1D1] border border-[#333333]' : 'text-[#555555] hover:text-[#D1D1D1]'
            }`}
          >
            <Activity className="w-3 h-3 text-[#7DCE13]" />
            htop
          </button>
          <button
            onClick={() => setActiveTab('lifecycle')}
            className={`px-2 py-1 rounded text-[10px] font-medium transition flex items-center gap-1 ${
              activeTab === 'lifecycle' ? 'bg-[#1A1A1A] text-[#D1D1D1] border border-[#333333]' : 'text-[#555555] hover:text-[#D1D1D1]'
            }`}
          >
            Lifecycle
          </button>
          <button
            onClick={() => setActiveTab('queue')}
            className={`px-2 py-1 rounded text-[10px] font-medium transition flex items-center gap-1 ${
              activeTab === 'queue' ? 'bg-[#1A1A1A] text-[#D1D1D1] border border-[#333333]' : 'text-[#555555] hover:text-[#D1D1D1]'
            }`}
          >
            Queue
          </button>
          <button
            onClick={() => setActiveTab('alerts')}
            className={`px-2 py-1 rounded text-[10px] font-medium transition flex items-center gap-1 ${
              activeTab === 'alerts' ? 'bg-[#1A1A1A] text-[#D1D1D1] border border-[#333333]' : 'text-[#555555] hover:text-[#D1D1D1]'
            }`}
          >
            <Bell className="w-3 h-3 text-[#FF9F45]" />
            {notifications.length}
          </button>
        </div>

        <button
          onClick={onToggleCollapse}
          className="p-1 hover:bg-[#1A1A1A] text-[#555555] hover:text-[#D1D1D1] rounded"
          title="Collapse Sidebar"
        >
          <ChevronRight className="w-3.5 h-3.5" />
        </button>
      </div>

      {/* Main Content Body */}
      <div className="flex-1 overflow-y-auto p-2.5 space-y-4">
        {activeTab === 'htop' && (
          <div className="space-y-4">
            {/* CPU Core Bars (htop style) */}
            <div className="p-2.5 bg-[#0a0a0d] border border-zinc-900 rounded space-y-2">
              <div className="flex items-center justify-between text-[11px]">
                <span className="font-bold text-zinc-200 flex items-center gap-1.5">
                  <Cpu className="w-3.5 h-3.5 text-orange-400" /> CPU Core Utilization
                </span>
                <span className="text-orange-400 font-bold">{telemetry.cpuUsageTotal}%</span>
              </div>

              <div className="grid grid-cols-2 gap-1.5">
                {(telemetry.cpuCores || []).map((val, idx) => (
                  <div key={idx} className="space-y-0.5">
                    <div className="flex justify-between text-[9px] text-zinc-500">
                      <span>Core {idx}</span>
                      <span className="text-zinc-300">{val}%</span>
                    </div>
                    <div className="w-full bg-zinc-900 h-1.5 rounded overflow-hidden">
                      <div
                        className="bg-gradient-to-r from-emerald-500 via-amber-500 to-red-500 h-full transition-all duration-300"
                        style={{ width: `${val}%` }}
                      ></div>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* RAM & GPU Gauges */}
            <div className="p-2.5 bg-[#0a0a0d] border border-zinc-900 rounded space-y-2">
              {/* RAM */}
              <div className="space-y-1">
                <div className="flex items-center justify-between text-[11px]">
                  <span className="text-zinc-300 font-bold flex items-center gap-1.5">
                    <HardDrive className="w-3.5 h-3.5 text-purple-400" /> RAM Memory RSS
                  </span>
                  <span className="text-purple-400 font-bold">{telemetry.ramUsedGb} / {telemetry.ramTotalGb} GB</span>
                </div>
                <div className="w-full bg-zinc-900 h-1.5 rounded overflow-hidden">
                  <div
                    className="bg-purple-500 h-full transition-all duration-300"
                    style={{ width: `${(telemetry.ramUsedGb / telemetry.ramTotalGb) * 100}%` }}
                  ></div>
                </div>
              </div>

              {/* GPU */}
              <div className="space-y-1 pt-1 border-t border-zinc-900">
                <div className="flex items-center justify-between text-[11px]">
                  <span className="text-zinc-300 font-bold flex items-center gap-1.5">
                    <Thermometer className="w-3.5 h-3.5 text-cyan-400" /> GPU Compute ({telemetry.gpuTempC}°C)
                  </span>
                  <span className="text-cyan-400 font-bold">{telemetry.gpuUsagePercent}%</span>
                </div>
                <div className="w-full bg-zinc-900 h-1.5 rounded overflow-hidden">
                  <div
                    className="bg-cyan-500 h-full transition-all duration-300"
                    style={{ width: `${telemetry.gpuUsagePercent}%` }}
                  ></div>
                </div>
              </div>
            </div>

            {/* Network RX/TX Sparkline */}
            <div className="p-2.5 bg-[#0a0a0d] border border-zinc-900 rounded space-y-2">
              <div className="flex items-center justify-between text-[11px]">
                <span className="text-zinc-300 font-bold flex items-center gap-1.5">
                  <Wifi className="w-3.5 h-3.5 text-blue-400" /> Network RX/TX I/O
                </span>
                <span className="text-blue-400 font-bold">{telemetry.networkRxKbps} KB/s</span>
              </div>

              <div
                className="p-2 bg-[#030305] border border-zinc-900 rounded flex items-center justify-center h-14"
                dangerouslySetInnerHTML={{
                  __html: renderSparklineSvg(telemetry.history.network, '#3b82f6', 220, 40) || '',
                }}
              />
            </div>

            {/* Process Tree Hierarchy */}
            <div className="p-2.5 bg-[#0a0a0d] border border-zinc-900 rounded space-y-2">
              <span className="font-bold text-zinc-200 text-[11px] flex items-center gap-1.5">
                <ListTree className="w-3.5 h-3.5 text-amber-400" /> htop PID Tree Hierarchy
              </span>

              <div className="space-y-1 text-[10px] text-zinc-400 font-mono border-t border-zinc-900 pt-1.5">
                {processTree[0]?.children?.[0]?.children?.map((proc) => (
                  <div key={proc.pid} className="flex items-center justify-between hover:bg-zinc-900/50 p-1 rounded">
                    <span className="truncate text-zinc-300 font-bold">{proc.name}</span>
                    <span className="text-zinc-500 shrink-0">PID {proc.pid} | {proc.cpuPercent}%</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}

        {activeTab === 'lifecycle' && (
          <div className="space-y-3">
            <span className="text-[10px] uppercase font-bold text-zinc-500 tracking-wider">
              Agent Swarm Lifecycle Metrics
            </span>

            <div className="grid grid-cols-2 gap-2 text-xs">
              <div className="p-2 bg-emerald-950/20 border border-emerald-500/30 rounded text-emerald-400 space-y-0.5">
                <span className="text-[10px] uppercase text-zinc-400 font-bold">Running</span>
                <div className="text-lg font-bold">{countByStatus('Running')}</div>
              </div>
              <div className="p-2 bg-amber-950/20 border border-amber-500/30 rounded text-amber-400 space-y-0.5">
                <span className="text-[10px] uppercase text-zinc-400 font-bold">Waiting</span>
                <div className="text-lg font-bold">{countByStatus('Waiting')}</div>
              </div>
              <div className="p-2 bg-zinc-900 border border-zinc-800 rounded text-zinc-400 space-y-0.5">
                <span className="text-[10px] uppercase text-zinc-400 font-bold">Paused</span>
                <div className="text-lg font-bold">{countByStatus('Paused')}</div>
              </div>
              <div className="p-2 bg-red-950/20 border border-red-500/30 rounded text-red-400 space-y-0.5">
                <span className="text-[10px] uppercase text-zinc-400 font-bold">Failed / Crashed</span>
                <div className="text-lg font-bold">{countByStatus('Failed') + countByStatus('Crashed')}</div>
              </div>
            </div>

            <div className="p-2.5 bg-[#0a0a0d] border border-zinc-900 rounded space-y-2">
              <span className="font-bold text-zinc-200 text-xs">Swarm Health Invariant Check</span>
              <p className="text-[11px] text-zinc-400 leading-normal">
                All 6 active agents responding to heartbeat pings. Consensus voting term stable.
              </p>
            </div>
          </div>
        )}

        {activeTab === 'queue' && (
          <div className="space-y-3">
            <span className="text-[10px] uppercase font-bold text-zinc-500 tracking-wider">
              Swarm Execution Queue
            </span>

            <div className="space-y-2">
              {executionQueue.map((task) => (
                <div key={task.id} className="p-2.5 bg-[#0a0a0d] border border-zinc-900 rounded space-y-1">
                  <div className="flex items-center justify-between">
                    <span className="font-bold text-zinc-200 text-[11px]">{task.title}</span>
                    <span className="text-[9px] px-1.5 py-0.2 bg-purple-950/40 text-purple-300 border border-purple-500/30 rounded font-bold">
                      {task.priority}
                    </span>
                  </div>
                  <div className="flex items-center justify-between text-[10px] text-zinc-400">
                    <span>Agent: {task.assignedAgentName}</span>
                    <span>ETA: {task.etaSeconds}s</span>
                  </div>
                  <div className="w-full bg-zinc-900 h-1 rounded overflow-hidden mt-1">
                    <div className="bg-purple-500 h-full" style={{ width: `${task.progressPercent}%` }}></div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {activeTab === 'alerts' && (
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-[10px] uppercase font-bold text-zinc-500 tracking-wider">
                System Alerts & Interrupts
              </span>
              <button
                onClick={onClearNotifications}
                className="text-[10px] text-red-400 hover:underline"
              >
                Clear All
              </button>
            </div>

            <div className="space-y-2">
              {notifications.map((n) => (
                <div key={n.id} className="p-2.5 bg-[#0a0a0d] border border-zinc-900 rounded space-y-1">
                  <div className="flex items-center justify-between">
                    <span className="font-bold text-zinc-200 text-[11px] flex items-center gap-1">
                      {n.type === 'warning' && <AlertCircle className="w-3.5 h-3.5 text-amber-400" />}
                      {n.type === 'success' && <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />}
                      {n.type === 'info' && <Clock className="w-3.5 h-3.5 text-blue-400" />}
                      {n.title}
                    </span>
                    <span className="text-[9px] text-zinc-500">{n.timestamp}</span>
                  </div>
                  <p className="text-[10px] text-zinc-400">{n.message}</p>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Footer Status */}
      <div className="p-2 border-t border-zinc-800/80 bg-[#050507] text-[10px] text-zinc-500 flex items-center justify-between">
        <span>SWARM TELEMETRY: LIVE</span>
        <span className="text-emerald-400 font-bold">100% HEALTH</span>
      </div>
    </aside>
  );
};
