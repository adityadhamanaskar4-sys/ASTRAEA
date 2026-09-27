import { createContext, useContext, useState, useCallback, useEffect } from 'react';
import { getOfficers, fetchOfficersFromBackend, syncBackendState } from '../services/astraeaLedger';

const AstraeaCtx = createContext(null);

export function AstraeaProvider({ children }) {
  const [officers, setOfficers] = useState(() => getOfficers());
  const [actingOfficerUid, setActingOfficerUid] = useState(() => {
    const list = getOfficers();
    return list[0]?.uid || 'OFC-2291';
  });
  const [activeSession, setActiveSession] = useState(null); // set only after ledger commit
  const [investigation, setInvestigation] = useState(null); // result of an investigator lookup
  const [refreshTick, setRefreshTick] = useState(0);

  const bumpRefresh = useCallback(() => {
    setRefreshTick((t) => t + 1);
    syncBackendState().catch(() => {});
  }, []);

  const refreshFromBackend = useCallback(async () => {
    try {
      const roster = await fetchOfficersFromBackend();
      if (roster && roster.length > 0) {
        setOfficers(roster);
      }
      await syncBackendState();
      setRefreshTick((t) => t + 1);
    } catch (err) {
      console.warn('Backend sync warning:', err.message);
    }
  }, []);

  useEffect(() => {
    refreshFromBackend();
  }, [refreshFromBackend]);

  const value = {
    officers,
    actingOfficerUid,
    setActingOfficerUid,
    activeSession,
    setActiveSession,
    investigation,
    setInvestigation,
    refreshTick,
    bumpRefresh,
    refreshFromBackend,
  };

  return <AstraeaCtx.Provider value={value}>{children}</AstraeaCtx.Provider>;
}

export function useAstraea() {
  const ctx = useContext(AstraeaCtx);
  if (!ctx) throw new Error('useAstraea must be used within AstraeaProvider');
  return ctx;
}
