import { useState, useEffect, useCallback } from "react";
import { PeraWalletConnect } from "@perawallet/connect";
import { vgDebug, vgInfo } from "../lib/vedaGuardLog";

const peraWallet = new PeraWalletConnect();

export function usePeraWallet() {
  const [address, setAddress] = useState<string | null>(null);
  const [isConnecting, setIsConnecting] = useState(false);

  const handleDisconnect = useCallback(() => {
    vgDebug("PeraWallet", "disconnect");
    peraWallet.disconnect();
    setAddress(null);
  }, []);

  useEffect(() => {
    peraWallet
      .reconnectSession()
      .then((accounts) => {
        if (accounts.length > 0) {
          setAddress(accounts[0]);
          vgInfo("PeraWallet", "reconnectSession", { address: accounts[0] });
          peraWallet.connector?.on("disconnect", handleDisconnect);
        }
      })
      .catch(() => {
        vgDebug("PeraWallet", "reconnectSession: no prior session");
      });
  }, [handleDisconnect]);

  const connect = useCallback(async () => {
    setIsConnecting(true);
    try {
      const accounts = await peraWallet.connect();
      if (accounts.length > 0) {
        setAddress(accounts[0]);
        vgInfo("PeraWallet", "connect OK", { address: accounts[0] });
        peraWallet.connector?.on("disconnect", handleDisconnect);
      }
    } catch (err) {
      console.error("Pera connect error:", err);
    } finally {
      setIsConnecting(false);
    }
  }, [handleDisconnect]);

  const disconnect = useCallback(() => {
    handleDisconnect();
  }, [handleDisconnect]);

  return { address, connect, disconnect, isConnecting, peraWallet };
}
