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
import {
  PageActions,
  PageNotice,
  PagePanel,
  PageShell,
  StatePage,
} from "../components/ui/PageShell.jsx";
import { getEmailStatus, listSessionsHeadless, me } from "../services/api";
import { needsPersonalization } from "../utils/profileState";
import styles from "./AccountSecurity.module.css";

function SkeletonCard({ children, minHeight = 160 }) {
  return (
    <PagePanel
      className="skeleton-block"
      style={{
        minHeight,
        display: "grid",
        gap: 12,
      }}
      aria-hidden="true"
    >
      {children}
    </PagePanel>
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
    <PageShell
      eyebrow="Аккаунт"
      title="Настройки и безопасность"
      description="Загружаем профиль, способы входа и активные сессии."
      contentClassName={styles.accountGrid}
    >
      <div className={styles.accountGrid} aria-busy="true" aria-live="polite">
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
            style={{
              display: "flex",
              justifyContent: "space-between",
              gap: 12,
            }}
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
            style={{
              display: "flex",
              justifyContent: "space-between",
              gap: 12,
            }}
          >
            <SkeletonLine width="24%" />
            <div className="skeleton-line" style={{ width: 18, height: 18 }} />
          </div>
        </SkeletonCard>

        <SkeletonCard minHeight={140}>
          <div
            style={{
              display: "flex",
              justifyContent: "space-between",
              gap: 12,
            }}
          >
            <div className="skeleton-line" style={{ width: 82, height: 20 }} />
            <div className="skeleton-line" style={{ width: 108, height: 24 }} />
          </div>
          <SkeletonLine width="24%" />
          <div className="skeleton-line" style={{ width: 120, height: 32 }} />
        </SkeletonCard>

        <SkeletonCard minHeight={140}>
          <div
            style={{
              display: "flex",
              justifyContent: "space-between",
              gap: 12,
            }}
          >
            <div className="skeleton-line" style={{ width: 94, height: 20 }} />
            <div className="skeleton-line" style={{ width: 148, height: 32 }} />
          </div>
          <SkeletonLine width="46%" />
        </SkeletonCard>

        <SkeletonCard minHeight={220}>
          <div
            style={{
              display: "flex",
              justifyContent: "space-between",
              gap: 12,
            }}
          >
            <div style={{ display: "grid", gap: 10, flex: "1 1 auto" }}>
              <div
                className="skeleton-line"
                style={{ width: 108, height: 20 }}
              />
              <SkeletonLine width="42%" />
            </div>
            <div style={{ display: "flex", gap: 12 }}>
              <div
                className="skeleton-line"
                style={{ width: 180, height: 28 }}
              />
              <div
                className="skeleton-line"
                style={{ width: 210, height: 28 }}
              />
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
            style={{
              display: "flex",
              justifyContent: "space-between",
              gap: 12,
            }}
          >
            <div className="skeleton-line" style={{ width: 180, height: 20 }} />
            <div className="skeleton-line" style={{ width: 136, height: 32 }} />
          </div>
          <SkeletonLine width="58%" />
        </SkeletonCard>
      </div>
    </PageShell>
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
      <PageShell
        narrow
        eyebrow="Аккаунт"
        title="Настройки недоступны"
        description="Сессия сохранена, но данные аккаунта сейчас не загрузились."
      >
        <PagePanel className={styles.panelStack} role="alert">
          <PageNotice tone="danger">
            Не удалось загрузить настройки аккаунта.
          </PageNotice>
          <p className={styles.muted}>
            Проверь подключение и попробуй ещё раз. Мы не завершаем сессию из-за
            временной ошибки сети или сервера.
          </p>
          <PageActions>
            <Button view="action" size="l" onClick={() => loadAccountData()}>
              Повторить
            </Button>
            <Button view="outlined" size="l" onClick={() => navigate("/")}>
              На главную
            </Button>
          </PageActions>
        </PagePanel>
      </PageShell>
    );
  }
  if (!profile) {
    return (
      <StatePage
        eyebrow="Аккаунт"
        icon="!"
        title="Профиль не найден"
        description="Сессия активна, но данные профиля не вернулись. Попробуй войти заново или вернуться на главную."
        actions={
          <>
            <Button
              view="action"
              size="l"
              onClick={() => navigate("/login?next=/account/security")}
            >
              Войти заново
            </Button>
            <Button view="outlined" size="l" onClick={() => navigate("/")}>
              На главную
            </Button>
          </>
        }
      />
    );
  }

  if (needsPersonalization(profile)) {
    return (
      <PageShell
        eyebrow="Аккаунт"
        title="Заверши профиль"
        description="Базовый аккаунт уже работает, но персональные настройки откроются после двух коротких шагов."
        contentClassName={styles.accountGrid}
      >
        <PagePanel className={styles.panelStack}>
          <PageNotice tone="warning">
            Для доступа к аккаунту нужен завершённый профиль
          </PageNotice>
          <p className={styles.muted}>
            Публичные разделы доступны. Профиль, привязки аккаунтов и
            персональные действия откроются после персонализации.
          </p>
          <PageActions>
            <Button
              view="action"
              size="l"
              onClick={() => navigate("/account/complete-profile")}
            >
              Завершить персонализацию
            </Button>
            <Button view="outlined" size="l" onClick={() => navigate("/")}>
              Перейти на сайт
            </Button>
          </PageActions>
        </PagePanel>
        <EmailCard
          initialStatus={emailStatus || fallbackEmailStatus(profile)}
        />
        <MfaCard profile={profile} />
      </PageShell>
    );
  }

  return (
    <PageShell
      eyebrow="Аккаунт"
      title="Настройки и безопасность"
      description="Управляй профилем, email, паролем, двухфакторной защитой и активными сессиями в одном месте."
      contentClassName={styles.accountGrid}
    >
      <AccountHero profile={profile} />
      <ProfileCard profile={profile} onUpdated={handleProfileUpdated} />
      <EmailCard initialStatus={emailStatus || fallbackEmailStatus(profile)} />
      <PasswordCard identityHint={profile?.email || profile?.username || ""} />
      <MfaCard profile={profile} />
      <SessionsCard initialSessions={sessionsPayload || { sessions: [] }} />
      <DeleteAccountCard />
    </PageShell>
  );
}
