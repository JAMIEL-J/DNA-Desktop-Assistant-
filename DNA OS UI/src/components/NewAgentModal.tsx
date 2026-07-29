import React, { useState } from 'react';
import { Plus, Terminal, X, Cpu, Layers } from 'lucide-react';
import { AgentRole } from '../types';
import { ROLE_COLORS } from '../data/initialAgents';

interface NewAgentModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSpawnAgent: (name: string, role: AgentRole, task: string) => void;
}

export const NewAgentModal: React.FC<NewAgentModalProps> = ({
  isOpen,
  onClose,
  onSpawnAgent,
}) => {
  const [name, setName] = useState('');
  const [role, setRole] = useState<AgentRole>('Developer');
  const [task, setTask] = useState('');

  if (!isOpen) return null;

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim()) return;
    onSpawnAgent(
      name.trim(),
      role,
      task.trim() || `Executing autonomous sub-routines for ${role} role`
    );
    setName('');
    setTask('');
    onClose();
  };

  const rolesList: AgentRole[] = ['Research', 'Planner', 'Developer', 'Writer', 'QA', 'Analyst'];

  return (
    <div className="fixed inset-0 bg-black/80 backdrop-blur-sm z-50 flex items-center justify-center p-4 font-mono select-none">
      <div className="bg-[#0a0a0e] border border-zinc-800 rounded-lg w-full max-w-md shadow-2xl overflow-hidden">
        <div className="p-3 bg-[#0d0d12] border-b border-zinc-800 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Plus className="w-4 h-4 text-purple-400" />
            <span className="font-bold text-zinc-100 text-xs">Spawn Autonomous Agent Process</span>
          </div>
          <button onClick={onClose} className="p-1 text-zinc-500 hover:text-zinc-200">
            <X className="w-4 h-4" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="p-4 space-y-4 text-xs">
          <div>
            <label className="block text-zinc-400 font-bold mb-1">Agent Name</label>
            <input
              type="text"
              required
              placeholder="e.g., Aether-Dev, Orion-QA, Sentinel-Analyst..."
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="w-full bg-[#050507] border border-zinc-800 rounded px-3 py-1.5 text-zinc-100 placeholder-zinc-600 focus:outline-none focus:border-purple-500"
            />
          </div>

          <div>
            <label className="block text-zinc-400 font-bold mb-1">Agent Role</label>
            <div className="grid grid-cols-3 gap-1.5">
              {rolesList.map((r) => {
                const style = ROLE_COLORS[r];
                const isSelected = role === r;
                return (
                  <button
                    key={r}
                    type="button"
                    onClick={() => setRole(r)}
                    className={`p-2 rounded border text-[10px] font-bold uppercase transition ${
                      isSelected
                        ? `${style.bg} ${style.text} ${style.border} ring-1 ring-purple-500/50`
                        : 'bg-[#050507] border-zinc-900 text-zinc-500 hover:text-zinc-300'
                    }`}
                  >
                    {r}
                  </button>
                );
              })}
            </div>
          </div>

          <div>
            <label className="block text-zinc-400 font-bold mb-1">Initial Task Directive</label>
            <textarea
              rows={3}
              placeholder="Describe initial task directive or command prompt..."
              value={task}
              onChange={(e) => setTask(e.target.value)}
              className="w-full bg-[#050507] border border-zinc-800 rounded p-2 text-zinc-100 placeholder-zinc-600 focus:outline-none focus:border-purple-500"
            />
          </div>

          <div className="pt-2 flex justify-end gap-2">
            <button
              type="button"
              onClick={onClose}
              className="px-3 py-1.5 rounded bg-zinc-800 text-zinc-300 hover:bg-zinc-700 font-medium"
            >
              Cancel
            </button>
            <button
              type="submit"
              className="px-4 py-1.5 rounded bg-purple-600 hover:bg-purple-500 text-white font-bold shadow-lg shadow-purple-600/30"
            >
              Spawn Agent
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
