"use client";

import { InstanceProvider } from "@/lib/instance";
import { WalletProvider } from "./WalletProvider";

export function Providers({ children }: { children: React.ReactNode }) {
  return (
    <WalletProvider>
      <InstanceProvider>{children}</InstanceProvider>
    </WalletProvider>
  );
}
