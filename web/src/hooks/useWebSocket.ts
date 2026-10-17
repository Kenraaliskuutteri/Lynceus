import { useEffect, useRef, useState, useCallback } from 'react';

type Status = 'connecting' | 'open' | 'closed';

export function useWebSocket(getUrl: (() => Promise<string | null>) | null) {
  const [status, setStatus] = useState<Status>('closed');
  const [lastMessage, setLastMessage] = useState<MessageEvent | null>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const retryRef = useRef<number>(0);
  const timeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    if (!getUrl) return;
    let cancelled = false;

    const retry = () => {
      const delay = Math.min(1000 * 2 ** retryRef.current, 15000);
      retryRef.current += 1;
      timeoutRef.current = setTimeout(connect, delay);
    };

    const connect = async () => {
      setStatus('connecting');
      const url = await getUrl();
      if (cancelled) return;
      if (!url) {
        setStatus('closed');
        retry();
        return;
      }

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
        retry();
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
  }, [getUrl]);

  const send = useCallback((data: string) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(data);
    }
  }, []);

  return { status, lastMessage, send };
}