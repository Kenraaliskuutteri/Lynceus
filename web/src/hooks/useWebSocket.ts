import { useEffect, useRef, useState, useCallback } from 'react';

type Status = 'connecting' | 'open' | 'closed';

export function useWebSocket(url: string | null) {
  const [status, setStatus] = useState<Status>('closed');
  const [lastMessage, setLastMessage] = useState<MessageEvent | null>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const retryRef = useRef<number>(0);
  const timeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    if (!url) return;
    let cancelled = false;

    const connect = () => {
      setStatus('connecting');
      const ws = new WebSocket(url);
      wsRef.current = ws;

      ws.onopen = () => {
        if (cancelled) return;
        retryRef.current = 0;
        setStatus('open');
      };

      ws.onmessage = (event) => {
        if (cancelled) return;
        setLastMessage(event);
      };

      ws.onclose = () => {
        if (cancelled) return;
        setStatus('closed');
        const delay = Math.min(1000 * 2 ** retryRef.current, 15000);
        retryRef.current += 1;
        timeoutRef.current = setTimeout(connect, delay);
      };

      ws.onerror = () => {
        ws.close();
      };
    };

    connect();

    return () => {
      cancelled = true;
      if (timeoutRef.current) clearTimeout(timeoutRef.current);
      wsRef.current?.close();
    };
  }, [url]);

  const send = useCallback((data: string) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(data);
    }
  }, []);

  return { status, lastMessage, send };
}