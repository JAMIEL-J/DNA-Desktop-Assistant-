import { useEffect, useRef } from 'react';
import { AgentProcess, GlobalEvent, SystemTelemetry } from '../types';

export interface WSMessage {
  type: 'metrics' | 'state' | 'stt' | 'tts' | 'log' | 'event';
  payload: any;
}

export function useWebSocket(
  url: string,
  onMessage: (msg: WSMessage) => void
) {
  const wsRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    let ws: WebSocket | null = null;
    let reconnectTimeout: any = null;

    function connect() {
      try {
        ws = new WebSocket(url);
        wsRef.current = ws;

        ws.onopen = () => {
          console.log('[WebSocket] Connected to Python backend at', url);
        };

        ws.onmessage = (event) => {
          try {
            const data: WSMessage = JSON.parse(event.data);
            onMessage(data);
          } catch (e) {
            console.error('[WebSocket] Error parsing message payload:', e);
          }
        };

        ws.onerror = (err) => {
          console.warn('[WebSocket] Error:', err);
        };

        ws.onclose = () => {
          console.log('[WebSocket] Closed. Attempting reconnect in 3s...');
          reconnectTimeout = setTimeout(connect, 3000);
        };
      } catch (err) {
        console.error('[WebSocket] Connection failure:', err);
        reconnectTimeout = setTimeout(connect, 3000);
      }
    }

    connect();

    return () => {
      if (reconnectTimeout) clearTimeout(reconnectTimeout);
      if (ws) {
        ws.onclose = null; // Prevent reconnect on unmount
        ws.close();
      }
    };
  }, [url, onMessage]);

  const sendDirective = (agentId: string, prompt: string) => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(
        JSON.stringify({
          action: 'execute_directive',
          agentId,
          prompt,
        })
      );
    } else {
      console.warn('[WebSocket] Cannot send directive: Socket not connected.');
    }
  };

  return { sendDirective };
}
