import { useEffect, useState } from 'react';
import { getApiBaseUrl } from '../config/urls';

const POLL_MS = 10000;

// Global count across all rooms (public + every private group), polled while
// the landing page is up -- see GET /api/rooms (backend/app/main.py).
export default function useActivePlayerCount() {
  const [count, setCount] = useState(null);

  useEffect(() => {
    let cancelled = false;

    const fetchCount = async () => {
      try {
        const res = await fetch(`${getApiBaseUrl()}/api/rooms`);
        if (!res.ok || cancelled) return;
        const data = await res.json();
        if (!cancelled && typeof data.total_players === 'number') {
          setCount(data.total_players);
        }
      } catch {
        // network hiccup -- keep showing the last known count
      }
    };

    fetchCount();
    const id = setInterval(fetchCount, POLL_MS);
    return () => { cancelled = true; clearInterval(id); };
  }, []);

  return count;
}
