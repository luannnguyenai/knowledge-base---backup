"use client";

import { useState } from "react";
import Chat from "./Chat";
import Login from "./Login";
import Overview from "./Overview";
import Profile from "./Profile";
import { Layout } from "@/components/chat/Layout";
import { ThemeProvider } from "@/ThemeProvider";

export type AppView = "chat" | "overview" | "profile";

export default function NextAppShell({ view = "chat" }: { view?: AppView }) {
  const [isLoggedIn, setIsLoggedIn] = useState(false);

  const handleLogout = () => setIsLoggedIn(false);

  return (
    <ThemeProvider>
      {!isLoggedIn ? (
        <Login onLogin={() => setIsLoggedIn(true)} />
      ) : (
        <Layout
          onLogout={handleLogout}
          content={
            <>
              {view === "overview" && <Overview />}
              {view === "profile" && <Profile onLogout={handleLogout} />}
              {view === "chat" && <Chat />}
            </>
          }
        />
      )}
    </ThemeProvider>
  );
}
