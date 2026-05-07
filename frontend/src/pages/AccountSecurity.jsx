import { Button } from "@gravity-ui/uikit";
import PropTypes from "prop-types";
import { useCallback, useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";

import AccountHero from "../components/account/AccountHero";
import DeleteAccountCard from "../components/account/DeleteAccountCard";
import EmailCard from "../components/account/EmailCard";
import MfaCard from "../components/account/MfaCard";
import PasswordCard from "../components/account/PasswordCard";
import ProfileCard from "../components/account/ProfileCard";
import SessionsCard from "../components/account/SessionsCard";
import { getEmailStatus, listSessionsHeadless, me } from "../services/api";
import { needsPersonalization } from "../utils/profileState";

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
            <div
              className="skeleton-line"
              style={{ width: "32%", height: 22 }}
            />
            <div className="skeleton-line" style={{ width: "44%" }} />
          </div>
        </div>
      </SkeletonCard>

      <SkeletonCard minHeight={220}>
        <div
          style={{ display: "flex", justifyContent: "space-between", gap: 12 }}
        >
          <div className="skeleton-line" style={{ width: 118, height: 20 }} />
          <div className="skeleton-line" style={{ width: 96, height: 32 }} />
        </div>
        <div
          className="skeleton-line"
          style={{ width: 92, height: 32, borderRadius: 999 }}
        />
        <SkeletonLine width="26%" />
        <SkeletonLine width="18%" />
        <div
          style={{ display: "flex", justifyContent: "space-between", gap: 12 }}
        >
          <SkeletonLine width="24%" />
          <div className="skeleton-line" style={{ width: 18, height: 18 }} />
        </div>
      </SkeletonCard>

      <SkeletonCard minHeight={140}>
        <div
          style={{ display: "flex", justifyContent: "space-between", gap: 12 }}
        >
          <div className="skeleton-line" style={{ width: 82, height: 20 }} />
          <div className="skeleton-line" style={{ width: 108, height: 24 }} />
        </div>
        <SkeletonLine width="24%" />
        <div className="skeleton-line" style={{ width: 120, height: 32 }} />
      </SkeletonCard>

      <SkeletonCard minHeight={140}>
        <div
          style={{ display: "flex", justifyContent: "space-between", gap: 12 }}
        >
          <div className="skeleton-line" style={{ width: 94, height: 20 }} />
          <div className="skeleton-line" style={{ width: 148, height: 32 }} />
        </div>
        <SkeletonLine width="46%" />
      </SkeletonCard>

      <SkeletonCard minHeight={220}>
        <div
          style={{ display: "flex", justifyContent: "space-between", gap: 12 }}
        >
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
            <div
              style={{
                display: "flex",
                justifyContent: "space-between",
                gap: 12,
              }}
            >
              <div style={{ display: "grid", gap: 8, flex: "1 1 auto" }}>
                <div style={{ display: "flex", gap: 8 }}>
                  <div
                    className="skeleton-line"
                    style={{ width: 126, height: 18 }}
                  />
                  <div
                    className="skeleton-line"
                    style={{ width: 68, height: 20 }}
                  />
                </div>
                <SkeletonLine width="76%" />
                <SkeletonLine width="60%" />
                <SkeletonLine width="34%" />
              </div>
              <div
                className="skeleton-line"
                style={{ width: 96, height: 32 }}
              />
            </div>
          </div>
        ))}
      </SkeletonCard>

      <SkeletonCard minHeight={140}>
        <div
          style={{ display: "flex", justifyContent: "space-between", gap: 12 }}
        >
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

// Session-lifecycle HTTP statuses. 401 = unauthenticated, 410 = session
// was invalidated server-side (e.g. revoked token). Anything else
// (5xx, network, CORS) is a transient server problem and must NOT
// bounce the user to `/session-expired`, otherwise they would be
// forcibly logged out on a flaky backend.
const SESSION_EXPIRED_STATUSES = new Set([401, 410]);

function responseStatus(result) {
  return result?.reason?.response?.status;
}

function isSessionExpiredResult(result) {
  return (
    result?.status === "rejected" &&
    SESSION_EXPIRED_STATUSES.has(responseStatus(result))
  );
}

function isTransientFailure(result) {
  if (result?.status !== "rejected") return false;
  const status = responseStatus(result);
  // No HTTP response at all (network error, aborted) or a server-side
  // failure — treat as transient, surface a page-level error.
  return status === undefined || status >= 500;
}

