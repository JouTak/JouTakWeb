import { useCallback, useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import PropTypes from "prop-types";
import { Button } from "@gravity-ui/uikit";

import { me } from "../services/api";

import { needsPersonalization } from "../utils/profileState";

import AccountHero from "../components/account/AccountHero";
import ProfileCard from "../components/account/ProfileCard";
import EmailCard from "../components/account/EmailCard";
import PasswordCard from "../components/account/PasswordCard";
import DeleteAccountCard from "../components/account/DeleteAccountCard";
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

SkeletonBlock.propTypes = {
  minHeight: PropTypes.number,
};

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
  const navigate = useNavigate();
  const [profile, setProfile] = useState(null);
  const [loading, setLoading] = useState(true);

  const redirectToSessionExpired = useCallback(() => {
    const params = new URLSearchParams({
      reason: "SESSION_UNAUTHORIZED",
      next: "/account/security",
    });
    navigate(`/session-expired?${params.toString()}`, { replace: true });
  }, [navigate]);

  const reload = async () => {
    setLoading(true);
    try {
      const p = await me();
      setProfile(p);
    } catch {
      redirectToSessionExpired();
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
      } catch {
        if (!cancelled) {
          redirectToSessionExpired();
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [redirectToSessionExpired]);

  if (loading) return <AccountSecuritySkeleton />;
  if (!profile) return null;

  return (
    <div
      className="container py-4"
      style={{ maxWidth: 960, display: "grid", gap: 24 }}
    >
      {needsPersonalization(profile) && (
        <section
          style={{
            border: "1px solid rgba(255, 163, 0, 0.45)",
            borderRadius: 12,
            padding: 16,
            background: "rgba(255, 163, 0, 0.12)",
            display: "grid",
            gap: 8,
          }}
        >
          <b>Базовый аккаунт: персонализация профиля не завершена</b>
          <span>
            Заполни обязательные поля профиля, чтобы открыть полный
            функционал.
          </span>
          <div>
            <Button
              view="normal"
              onClick={() => navigate("/account/complete-profile")}
            >
              Завершить профиль
            </Button>
          </div>
        </section>
      )}
      <AccountHero profile={profile} />
      <ProfileCard onUpdated={reload} />
      <EmailCard />
      <PasswordCard />
      {/*<MfaCard profile={profile} />*/}
      {/*<PasskeysCard />*/}
      {/*<OauthCard />*/}
      <SessionsCard />
      <DeleteAccountCard />
    </div>
  );
}
