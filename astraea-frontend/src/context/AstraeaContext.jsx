import { createContext, useContext, useState, useCallback } from 'react';
import { getOfficers } from '../services/astraeaLedger';

const AstraeaCtx = createContext(null);

export function AstraeaProvider({ children }) {
  const officers = getOfficers();
  const [actingOfficerUid, setActingOfficerUid] = useState(officers[0].uid);
  const [activeSession, setActiveSession] = useState(null); // set only after ledger commit
  const [investigation, setInvestigation] = useState(null); // result of an investigator lookup
  const [refreshTick, setRefreshTick] = useState(0);

  const bumpRefresh = useCallback(() => setRefreshTick((t) => t + 1), []);

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
  };

  return <AstraeaCtx.Provider value={value}>{children}</AstraeaCtx.Provider>;
}

export function useAstraea() {
  const ctx = useContext(AstraeaCtx);
  if (!ctx) throw new Error('useAstraea must be used within AstraeaProvider');
  return ctx;
}