export default function AccountSecurity() {
  const navigate = useNavigate();
  const [profile, setProfile] = useState(null);
  const [emailStatus, setEmailStatus] = useState(null);
  const [sessionsPayload, setSessionsPayload] = useState(null);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState(null);

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

  const loadAccountData = useCallback(async () => {
    setLoading(true);
    setLoadError(null);

    const [profileResult, emailResult, sessionsResult] =
      await Promise.allSettled([
        me(),
        getEmailStatus(),
        listSessionsHeadless(),
      ]);

    // Profile endpoint is authoritative for session lifecycle — if it
    // fails with 401/410 the session really is gone. Same for the
    // subresources (email / sessions) when THEY report 401/410.
    const expiredProfile =
      profileResult.status === "rejected" &&
      SESSION_EXPIRED_STATUSES.has(responseStatus(profileResult));
    if (
      expiredProfile ||
      isSessionExpiredResult(emailResult) ||
      isSessionExpiredResult(sessionsResult)
    ) {
      redirectToSessionExpired();
      return;
    }

    // Any other failure of the primary profile call (network, 5xx,
    // 4xx != 401/410) is a real load error: stay on the page, show a
    // retry card rather than forcibly logging the user out.
    if (profileResult.status !== "fulfilled") {
      setLoadError(profileResult.reason ?? new Error("Profile load failed"));
      setLoading(false);
      return;
    }

    const profileData = profileResult.value;
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
    // Log transient sub-resource failures so ops can see them without
    // punishing the user.
    if (isTransientFailure(emailResult) || isTransientFailure(sessionsResult)) {
      console.warn("AccountSecurity: transient subresource failure", {
        email: emailResult.status,
        sessions: sessionsResult.status,
      });
    }
    setLoading(false);
  }, [redirectToSessionExpired]);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        if (!cancelled) await loadAccountData();
      } catch (err) {
        if (!cancelled) {
          setLoadError(err);
          setLoading(false);
        }
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [loadAccountData]);

  if (loading) return <AccountSecuritySkeleton />;
  if (loadError) {
    return (
      <div
        className="container py-4"
        style={{ maxWidth: 960, display: "grid", gap: 16 }}
        role="alert"
      >
        <h2 style={{ margin: 0 }}>Не удалось загрузить настройки аккаунта</h2>
        <p style={{ margin: 0, opacity: 0.8 }}>
          Проверь подключение и попробуй ещё раз. Если ошибка повторяется,
          сообщи нам.
        </p>
        <div>
          <Button view="action" onClick={() => loadAccountData()}>
            Повторить
          </Button>
        </div>
      </div>
    );
  }
  if (!profile) return null;

  if (needsPersonalization(profile)) {
    return (
      <div
        className="container py-4"
        style={{ maxWidth: 960, display: "grid", gap: 16 }}
      >
        <section
          style={{
            border: "1px solid rgba(255, 163, 0, 0.45)",
            borderRadius: 12,
            padding: 20,
            background: "rgba(255, 163, 0, 0.12)",
            display: "grid",
            gap: 12,
          }}
        >
          <h2 style={{ margin: 0 }}>
            Для доступа к аккаунту нужен завершённый профиль
          </h2>
          <p style={{ margin: 0, opacity: 0.85 }}>
            Публичные разделы доступны. Профиль, привязки аккаунтов и
            персональные действия откроются после персонализации.
          </p>
          <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
            <Button
              view="action"
              onClick={() => navigate("/account/complete-profile")}
            >
              Завершить персонализацию
            </Button>
            <Button view="outlined" onClick={() => navigate("/joutak")}>
              Перейти на сайт
            </Button>
          </div>
        </section>
        <EmailCard
          initialStatus={emailStatus || fallbackEmailStatus(profile)}
        />
        <MfaCard profile={profile} />
      </div>
    );
  }

  return (
    <div
      className="container py-4"
      style={{ maxWidth: 960, display: "grid", gap: 24 }}
    >
      <AccountHero profile={profile} />
      <ProfileCard profile={profile} onUpdated={handleProfileUpdated} />
      <EmailCard initialStatus={emailStatus || fallbackEmailStatus(profile)} />
      <PasswordCard identityHint={profile?.email || profile?.username || ""} />
      <MfaCard profile={profile} />
      <SessionsCard initialSessions={sessionsPayload || { sessions: [] }} />
      <DeleteAccountCard />
    </div>
  );
}
