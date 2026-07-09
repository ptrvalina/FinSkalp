// FinSkalp wallet graph — indexes for multi-hop traversal (avoid full graph scan)
CREATE INDEX wallet_address IF NOT EXISTS FOR (w:Wallet) ON (w.address);
CREATE INDEX wallet_case_ref IF NOT EXISTS FOR (w:Wallet) ON (w.case_ref);
CREATE INDEX wallet_id IF NOT EXISTS FOR (w:Wallet) ON (w.id);
CREATE INDEX finsk_case_ref IF NOT EXISTS FOR (c:FinSkalpCase) ON (c.case_ref);
