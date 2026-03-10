import { useCallback, useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import PropTypes from "prop-types";
import { Button } from "@gravity-ui/uikit";

import { getEmailStatus, listSessionsHeadless, me } from "../services/api";

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

const pageStyle = {
  maxWidth: 960,
  display: "grid",
  gap: 24,
};

function SkeletonCard({ children, minHeight = 160 }) {
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
      {children}
    </div>
  );
}

SkeletonCard.propTypes = {
  children: PropTypes.node.isRequired,
  minHeight: PropTypes.number,
};

function SkeletonLine({ width = "100%", height = 12 }) {
  return (
    <div
      className="skeleton-line"
      style={{
        width,
        height,
        borderRadius: 999,
      }}
      aria-hidden="true"
    />
  );
}

SkeletonLine.propTypes = {
  height: PropTypes.number,
  width: PropTypes.oneOfType([PropTypes.number, PropTypes.string]),
};

function AccountSecuritySkeleton() {
  return (
    <div
      className="container py-4"
      style={pageStyle}
      aria-busy="true"
      aria-live="polite"
    >
      <SkeletonCard minHeight={120}>
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "minmax(96px, 120px) 1fr",
            gap: 16,
            alignItems: "center",
          }}
        >
          <div
            className="skeleton-line"
            style={{
              width: 72,
              height: 72,
              borderRadius: "50%",
              justifySelf: "center",
            }}
          />
          <div style={{ display: "grid", gap: 10 }}>
            <div className="skeleton-line" style={{ width: "32%", height: 22 }} />
            <div className="skeleton-line" style={{ width: "44%" }} />
          </div>
        </div>
      </SkeletonCard>

      <SkeletonCard minHeight={220}>
        <div style={{ display: "flex", justifyContent: "space-between", gap: 12 }}>
          <div className="skeleton-line" style={{ width: 118, height: 20 }} />
          <div className="skeleton-line" style={{ width: 96, height: 32 }} />
        </div>
        <div className="skeleton-line" style={{ width: 92, height: 32, borderRadius: 999 }} />
        <SkeletonLine width="26%" />
        <SkeletonLine width="18%" />
        <div style={{ display: "flex", justifyContent: "space-between", gap: 12 }}>
          <SkeletonLine width="24%" />
          <div className="skeleton-line" style={{ width: 18, height: 18 }} />
        </div>
      </SkeletonCard>

      <SkeletonCard minHeight={140}>
        <div style={{ display: "flex", justifyContent: "space-between", gap: 12 }}>
          <div className="skeleton-line" style={{ width: 82, height: 20 }} />
          <div className="skeleton-line" style={{ width: 108, height: 24 }} />
        </div>
        <SkeletonLine width="24%" />
        <div className="skeleton-line" style={{ width: 120, height: 32 }} />
      </SkeletonCard>

      <SkeletonCard minHeight={140}>
        <div style={{ display: "flex", justifyContent: "space-between", gap: 12 }}>
          <div className="skeleton-line" style={{ width: 94, height: 20 }} />
          <div className="skeleton-line" style={{ width: 148, height: 32 }} />
        </div>
        <SkeletonLine width="46%" />
      </SkeletonCard>

      <SkeletonCard minHeight={220}>
        <div style={{ display: "flex", justifyContent: "space-between", gap: 12 }}>
          <div style={{ display: "grid", gap: 10, flex: "1 1 auto" }}>
            <div className="skeleton-line" style={{ width: 108, height: 20 }} />
            <SkeletonLine width="42%" />
          </div>
          <div style={{ display: "flex", gap: 12 }}>
            <div className="skeleton-line" style={{ width: 180, height: 28 }} />
            <div className="skeleton-line" style={{ width: 210, height: 28 }} />
          </div>
        </div>
        {Array.from({ length: 2 }).map((_, index) => (
          <div
            key={index}
            style={{
              border: "1px solid rgba(255,255,255,0.08)",
              borderRadius: 10,
              padding: 12,
              display: "grid",
              gap: 10,
            }}
          >
            <div style={{ display: "flex", justifyContent: "space-between", gap: 12 }}>
              <div style={{ display: "grid", gap: 8, flex: "1 1 auto" }}>
                <div style={{ display: "flex", gap: 8 }}>
                  <div className="skeleton-line" style={{ width: 126, height: 18 }} />
                  <div className="skeleton-line" style={{ width: 68, height: 20 }} />
                </div>
                <SkeletonLine width="76%" />
                <SkeletonLine width="60%" />
                <SkeletonLine width="34%" />
              </div>
              <div className="skeleton-line" style={{ width: 96, height: 32 }} />
            </div>
          </div>
        ))}
      </SkeletonCard>

      <SkeletonCard minHeight={140}>
        <div style={{ display: "flex", justifyContent: "space-between", gap: 12 }}>
          <div className="skeleton-line" style={{ width: 180, height: 20 }} />
          <div className="skeleton-line" style={{ width: 136, height: 32 }} />
        </div>
        <SkeletonLine width="58%" />
      </SkeletonCard>
    </div>
  );
}

function fallbackEmailStatus(profile) {
  return {
    email: profile?.email || "",
    verified: !!profile?.email_verified,
    pending_email: "",
    resend_target: "",
  };
}

function isUnauthorizedResult(result) {
  return result?.status === "rejected" && result.reason?.response?.status === 401;
}

export default function AccountSecurity() {
  const navigate = useNavigate();
  const [profile, setProfile] = useState(null);
  const [emailStatus, setEmailStatus] = useState(null);
  const [sessionsPayload, setSessionsPayload] = useState(null);
  const [loading, setLoading] = useState(true);

  const redirectToSessionExpired = useCallback(() => {
    const params = new URLSearchParams({
      reason: "SESSION_UNAUTHORIZED",
      next: "/account/security",
    });
    navigate(`/session-expired?${params.toString()}`, { replace: true });
  }, [navigate]);

  const handleProfileUpdated = useCallback((patch = {}) => {
    setProfile((current) => (current ? { ...current, ...patch } : current));
  }, []);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const [profileResult, emailResult, sessionsResult] = await Promise.allSettled([
          me(),
          getEmailStatus(),
          listSessionsHeadless(),
        ]);

        if (
          profileResult.status !== "fulfilled" ||
          isUnauthorizedResult(emailResult) ||
          isUnauthorizedResult(sessionsResult)
        ) {
          if (!cancelled) redirectToSessionExpired();
          return;
        }

        const profileData = profileResult.value;
        if (!cancelled) {
          setProfile(profileData);
          setEmailStatus(
            emailResult.status === "fulfilled"
              ? emailResult.value
              : fallbackEmailStatus(profileData),
          );
          setSessionsPayload(
            sessionsResult.status === "fulfilled"
              ? sessionsResult.value
              : { sessions: [] },
          );
        }
      } catch {
        if (!cancelled) redirectToSessionExpired();
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
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
      <ProfileCard profile={profile} onUpdated={handleProfileUpdated} />
      <EmailCard initialStatus={emailStatus || fallbackEmailStatus(profile)} />
      <PasswordCard username={profile?.username || profile?.email || ""} />
      {/*<MfaCard profile={profile} />*/}
      {/*<PasskeysCard />*/}
      {/*<OauthCard />*/}
      <SessionsCard initialSessions={sessionsPayload || { sessions: [] }} />
      <DeleteAccountCard />
    </div>
  );
}
