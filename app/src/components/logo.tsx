"use client";

import { useTheme } from "next-themes";
import { useEffect, useState } from "react";
import Image from "next/image";

export function Logo() {
  const { resolvedTheme } = useTheme();
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  if (!mounted) {
    return <div className="w-7 h-7" />;
  }

  return (
    <Image
      src={resolvedTheme === "dark" ? "/logo-light.png" : "/logo-dark.png"}
      alt="Hummingbot"
      width={28}
      height={28}
    />
  );
}
