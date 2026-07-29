import React, { useRef, useEffect, useState } from 'react';
import { Mic, MicOff, Volume2, Sparkles, Radio, Activity, Eye, Zap } from 'lucide-react';

interface NeuralGlobeProps {
  width?: number;
  height?: number;
  className?: string;
  isCompact?: boolean;
  isFullScreen?: boolean;
}

interface Node3D {
  x: number;
  y: number;
  z: number;
  baseX: number;
  baseY: number;
  baseZ: number;
  radius: number;
  pulseOffset: number;
  connections: number[];
  energy: number;
}

export const NeuralGlobe: React.FC<NeuralGlobeProps> = ({
  width = 380,
  height = 380,
  className = '',
  isCompact = false,
  isFullScreen = false,
}) => {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const [dimensions, setDimensions] = useState({
    w: isFullScreen ? (typeof window !== 'undefined' ? window.innerWidth : 1200) : width,
    h: isFullScreen ? (typeof window !== 'undefined' ? window.innerHeight : 800) : height,
  });

  const [isMicActive, setIsMicActive] = useState(false);
  const [audioLevel, setAudioLevel] = useState(0);

  const audioContextRef = useRef<AudioContext | null>(null);
  const analyserRef = useRef<AnalyserNode | null>(null);
  const micStreamRef = useRef<MediaStream | null>(null);

  // Mouse / Pointer State
  const mouseRef = useRef({ x: 0, y: 0, targetX: 0, targetY: 0, isHovering: false });
  const rotRef = useRef({ rx: 0, ry: 0, speedX: 0.002, speedY: 0.003 });

  // Handle Resize for Full Window Workspace mode
  useEffect(() => {
    if (!isFullScreen) {
      setDimensions({ w: width, h: height });
      return;
    }

    const updateContainerDimensions = () => {
      if (containerRef.current) {
        const cw = containerRef.current.clientWidth || window.innerWidth;
        const ch = containerRef.current.clientHeight || window.innerHeight;
        setDimensions({ w: Math.max(300, cw), h: Math.max(300, ch) });
      } else {
        setDimensions({
          w: typeof window !== 'undefined' ? window.innerWidth : 1000,
          h: typeof window !== 'undefined' ? window.innerHeight : 600,
        });
      }
    };

    updateContainerDimensions();
    const resizeObserver = new ResizeObserver(() => updateContainerDimensions());
    if (containerRef.current) {
      resizeObserver.observe(containerRef.current);
    }

    window.addEventListener('resize', updateContainerDimensions);
    return () => {
      resizeObserver.disconnect();
      window.removeEventListener('resize', updateContainerDimensions);
    };
  }, [isFullScreen, width, height]);

  // Window-wide Mouse Tracking when in Full Screen Mode
  useEffect(() => {
    if (!isFullScreen) return;

    const handleWindowMouseMove = (e: MouseEvent) => {
      const centerX = window.innerWidth / 2;
      const centerY = window.innerHeight / 2;
      mouseRef.current.targetX = e.clientX - centerX;
      mouseRef.current.targetY = e.clientY - centerY;
      mouseRef.current.isHovering = true;
    };

    window.addEventListener('mousemove', handleWindowMouseMove);
    return () => window.removeEventListener('mousemove', handleWindowMouseMove);
  }, [isFullScreen]);

  // Toggle Microphone Audio Reactivity
  const toggleMicrophone = async () => {
    if (isMicActive) {
      // Stop mic
      if (micStreamRef.current) {
        micStreamRef.current.getTracks().forEach((t) => t.stop());
      }
      if (audioContextRef.current) {
        audioContextRef.current.close();
      }
      setIsMicActive(false);
      setAudioLevel(0);
      return;
    }

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      micStreamRef.current = stream;
      const audioCtx = new (window.AudioContext || (window as any).webkitAudioContext)();
      const analyser = audioCtx.createAnalyser();
      analyser.fftSize = 64;
      const source = audioCtx.createMediaStreamSource(stream);
      source.connect(analyser);

      audioContextRef.current = audioCtx;
      analyserRef.current = analyser;
      setIsMicActive(true);
    } catch (err) {
      console.warn('Microphone access denied or not supported, switching to synthetic voice simulation mode:', err);
      // Fallback to simulated voice pulses
      setIsMicActive(true);
    }
  };

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    let animationFrameId: number;

    // Generate 3D Spherical Neural Nodes
    const currentW = isFullScreen ? (typeof window !== 'undefined' ? window.innerWidth : 1200) : dimensions.w;
    const currentH = isFullScreen ? (typeof window !== 'undefined' ? window.innerHeight : 800) : dimensions.h;

    const NODE_COUNT = isFullScreen ? 220 : (isCompact ? 70 : 120);
    const GLOBE_RADIUS = isFullScreen
      ? Math.min(currentW, currentH) * 0.28
      : (isCompact ? 110 : 140);

    const nodes: Node3D[] = [];

    // Fibonacci sphere distribution for uniform neuron dispersion
    const phi = Math.PI * (3 - Math.sqrt(5));
    for (let i = 0; i < NODE_COUNT; i++) {
      const y = 1 - (i / (NODE_COUNT - 1)) * 2; // y goes from 1 to -1
      const radiusAtY = Math.sqrt(1 - y * y); // radius at y
      const theta = phi * i; // golden angle increment

      const x = Math.cos(theta) * radiusAtY;
      const z = Math.sin(theta) * radiusAtY;

      const px = x * GLOBE_RADIUS;
      const py = y * GLOBE_RADIUS;
      const pz = z * GLOBE_RADIUS;

      nodes.push({
        x: px,
        y: py,
        z: pz,
        baseX: px,
        baseY: py,
        baseZ: pz,
        radius: Math.random() * 2 + 1.2,
        pulseOffset: Math.random() * Math.PI * 2,
        connections: [],
        energy: Math.random(),
      });
    }

    // Connect nearest spatial neighbors to form neural synaptic mesh
    let totalConn = 0;
    for (let i = 0; i < nodes.length; i++) {
      const distances: { index: number; dist: number }[] = [];
      for (let j = 0; j < nodes.length; j++) {
        if (i === j) continue;
        const dx = nodes[i].baseX - nodes[j].baseX;
        const dy = nodes[i].baseY - nodes[j].baseY;
        const dz = nodes[i].baseZ - nodes[j].baseZ;
        const dist = Math.sqrt(dx * dx + dy * dy + dz * dz);
        if (dist < GLOBE_RADIUS * 0.65) {
          distances.push({ index: j, dist });
        }
      }
      distances.sort((a, b) => a.dist - b.dist);
      nodes[i].connections = distances.slice(0, 3).map((d) => d.index);
      totalConn += nodes[i].connections.length;
    }

    let simulatedVoiceTime = 0;

    const render = () => {
      ctx.clearRect(0, 0, canvas.width, canvas.height);

      const centerX = canvas.width / 2;
      const centerY = canvas.height / 2;

      // Handle Voice / Mic Audio Level Calculation
      let currentAudioVolume = 0;
      if (isMicActive) {
        if (analyserRef.current) {
          const dataArray = new Uint8Array(analyserRef.current.frequencyBinCount);
          analyserRef.current.getByteFrequencyData(dataArray);
          let sum = 0;
          for (let i = 0; i < dataArray.length; i++) {
            sum += dataArray[i];
          }
          currentAudioVolume = sum / dataArray.length / 255; // 0.0 to 1.0
        } else {
          // Synthetic voice modulation
          simulatedVoiceTime += 0.08;
          currentAudioVolume = Math.abs(Math.sin(simulatedVoiceTime) * Math.cos(simulatedVoiceTime * 2.3)) * 0.7 + 0.15;
        }
      }
      setAudioLevel(currentAudioVolume);

      // Mouse Smooth Interpolation
      mouseRef.current.x += (mouseRef.current.targetX - mouseRef.current.x) * 0.08;
      mouseRef.current.y += (mouseRef.current.targetY - mouseRef.current.y) * 0.08;

      // Rotate Globe
      rotRef.current.ry += rotRef.current.speedY + (mouseRef.current.x / canvas.width - 0.5) * 0.02;
      rotRef.current.rx += rotRef.current.speedX + (mouseRef.current.y / canvas.height - 0.5) * 0.02;

      const cosY = Math.cos(rotRef.current.ry);
      const sinY = Math.sin(rotRef.current.ry);
      const cosX = Math.cos(rotRef.current.rx);
      const sinX = Math.sin(rotRef.current.rx);

      // Project 3D points
      const projectedNodes: { x: number; y: number; z: number; scale: number; orig: Node3D; index: number }[] = [];

      nodes.forEach((node, idx) => {
        // Voice expansion pulse - expands globe largely across full window when voice speaks
        const hoverExpansion = mouseRef.current.isHovering ? 0.25 : 0;
        const voiceMultiplier = isFullScreen ? 2.4 : 1.35;
        const expansionFactor = 1 + currentAudioVolume * voiceMultiplier + hoverExpansion;
        let x = node.baseX * expansionFactor;
        let y = node.baseY * expansionFactor;
        let z = node.baseZ * expansionFactor;

        // Rotation Y
        let x1 = x * cosY - z * sinY;
        let z1 = z * cosY + x * sinY;

        // Rotation X
        let y1 = y * cosX - z1 * sinX;
        let z2 = z1 * cosX + y * sinX;

        // Perspective Projection
        const fov = isFullScreen ? 800 : 500;
        const safeZ = Math.max(-fov + 20, z2);
        const scale = Math.max(0.05, fov / (fov + safeZ));
        let projX = centerX + x1 * scale;
        let projY = centerY + y1 * scale;

        // Interactive Cursor Magnetic Warp & Displacement
        const mouseDx = projX - (centerX + mouseRef.current.x * (isFullScreen ? 0.9 : 0.7));
        const mouseDy = projY - (centerY + mouseRef.current.y * (isFullScreen ? 0.9 : 0.7));
        const distToMouse = Math.sqrt(mouseDx * mouseDx + mouseDy * mouseDy);
        const cursorInfluenceRadius = isFullScreen ? 260 : 130;

        if (distToMouse < cursorInfluenceRadius && distToMouse > 0) {
          const force = (1 - distToMouse / cursorInfluenceRadius);
          // Magnetic wave push/pull effect
          const displace = force * (isFullScreen ? 60 : 35);
          projX += (mouseDx / distToMouse) * displace;
          projY += (mouseDy / distToMouse) * displace;
        }

        projectedNodes.push({
          x: projX,
          y: projY,
          z: z2,
          scale,
          orig: node,
          index: idx,
        });
      });

      // Sort by Z for proper depth rendering
      projectedNodes.sort((a, b) => b.z - a.z);

      const timeNow = Date.now() * 0.003;

      // Draw Synaptic Connecting Axons / Lines
      ctx.lineWidth = 0.8;
      projectedNodes.forEach((pNode) => {
        if (pNode.z > 200) return; // Cull back faces

        const alphaDepth = Math.max(0.05, Math.min(1, (180 - pNode.z) / 320));

        pNode.orig.connections.forEach((targetIdx) => {
          const targetNode = projectedNodes.find((p) => p.index === targetIdx);
          if (!targetNode) return;

          // Check distance to mouse pointer for cursor reactivity
          const mouseDx = pNode.x - (centerX + mouseRef.current.x * 0.5);
          const mouseDy = pNode.y - (centerY + mouseRef.current.y * 0.5);
          const distToMouse = Math.sqrt(mouseDx * mouseDx + mouseDy * mouseDy);
          const isCursorNear = distToMouse < 90;

          // Axon line opacity & glow
          let lineAlpha = alphaDepth * 0.35;
          if (isCursorNear) lineAlpha = Math.min(0.9, lineAlpha * 2.5);
          if (currentAudioVolume > 0.2) lineAlpha += currentAudioVolume * 0.4;

          // Gradient color stroke
          ctx.beginPath();
          ctx.moveTo(pNode.x, pNode.y);
          ctx.lineTo(targetNode.x, targetNode.y);

          if (isCursorNear || currentAudioVolume > 0.4) {
            ctx.strokeStyle = `rgba(185, 131, 255, ${lineAlpha})`; // Purple flare
          } else {
            ctx.strokeStyle = `rgba(77, 150, 255, ${lineAlpha * 0.7})`; // Blue idle
          }
          ctx.stroke();

          // Reactive Synaptic Action Potential Pulses (floating energy sparks along axons)
          if ((pNode.index + targetIdx) % 3 === 0) {
            const sparkPos = (Math.sin(timeNow + pNode.index) + 1) / 2;
            const sx = pNode.x + (targetNode.x - pNode.x) * sparkPos;
            const sy = pNode.y + (targetNode.y - pNode.y) * sparkPos;
            const sparkRadius = Math.max(0.1, 1.2 * pNode.scale);

            ctx.beginPath();
            ctx.arc(sx, sy, sparkRadius, 0, Math.PI * 2);
            ctx.fillStyle = `rgba(255, 159, 69, ${lineAlpha * 0.9})`; // Orange spark
            ctx.fill();
          }
        });
      });

      // Draw Neuron Nodes
      projectedNodes.forEach((pNode) => {
        const mouseDx = pNode.x - (centerX + mouseRef.current.x * 0.5);
        const mouseDy = pNode.y - (centerY + mouseRef.current.y * 0.5);
        const distToMouse = Math.sqrt(mouseDx * mouseDx + mouseDy * mouseDy);
        const isCursorNear = distToMouse < 80;

        const pulse = Math.sin(timeNow * 2 + pNode.orig.pulseOffset) * 0.5 + 0.5;
        let nodeRadius = Math.max(0.1, (pNode.orig.radius + pulse * 1.5) * pNode.scale);

        if (isCursorNear) nodeRadius *= 1.8;
        if (currentAudioVolume > 0.1) nodeRadius *= 1 + currentAudioVolume * 1.2;

        const alphaDepth = Math.max(0.15, Math.min(1, (180 - pNode.z) / 300));
        const auraRadius = Math.max(0.2, nodeRadius * 3.5);

        // Outer Glow Aura
        const auraGrad = ctx.createRadialGradient(pNode.x, pNode.y, 0, pNode.x, pNode.y, auraRadius);
        if (isCursorNear) {
          auraGrad.addColorStop(0, `rgba(255, 159, 69, ${alphaDepth * 0.8})`);
          auraGrad.addColorStop(1, 'rgba(255, 159, 69, 0)');
        } else if (currentAudioVolume > 0.3) {
          auraGrad.addColorStop(0, `rgba(185, 131, 255, ${alphaDepth * 0.9})`);
          auraGrad.addColorStop(1, 'rgba(185, 131, 255, 0)');
        } else {
          auraGrad.addColorStop(0, `rgba(77, 150, 255, ${alphaDepth * 0.5})`);
          auraGrad.addColorStop(1, 'rgba(77, 150, 255, 0)');
        }

        ctx.beginPath();
        ctx.arc(pNode.x, pNode.y, auraRadius, 0, Math.PI * 2);
        ctx.fillStyle = auraGrad;
        ctx.fill();

        // Core Neuron Point
        ctx.beginPath();
        ctx.arc(pNode.x, pNode.y, Math.max(0.8, nodeRadius), 0, Math.PI * 2);
        ctx.fillStyle = isCursorNear
          ? '#ffffff'
          : currentAudioVolume > 0.3
          ? '#B983FF'
          : '#4D96FF';
        ctx.fill();

        // Draw lightning tendril to cursor if cursor is directly hovering close
        if (isCursorNear && distToMouse < 45) {
          ctx.beginPath();
          ctx.moveTo(pNode.x, pNode.y);
          const midX = (pNode.x + (centerX + mouseRef.current.x * 0.5)) / 2 + (Math.random() - 0.5) * 10;
          const midY = (pNode.y + (centerY + mouseRef.current.y * 0.5)) / 2 + (Math.random() - 0.5) * 10;
          ctx.lineTo(midX, midY);
          ctx.lineTo(centerX + mouseRef.current.x * 0.5, centerY + mouseRef.current.y * 0.5);
          ctx.strokeStyle = `rgba(255, 255, 255, ${0.8 - distToMouse / 60})`;
          ctx.lineWidth = 1;
          ctx.stroke();
        }
      });

      // Draw Center Energy Nucleus Core
      const voiceExpansionBonus = currentAudioVolume * 70;
      const hoverBonus = mouseRef.current.isHovering ? 18 : 0;
      const coreRadius = Math.max(0.5, (20 + voiceExpansionBonus + hoverBonus) * (isCompact ? 0.7 : 1));
      const coreOuterRadius = Math.max(1, coreRadius * 2.5);
      const coreGrad = ctx.createRadialGradient(centerX, centerY, 0, centerX, centerY, coreOuterRadius);
      coreGrad.addColorStop(0, `rgba(185, 131, 255, ${0.6 + currentAudioVolume * 0.4})`);
      coreGrad.addColorStop(0.4, `rgba(77, 150, 255, ${0.35 + currentAudioVolume * 0.45})`);
      coreGrad.addColorStop(0.8, `rgba(125, 206, 19, ${currentAudioVolume * 0.35})`);
      coreGrad.addColorStop(1, 'rgba(5, 5, 5, 0)');

      ctx.beginPath();
      ctx.arc(centerX, centerY, coreOuterRadius, 0, Math.PI * 2);
      ctx.fillStyle = coreGrad;
      ctx.fill();

      animationFrameId = requestAnimationFrame(render);
    };

    render();

    return () => {
      cancelAnimationFrame(animationFrameId);
    };
  }, [isCompact, isMicActive]);

  // Pointer Movement Handler
  const handleMouseMove = (e: React.MouseEvent<HTMLDivElement>) => {
    const rect = e.currentTarget.getBoundingClientRect();
    const x = e.clientX - rect.left - rect.width / 2;
    const y = e.clientY - rect.top - rect.height / 2;
    mouseRef.current.targetX = x;
    mouseRef.current.targetY = y;
    mouseRef.current.isHovering = true;
  };

  const handleMouseLeave = () => {
    mouseRef.current.targetX = 0;
    mouseRef.current.targetY = 0;
    mouseRef.current.isHovering = false;
  };

  const canvasW = dimensions.w;
  const canvasH = dimensions.h;

  return (
    <div
      ref={containerRef}
      onMouseMove={handleMouseMove}
      onMouseLeave={handleMouseLeave}
      className={`relative flex flex-col items-center justify-center font-sans select-none ${
        isFullScreen ? 'w-full h-full min-h-screen overflow-hidden' : ''
      } ${className}`}
    >
      {/* Canvas Neural Globe Stage */}
      <div className="relative flex items-center justify-center">
        <canvas
          ref={canvasRef}
          width={canvasW}
          height={canvasH}
          className="cursor-crosshair rounded-full transition-transform duration-300"
        />

        {/* Ambient Ring Details */}
        <div
          className="absolute rounded-full border border-dashed border-[#1A1A1A] pointer-events-none animate-[spin_40s_linear_infinite]"
          style={{
            width: Math.min(canvasW, canvasH) * 0.88,
            height: Math.min(canvasW, canvasH) * 0.88,
          }}
        />
        <div
          className="absolute rounded-full border border-dotted border-[#B983FF]/20 pointer-events-none animate-[spin_25s_linear_infinite_reverse]"
          style={{
            width: Math.min(canvasW, canvasH) * 0.72,
            height: Math.min(canvasW, canvasH) * 0.72,
          }}
        />
      </div>

      {/* Control & Voice Reactivity Bar */}
      <div
        className={`${
          isFullScreen ? 'absolute bottom-6 z-50' : 'mt-2'
        } flex items-center gap-3 bg-[#0B0B0B]/90 backdrop-blur-md border border-[#1A1A1A] px-4 py-1.5 rounded-full text-[11px] text-[#888888] shadow-2xl`}
      >
        {/* Voice Trigger Toggle */}
        <button
          onClick={toggleMicrophone}
          className={`flex items-center gap-1.5 px-2.5 py-0.5 rounded-full transition font-bold ${
            isMicActive
              ? 'bg-[#B983FF]/20 text-[#B983FF] border border-[#B983FF]/50 animate-pulse'
              : 'bg-[#111111] text-[#555555] hover:text-[#D1D1D1] border border-[#1A1A1A]'
          }`}
          title={isMicActive ? 'Voice Reactivity Active' : 'Enable Voice Reactivity'}
        >
          {isMicActive ? (
            <>
              <Mic className="w-3 h-3 text-[#B983FF]" />
              <span>Voice Active</span>
            </>
          ) : (
            <>
              <MicOff className="w-3 h-3" />
              <span>Enable Voice</span>
            </>
          )}
        </button>

        <span className="text-[#1A1A1A]">|</span>

        {/* Audio Level Wave Visual Bar */}
        <div className="flex items-center gap-1">
          <Volume2 className={`w-3 h-3 ${audioLevel > 0.1 ? 'text-[#4D96FF]' : 'text-[#555555]'}`} />
          <div className="w-12 bg-[#111111] h-1.5 rounded-full overflow-hidden border border-[#1A1A1A]">
            <div
              className="bg-gradient-to-r from-[#4D96FF] to-[#B983FF] h-full transition-all duration-75"
              style={{ width: `${Math.min(100, Math.max(5, audioLevel * 100))}%` }}
            />
          </div>
        </div>

        <span className="text-[#1A1A1A]">|</span>

        {/* Cursor Signal Indicator */}
        <div className="flex items-center gap-1 text-[#555555]">
          <Sparkles className="w-3 h-3 text-[#FF9F45]" />
          <span>Cursor Synapses Active</span>
        </div>
      </div>
    </div>
  );
};
