import { useEffect, useState } from "react";
import { toaster } from "@gravity-ui/uikit/toaster-singleton";
import { me } from "../services/api";

import AccountHero from "../components/account/AccountHero";
import ProfileCard from "../components/account/ProfileCard";
import EmailCard from "../components/account/EmailCard";
import PasswordCard from "../components/account/PasswordCard";
// import MfaCard from '../components/account/MfaCard';
// import PasskeysCard from '../components/account/PasskeysCard';
// import OauthCard from '../components/account/OauthCard';
import SessionsCard from "../components/account/SessionsCard";

function SkeletonBlock({ minHeight = 160 }) {
  return (
    <div
      className="skeleton-block"
      style={{
        minHeight,
        borderRadius: 12,
        border: "1px solid rgba(255,255,255,0.08)",
        padding: 16,
        display: "grid",
        gap: 12,
      }}
      aria-hidden="true"
    >
      <div className="skeleton-line" style={{ width: "40%" }} />
      <div className="skeleton-line" />
      <div className="skeleton-line" style={{ width: "80%" }} />
      <div className="skeleton-line" style={{ width: "60%" }} />
    </div>
  );
}

function AccountSecuritySkeleton() {
  return (
    <div
      className="container py-4"
      style={{ maxWidth: 960, display: "grid", gap: 24 }}
      aria-busy="true"
      aria-live="polite"
    >
      {/* Hero */}
      <div
        className="skeleton-block"
        style={{
          minHeight: 120,
          borderRadius: 12,
          border: "1px solid rgba(255,255,255,0.08)",
          padding: 16,
          display: "grid",
          gap: 12,
        }}
      >
        <div className="skeleton-line" style={{ width: "30%", height: 18 }} />
        <div className="skeleton-line" style={{ width: "60%" }} />
      </div>

      <SkeletonBlock minHeight={220} />
      <SkeletonBlock minHeight={160} />
      <SkeletonBlock minHeight={160} />
      <SkeletonBlock minHeight={220} />
    </div>
  );
}

export default function AccountSecurity() {
  const [profile, setProfile] = useState(null);
  const [loading, setLoading] = useState(true);

  const reload = async () => {
    setLoading(true);
    try {
      const p = await me();
      setProfile(p);
    } catch (e) {
      toaster.add({ title: "Не удалось обновить профиль", theme: "danger" });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const p = await me();
        if (!cancelled) setProfile(p);
      } catch (e) {
        toaster.add({ title: "Ошибка загрузки профиля", theme: "danger" });
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  if (loading) return <AccountSecuritySkeleton />;

  return (
    <div
      className="container py-4"
      style={{ maxWidth: 960, display: "grid", gap: 24 }}
    >
      <AccountHero profile={profile} />
      <ProfileCard profile={profile} onUpdated={reload} />
      <EmailCard />
      <PasswordCard />
      {/*<MfaCard profile={profile} />*/}
      {/*<PasskeysCard />*/}
      {/*<OauthCard />*/}
      <SessionsCard />
    </div>
  );
}
