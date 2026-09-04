import React, { useState, useEffect, useCallback } from 'react';
import { AgentProcess, AgentRole, AgentStatus, GlobalEvent, LayoutMode, NotificationItem, SystemTelemetry, WorkspacePreset } from './types';
import { INITIAL_AGENTS } from './data/initialAgents';
import { generateInitialTelemetry, getUpdatedTelemetry } from './utils/telemetryEngine';
import { Header } from './components/Header';
import { LeftSidebar } from './components/LeftSidebar';
import { RightSidebar } from './components/RightSidebar';
import { BottomConsole } from './components/BottomConsole';
import { TilingWorkspace } from './components/TilingWorkspace';
import { CommandPalette } from './components/CommandPalette';
import { UniversalSearchModal } from './components/UniversalSearchModal';
import { NewAgentModal } from './components/NewAgentModal';
import { SwarmAvatarRosterModal } from './components/SwarmAvatarRosterModal';
import { useWebSocket, WSMessage } from './utils/wsClient';

export default function App() {
  const [agents, setAgents] = useState<AgentProcess[]>(INITIAL_AGENTS);
  const [focusedAgentId, setFocusedAgentId] = useState<string | null>(INITIAL_AGENTS[0]?.id || null);
  const [layoutMode, setLayoutMode] = useState<LayoutMode>('2x2_GRID');
  
  // Sidebars & Panels state
  const [isLeftSidebarCollapsed, setIsLeftSidebarCollapsed] = useState(false);
  const [isRightSidebarCollapsed, setIsRightSidebarCollapsed] = useState(false);
  const [isBottomConsoleCollapsed, setIsBottomConsoleCollapsed] = useState(false);
  const [isNeuralGlobeActive, setIsNeuralGlobeActive] = useState(false);
  const [isBootSequenceActive, setIsBootSequenceActive] = useState(true);
  const [isAvatarRosterOpen, setIsAvatarRosterOpen] = useState(false);

  // Modals state
  const [isCommandPaletteOpen, setIsCommandPaletteOpen] = useState(false);
  const [isUniversalSearchOpen, setIsUniversalSearchOpen] = useState(false);
  const [isNewAgentModalOpen, setIsNewAgentModalOpen] = useState(false);

  // Real-time System Telemetry
  const [telemetry, setTelemetry] = useState<SystemTelemetry>(generateInitialTelemetry());

  // Global Event Bus
  const [globalEvents, setGlobalEvents] = useState<GlobalEvent[]>([
    { id: 'ev-1', timestamp: '09:14:21', sourceAgent: 'SYSTEM', level: 'info', message: 'AgentOS Kernel v4.2.0-alpha booted on Cloud Run instance.' },
    { id: 'ev-2', timestamp: '09:15:02', sourceAgent: 'Atlas-Research', level: 'broadcast', message: 'Emitted consensus research matrix payload to Chronos-Planner.' },
    { id: 'ev-3', timestamp: '09:15:48', sourceAgent: 'Nexus-Developer', level: 'info', message: 'Rust raft_engine binary artifact emitted with zero warnings.' },
    { id: 'ev-4', timestamp: '09:16:15', sourceAgent: 'Vigil-QA', level: 'broadcast', message: 'Split-brain chaos fuzz tests passed with 100% assertions.' }
  ]);

  // Notifications List
  const [notifications, setNotifications] = useState<NotificationItem[]>([
    { id: 'n-1', title: 'Compile Success', message: 'Nexus-Developer built raft_node_daemon binary in 11.0s.', type: 'success', timestamp: '09:15:42', read: false, agentRole: 'Developer' },
    { id: 'n-2', title: 'Chaos Partition Warning', message: 'Vigil-QA injected 3/2 split-brain partition into cluster.', type: 'warning', timestamp: '09:15:53', read: false, agentRole: 'QA' }
  ]);

  // Execution Queue
  const executionQueue = [
    { id: 'q-1', title: 'Compile Release Binary', assignedAgentId: 'agent-developer-03', assignedAgentName: 'Nexus-Developer', priority: 'CRITICAL' as const, status: 'RUNNING' as const, progressPercent: 88, etaSeconds: 4 },
    { id: 'q-2', title: 'Linearizability Audit', assignedAgentId: 'agent-qa-04', assignedAgentName: 'Vigil-QA', priority: 'HIGH' as const, status: 'RUNNING' as const, progressPercent: 94, etaSeconds: 2 },
    { id: 'q-3', title: 'API Doc Generation', assignedAgentId: 'agent-writer-05', assignedAgentName: 'Scribe-Writer', priority: 'MEDIUM' as const, status: 'QUEUED' as const, progressPercent: 20, etaSeconds: 12 }
  ];

  // Spoken voice subtitles state
  const [subtitle, setSubtitle] = useState<{ text: string; type: 'stt' | 'tts'; timestamp: string } | null>(null);

  // Real-time Python WebSocket Handler
  const handleWSMessage = useCallback((msg: WSMessage) => {
    const timeStr = new Date().toLocaleTimeString('en-US', { hour12: false });
    
    if (msg.type === 'metrics' && msg.payload) {
      setTelemetry((prev) => ({
        ...prev,
        cpuUsageTotal: msg.payload.cpu_percent || prev.cpuUsageTotal,
        cpuCores: msg.payload.cpu_cores || prev.cpuCores,
        ramUsedGb: msg.payload.used_memory_gb || prev.ramUsedGb,
        ramTotalGb: msg.payload.total_memory_gb || prev.ramTotalGb,
        activeThreads: msg.payload.total_apps || prev.activeThreads,
      }));
    } else if (msg.type === 'stt' && msg.payload) {
      const text = typeof msg.payload === 'string' ? msg.payload : msg.payload.text;
      if (text) {
        setSubtitle({ text: `Boss: "${text}"`, type: 'stt', timestamp: timeStr });
        setGlobalEvents((prev) => [
          ...prev,
          { id: `ev-${Date.now()}`, timestamp: timeStr, sourceAgent: 'BOSS', level: 'broadcast', message: text }
        ]);
      }
    } else if (msg.type === 'tts' && msg.payload) {
      const text = typeof msg.payload === 'string' ? msg.payload : msg.payload.text;
      const agentName = (typeof msg.payload === 'object' && msg.payload.agentName) ? msg.payload.agentName : 'JARVIS';
      if (text) {
        setSubtitle({ text: `${agentName}: "${text}"`, type: 'tts', timestamp: timeStr });
        setGlobalEvents((prev) => [
          ...prev,
          { id: `ev-${Date.now()}`, timestamp: timeStr, sourceAgent: agentName, level: 'info', message: text }
        ]);
      }
    } else if (msg.type === 'log' && msg.payload) {
      const { agentName, message, level } = msg.payload;
      // NEXUS orchestrator messages land in the JARVIS terminal (no separate NEXUS window).
      const key = (agentName || '').toLowerCase() === 'nexus' ? 'jarvis' : (agentName || '').toLowerCase();
      if (message) {
        setAgents((prev) =>
          prev.map((ag) => {
            if (ag.name.toLowerCase() === key || ag.role.toLowerCase() === key) {
              return {
                ...ag,
                logs: [...ag.logs, { id: `log-${Date.now()}-${Math.random()}`, timestamp: timeStr, message, level: level || 'info' }]
              };
            }
            return ag;
          })
        );
      }
    }
  }, []);

  const { sendDirective } = useWebSocket('ws://127.0.0.1:8765', handleWSMessage);

  // Keyboard Shortcuts Listener
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'k') {
        e.preventDefault();
        setIsCommandPaletteOpen((prev) => !prev);
      }
      if ((e.metaKey || e.ctrlKey) && e.shiftKey && e.key.toLowerCase() === 'p') {
        e.preventDefault();
        setIsCommandPaletteOpen((prev) => !prev);
      }
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'b') {
        e.preventDefault();
        setIsLeftSidebarCollapsed((prev) => !prev);
      }
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'j') {
        e.preventDefault();
        setIsBottomConsoleCollapsed((prev) => !prev);
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);

  // Handlers for Agents
  const handleUpdateAgent = useCallback((updatedAgent: AgentProcess) => {
    setAgents((prev) => prev.map((a) => (a.id === updatedAgent.id ? updatedAgent : a)));
  }, []);

  const handleCloseAgent = (id: string) => {
    setAgents((prev) => prev.filter((a) => a.id !== id));
  };

  const handleTogglePinAgent = (id: string) => {
    setAgents((prev) =>
      prev.map((a) => (a.id === id ? { ...a, isPinned: !a.isPinned } : a))
    );
  };

  const handleCloneAgent = (id: string) => {
    const target = agents.find((a) => a.id === id);
    if (!target) return;
    const newPid = Math.floor(8000 + Math.random() * 1000);
    const timeStr = new Date().toLocaleTimeString('en-US', { hour12: false });
    const cloned: AgentProcess = {
      ...target,
      id: `agent-clone-${Date.now()}`,
      pid: newPid,
      name: `${target.name}-Worker`,
      status: 'Running',
      logs: [
        ...target.logs,
        {
          id: `log-clone-init`,
          timestamp: timeStr,
          message: `Forked child process PID ${newPid} from parent process PID ${target.pid}`,
          level: 'system',
        },
      ],
    };
    setAgents((prev) => [...prev, cloned]);
  };

  const handleSplitHorizontal = (id: string) => {
    setLayoutMode('2x2_GRID');
    handleCloneAgent(id);
  };

  const handleSplitVertical = (id: string) => {
    setLayoutMode('3_COLUMN');
    handleCloneAgent(id);
  };

  const handleExecuteDirective = async (agentId: string, prompt: string) => {
    const timeStr = new Date().toLocaleTimeString('en-US', { hour12: false });
    
    // Append user input prompt to agent terminal logs immediately
    setAgents((prev) =>
      prev.map((a) => {
        if (a.id === agentId) {
          return {
            ...a,
            status: 'Running',
            activeTask: prompt,
            logs: [
              ...a.logs,
              {
                id: `log-user-cmd-${Date.now()}`,
                timestamp: timeStr,
                message: `$ ${prompt}`,
                level: 'debug',
              },
            ],
          };
        }
        return a;
      })
    );

    // Add event to global bus
    const agentName = agents.find((a) => a.id === agentId)?.name || 'AGENT';
    setGlobalEvents((prev) => [
      ...prev,
      {
        id: `ev-${Date.now()}`,
        timestamp: timeStr,
        sourceAgent: agentName,
        level: 'info',
        message: `Executing directive: "${prompt}"`,
      },
    ]);

    // Send directive to server API
    try {
      const res = await fetch('/api/agent/execute', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          agentRole: agents.find((a) => a.id === agentId)?.role || 'Developer',
          agentName,
          prompt,
        }),
      });
      const data = await res.json();

      if (data.success && data.result) {
        const { logs: responseLogs, reasoningExplanation, codeArtifact, transparency } = data.result;

        setAgents((prev) =>
          prev.map((a) => {
            if (a.id === agentId) {
              const newLogs = (responseLogs || []).map((msg: string, idx: number) => ({
                id: `log-res-${Date.now()}-${idx}`,
                timestamp: new Date().toLocaleTimeString('en-US', { hour12: false }),
                message: msg,
                level: 'success' as const,
              }));

              const newFiles = codeArtifact
                ? [
                    ...a.files,
                    {
                      id: `file-dyn-${Date.now()}`,
                      path: codeArtifact.filename || `/workspace/dynamic_output.ts`,
                      language: codeArtifact.language || 'typescript',
                      content: codeArtifact.code || '// Generated output',
                      sizeKb: 1.2,
                      lastModifiedBy: a.name,
                      timestamp: timeStr,
                    },
                  ]
                : a.files;

              return {
                ...a,
                logs: [...a.logs, ...newLogs],
                files: newFiles,
                transparency: transparency
                  ? { ...a.transparency, ...transparency }
                  : a.transparency,
              };
            }
            return a;
          })
        );
      }
    } catch (err) {
      console.error('Failed to execute directive API:', err);
    }
  };

  const handleClearAgentLogs = (agentId: string) => {
    setAgents((prev) =>
      prev.map((a) => (a.id === agentId ? { ...a, logs: [] } : a))
    );
  };

  const handleSpawnNewAgent = (name: string, role: AgentRole, task: string) => {
    const timeStr = new Date().toLocaleTimeString('en-US', { hour12: false });
    const newPid = Math.floor(8100 + Math.random() * 500);
    const newAgent: AgentProcess = {
      id: `agent-custom-${Date.now()}`,
      pid: newPid,
      name,
      role,
      color: 'text-purple-400',
      borderHex: '#a855f7',
      status: 'Running',
      activeTask: task,
      runtimeSeconds: 0,
      cpuUsagePercent: 12.0,
      memoryUsageMb: 250,
      activeTab: 'Terminal',
      isMinimized: false,
      isMaximized: false,
      isFloating: false,
      isPinned: false,
      logs: [
        { id: 'log-init-1', timestamp: timeStr, message: `Initialized process ${name} [PID ${newPid}] for role ${role}`, level: 'system' },
        { id: 'log-init-2', timestamp: timeStr, message: `Executing task directive: "${task}"`, level: 'info' },
      ],
      timeline: [
        { id: 't-1', title: 'Process Spawn', description: 'Container process spawned in netns', status: 'completed', timestamp: timeStr, durationMs: 120 },
      ],
      memory: [
        { id: 'm-1', key: 'initial_directive', value: task, type: 'state', updatedAt: timeStr, sizeBytes: 512 },
      ],
      files: [],
      conversations: [
        {
          commitHash: `c${Math.floor(Math.random() * 100000)}`,
          author: name,
          agentRole: role,
          timestamp: timeStr,
          executionId: `exec_${Date.now()}`,
          summary: `feat(spawn): Process spawned for ${role} task`,
          reasoningPrompt: task,
          reasoningExplanation: 'Allocated new process thread in kernel container.',
          diffSummary: '+ Process entry created',
          inputs: { task },
          outputs: { pid: newPid },
        },
      ],
      dependencyNodes: [
        { id: `node-${Date.now()}`, label: name, agentRole: role, status: 'active', upstreamIds: [], downstreamIds: [] },
      ],
      transparency: {
        whatHappened: `Spawned ${name} to execute ${task}`,
        whyItHappened: 'User manual process trigger from AgentOS UI',
        inputPayload: JSON.stringify({ name, role, task }),
        outputResult: JSON.stringify({ status: 'SPAWNED', pid: newPid }),
        reasoningSummary: ['Allocated PID thread', 'Mounted workspace files'],
        dependencies: ['Kernel Process Daemon'],
        confidenceScore: 99.0,
        executionDurationMs: 120,
        modelUsed: 'gemini-2.5-flash',
        tokensConsumed: 1200,
      },
      metricsHistory: {
        timestamps: ['00:00', '00:01'],
        cpuUsage: [10, 12],
        memoryUsage: [200, 250],
        ioRate: [5, 8],
        networkRate: [20, 30],
      },
    };

    setAgents((prev) => [...prev, newAgent]);
    setFocusedAgentId(newAgent.id);
  };

  const handleBroadcastCommand = (cmd: string) => {
    const timeStr = new Date().toLocaleTimeString('en-US', { hour12: false });
    setGlobalEvents((prev) => [
      ...prev,
      {
        id: `ev-broadcast-${Date.now()}`,
        timestamp: timeStr,
        sourceAgent: 'BROADCAST',
        level: 'broadcast',
        message: `User Broadcast: "${cmd}"`,
      },
    ]);

    if (cmd.toLowerCase() === 'pause all') {
      setAgents((prev) => prev.map((a) => ({ ...a, status: 'Paused' })));
    } else if (cmd.toLowerCase() === 'resume all') {
      setAgents((prev) => prev.map((a) => ({ ...a, status: 'Running' })));
    } else if (cmd.toLowerCase() === 'restart all') {
      setAgents((prev) => prev.map((a) => ({ ...a, status: 'Restarting' })));
    } else {
      // Send broadcast prompt to all running agents
      agents.forEach((ag) => handleExecuteDirective(ag.id, cmd));
    }
  };

  const handleApplyPreset = (preset: WorkspacePreset) => {
    setLayoutMode(preset.layout);
  };

  const handleResetWorkspace = () => {
    setAgents(INITIAL_AGENTS);
    setLayoutMode('2x2_GRID');
    setFocusedAgentId(INITIAL_AGENTS[0]?.id || null);
  };

  const handleSelectAgentTabFromSearch = (agentId: string, tabTarget: string) => {
    setAgents((prev) =>
      prev.map((a) => (a.id === agentId ? { ...a, activeTab: tabTarget as any } : a))
    );
    setFocusedAgentId(agentId);
  };

  return (
    <div className="flex flex-col h-screen w-screen bg-[#050505] grid-bg text-[#d1d1d1] font-mono overflow-hidden select-none">
      {/* Top OS Header */}
      <Header
        onOpenCommandPalette={() => setIsCommandPaletteOpen(true)}
        onOpenUniversalSearch={() => setIsUniversalSearchOpen(true)}
        onOpenNewAgentModal={() => setIsNewAgentModalOpen(true)}
        currentLayout={layoutMode}
        onChangeLayout={setLayoutMode}
        activeAgentsCount={agents.filter((a) => a.status === 'Running').length}
        totalAgentsCount={agents.length}
        onResetWorkspace={handleResetWorkspace}
        onToggleNeuralGlobe={() => setIsNeuralGlobeActive((p) => !p)}
        isNeuralGlobeActive={isNeuralGlobeActive}
        onTriggerBootSequence={() => setIsBootSequenceActive(true)}
        onOpenAvatarRoster={() => setIsAvatarRosterOpen(true)}
      />

      {/* Main Workspace Body */}
      <div className="flex-1 flex overflow-hidden relative">
        {/* Left Sidebar */}
        <LeftSidebar
          agents={agents}
          focusedAgentId={focusedAgentId}
          onSelectAgent={setFocusedAgentId}
          onTogglePinAgent={handleTogglePinAgent}
          onApplyPreset={handleApplyPreset}
          onOpenNewAgentModal={() => setIsNewAgentModalOpen(true)}
          isCollapsed={isLeftSidebarCollapsed}
          onToggleCollapse={() => setIsLeftSidebarCollapsed((p) => !p)}
        />

        {/* Center Multi-Window Workspace */}
        <TilingWorkspace
          agents={agents}
          layoutMode={layoutMode}
          isNeuralGlobeActive={isNeuralGlobeActive}
          isBootSequenceActive={isBootSequenceActive}
          onToggleNeuralGlobe={() => setIsNeuralGlobeActive((p) => !p)}
          onCompleteBootSequence={() => setIsBootSequenceActive(false)}
          onUpdateAgent={handleUpdateAgent}
          onCloseAgent={handleCloseAgent}
          onSplitHorizontal={handleSplitHorizontal}
          onSplitVertical={handleSplitVertical}
          onCloneAgent={handleCloneAgent}
          onExecuteDirective={handleExecuteDirective}
          onClearAgentLogs={handleClearAgentLogs}
        />

        {/* Right System Monitor Sidebar */}
        <RightSidebar
          telemetry={telemetry}
          agents={agents}
          executionQueue={executionQueue}
          notifications={notifications}
          isCollapsed={isRightSidebarCollapsed}
          onToggleCollapse={() => setIsRightSidebarCollapsed((p) => !p)}
          onClearNotifications={() => setNotifications([])}
        />
      </div>

      {/* Live Voice Subtitle Overlay Banner (Floating, Fully Visible Multi-Line) */}
      {subtitle && (
        <div className="fixed bottom-4 left-1/2 -translate-x-1/2 max-w-4xl w-[90%] bg-[#0D0B18]/95 backdrop-blur-md border border-[#B983FF]/50 px-5 py-3 rounded-xl flex items-start justify-between text-xs font-mono select-text z-50 shadow-[0_0_30px_rgba(185,131,255,0.25)]">
          <div className="flex items-start gap-3 overflow-hidden">
            <span className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider shrink-0 ${subtitle.type === 'stt' ? 'bg-[#FF9F45]/20 text-[#FF9F45] border border-[#FF9F45]/40' : 'bg-[#B983FF]/20 text-[#B983FF] border border-[#B983FF]/40'}`}>
              {subtitle.type === 'stt' ? 'VOICE INPUT' : 'NEXUS SPOKEN VOICE'}
            </span>
            <p className="text-[#F0F0F0] font-medium leading-relaxed whitespace-pre-wrap break-words text-xs">
              {subtitle.text}
            </p>
          </div>
          <span className="text-[#777777] text-[10px] shrink-0 ml-4 font-bold">{subtitle.timestamp}</span>
        </div>
      )}

      {/* Modals & Dialog Overlay */}
      <CommandPalette
        isOpen={isCommandPaletteOpen}
        onClose={() => setIsCommandPaletteOpen(false)}
        agents={agents}
        onSelectAgent={setFocusedAgentId}
        onOpenNewAgentModal={() => setIsNewAgentModalOpen(true)}
        onChangeLayout={setLayoutMode}
        onPauseAll={() => handleBroadcastCommand('pause all')}
        onResumeAll={() => handleBroadcastCommand('resume all')}
        onResetWorkspace={handleResetWorkspace}
      />

      <UniversalSearchModal
        isOpen={isUniversalSearchOpen}
        onClose={() => setIsUniversalSearchOpen(false)}
        agents={agents}
        onSelectAgentTab={handleSelectAgentTabFromSearch}
      />

      <NewAgentModal
        isOpen={isNewAgentModalOpen}
        onClose={() => setIsNewAgentModalOpen(false)}
        onSpawnAgent={handleSpawnNewAgent}
      />

      <SwarmAvatarRosterModal
        isOpen={isAvatarRosterOpen}
        agents={agents}
        onClose={() => setIsAvatarRosterOpen(false)}
        onSelectAgent={setFocusedAgentId}
        onSpawnNewAgent={() => {
          setIsAvatarRosterOpen(false);
          setIsNewAgentModalOpen(true);
        }}
      />
    </div>
  );
}
