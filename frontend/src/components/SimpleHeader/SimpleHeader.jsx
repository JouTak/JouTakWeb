import {
  Avatar,
  Button,
  DropdownMenu,
  Label,
  Loader,
  Modal,
  Select,
} from "@gravity-ui/uikit";
import { useCallback, useEffect, useId, useMemo, useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";

import { useHub } from "../../features/hub/context";
import { PROFILE_CHANGED_EVENT } from "../../features/hub/profileEvents";
import {
  AUTH_STATE_EVENT,
  hasStoredAuth,
  logout,
  me,
  readStoredTokens,
} from "../../services/api";
import { safeHubImageUrl } from "../../services/urlSafety";
import { getProfileDisplayName } from "../../utils/accountIdentity";
import {
  getPersonalizationNoticeKey,
  hasSeenPersonalizationNotice,
  isPostSignupPersonalizationSession,
  markPersonalizationNoticeSeen,
} from "../../utils/personalizationNotice";
import {
  isLegacyPersonalization,
  isNewRegistrationPersonalization,
  isPersonalizedProfile,
  needsPersonalization,
} from "../../utils/profileState";
import {
  getPathByProject,
  getProjectByPath,
  isProjectLandingPath,
} from "../../utils/projectUtils";
import AuthModal from "../AuthModal";
import DynamicMenu from "../DynamicMenu";
import styles from "./SimpleHeader.module.css";

function isPersonalizationFlowPath(pathname) {
  return (
    pathname.startsWith("/account/complete-registration") ||
    pathname.startsWith("/account/complete-profile") ||
    pathname.startsWith("/account/onboarding")
  );
}

function ProjectSelect() {
  const navigate = useNavigate();
  const location = useLocation();
  const selectId = useId();

  const options = useMemo(
    () => [
      { value: "jou_tak", content: "JouTak" },
      { value: "mini_games", content: "miniGAMES" },
      { value: "legacy", content: "Legacy" },
      { value: "itmo_craft", content: "ITMOcraft" },
    ],
    [],
  );

  const selectedValue = [getProjectByPath(location.pathname)];
  const handleUpdate = (newVal) => {
    const chosen = newVal[0];
    if (!chosen) return;
    const target = getPathByProject(chosen);
    if (target !== location.pathname) navigate(target);
  };

  return (
    <div>
      <label htmlFor={selectId}>сервер /&nbsp;</label>
      <Select
        id={selectId}
        title="Выбор сервера"
        options={options}
        value={selectedValue}
        onUpdate={handleUpdate}
      />
    </div>
  );
}

const SimpleHeader = () => {
  const navigate = useNavigate();
  const location = useLocation();

  const [authOpen, setAuthOpen] = useState(false);
  const [profile, setProfile] = useState(null);
  const [loadingProfile, setLoadingProfile] = useState(false);
  const [personalizationModalOpen, setPersonalizationModalOpen] =
    useState(false);
  const [postSignupBannerDismissed, setPostSignupBannerDismissed] =
    useState(false);

  const openAuth = useCallback(() => {
    setAuthOpen(true);
  }, []);

  useEffect(() => {
    setPostSignupBannerDismissed(false);
  }, [profile?.email, profile?.username]);

  const loadProfileIfTokens = useCallback(async () => {
    const tokens = readStoredTokens();
    if (tokens?.pending_mfa) {
      setProfile(null);
      setLoadingProfile(false);
      return;
    }
    if (!hasStoredAuth()) {
      setProfile(null);
      return;
    }
    setLoadingProfile(true);
    try {
      const p = await me();
      setProfile(p);
    } catch {
      setProfile(null);
    } finally {
      setLoadingProfile(false);
    }
  }, []);

  useEffect(() => {
    loadProfileIfTokens();
  }, [loadProfileIfTokens]);
  useEffect(() => {
    if (!authOpen) loadProfileIfTokens();
  }, [authOpen, loadProfileIfTokens]);
  useEffect(() => {
    const onAuthStateChanged = () => {
      loadProfileIfTokens();
    };
    window.addEventListener(AUTH_STATE_EVENT, onAuthStateChanged);
    window.addEventListener(PROFILE_CHANGED_EVENT, onAuthStateChanged);
    return () => {
      window.removeEventListener(AUTH_STATE_EVENT, onAuthStateChanged);
      window.removeEventListener(PROFILE_CHANGED_EVENT, onAuthStateChanged);
    };
  }, [loadProfileIfTokens]);

  const { flags: hubFlags } = useHub();
  const goSecurity = () => navigate("/account/security");
  const goOnboarding = () => navigate("/account/complete-profile");
  const onLogout = useCallback(async () => {
    setAuthOpen(false);
    setPersonalizationModalOpen(false);
    try {
      await logout();
    } finally {
      setProfile(null);
      navigate("/joutak", { replace: true });
    }
  }, [navigate]);

  const registrationCompleted = useMemo(
    () => isPersonalizedProfile(profile),
    [profile],
  );
  const legacyPersonalization = isLegacyPersonalization(profile);
  const showPostSignupBanner =
    profile &&
    !authOpen &&
    !postSignupBannerDismissed &&
    !isPersonalizationFlowPath(location.pathname) &&
    needsPersonalization(profile) &&
    isNewRegistrationPersonalization(profile) &&
    isPostSignupPersonalizationSession();

  const personalizationNoticeKey = useMemo(() => {
    return getPersonalizationNoticeKey(profile);
  }, [profile]);

  const closePersonalizationModal = useCallback(
    ({ markSeen = true } = {}) => {
      if (markSeen) markPersonalizationNoticeSeen(profile);
      setPersonalizationModalOpen(false);
    },
    [profile],
  );

  const openPersonalizationFlow = useCallback(() => {
    closePersonalizationModal({ markSeen: true });
    navigate("/account/complete-profile");
  }, [closePersonalizationModal, navigate]);

  const openRegistrationSetup = useCallback(() => {
    navigate("/account/complete-registration");
  }, [navigate]);

  useEffect(() => {
    if (!profile || authOpen) return;
    if (isPersonalizationFlowPath(location.pathname)) return;
    if (!needsPersonalization(profile)) return;
    if (profile?.personalization_interstitial_enabled === false) return;
    if (
      !isLegacyPersonalization(profile) &&
      isPostSignupPersonalizationSession()
    ) {
      return;
    }
    if (hasSeenPersonalizationNotice(profile)) return;
    setPersonalizationModalOpen(true);
  }, [authOpen, location.pathname, personalizationNoticeKey, profile]);

  useEffect(() => {
    if (isPersonalizationFlowPath(location.pathname)) {
      setPersonalizationModalOpen(false);
    }
  }, [location.pathname]);

  const renderAccountSwitcher = (switcherProps) => (
    <Button
      {...switcherProps}
      size="m"
      view="flat"
      aria-label={profile ? "Меню аккаунта" : "Войти"}
      title={profile ? "Меню аккаунта" : "Войти"}
      style={{ padding: 0, borderRadius: 12 }}
      className="ms-2"
    >
      <Avatar
        size="m"
        text={getProfileDisplayName(profile)}
        imgUrl={safeHubImageUrl(profile?.avatar_url)}
        view="outlined"
        title={getProfileDisplayName(profile)}
      />
    </Button>
  );

  return (
    <>
      <header>
        <nav
          className="navbar navbar-dark bg-dark"
          aria-label="Основная навигация"
        >
          <div
            className={`container-fluid d-flex justify-content-between align-items-center px-3 px-lg-4 ${styles.navigation}`}
          >
            <Link className="navbar-brand" to="/" aria-label="На главную">
              <img
                src="/img/icons/logo.png"
                alt="JouTak"
                width="30"
                height="30"
                className="d-inline-block align-text-top"
              />
            </Link>

            {isProjectLandingPath(location.pathname) && (
              <div className={styles.projectSelect}>
                <ProjectSelect />
              </div>
            )}

            <div className="d-flex align-items-center">
              <DynamicMenu />
              {loadingProfile ? (
                <Loader size="m" className="ms-2" />
              ) : profile ? (
                <DropdownMenu
                  size="m"
                  renderSwitcher={renderAccountSwitcher}
                  items={[
                    ...(!registrationCompleted
                      ? [
                          [
                            {
                              text: "Завершить профиль",
                              action: goOnboarding,
                            },
                          ],
                        ]
                      : []),
                    ...(hubFlags.community_profiles_ui
                      ? [
                          [
                            {
                              text: "Личный кабинет",
                              action: () => navigate("/account"),
                            },
                            {
                              text: "Игроки",
                              action: () => navigate("/players"),
                            },
                            {
                              text: "Профиль",
                              action: () =>
                                navigate(
                                  `/u/${encodeURIComponent(profile.username)}`,
                                ),
                            },
                          ],
                        ]
                      : []),
                    ...(hubFlags.communities_ui
                      ? [
                          [
                            {
                              text: "Сообщества",
                              action: () => navigate("/account/communities"),
                            },
                          ],
                        ]
                      : []),
                    [{ text: "Безопасность", action: goSecurity }],
                    { text: "Выйти", action: onLogout, theme: "danger" },
                  ]}
                />
              ) : (
                <Button
                  size="m"
                  view="flat"
                  onClick={openAuth}
                  aria-label="Войти"
                  title="Войти"
                  className="ms-2"
                  style={{ padding: 0, borderRadius: 12 }}
                >
                  <Avatar size="m" text="?" view="outlined" title="Гость" />
                </Button>
              )}
            </div>
          </div>
        </nav>
        {showPostSignupBanner && (
          <div
            style={{
              borderBottom: "1px solid rgba(255, 190, 92, 0.35)",
              background: "rgba(255, 163, 0, 0.12)",
              padding: "10px 16px",
            }}
          >
            <div
              className="container-fluid"
              style={{
                display: "flex",
                alignItems: "center",
                justifyContent: "space-between",
                gap: 12,
                flexWrap: "wrap",
              }}
            >
              <div style={{ display: "grid", gap: 2 }}>
                <b>Аккаунт создан. Осталось завершить регистрацию.</b>
                <span style={{ opacity: 0.85 }}>
                  Публичные разделы доступны, а профиль и персональные функции
                  откроются после 2 коротких шагов.
                </span>
              </div>
              <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
                <Button view="action" onClick={openRegistrationSetup}>
                  Завершить
                </Button>
                <Button
                  view="flat"
                  onClick={() => setPostSignupBannerDismissed(true)}
                >
                  Позже
                </Button>
              </div>
            </div>
          </div>
        )}
      </header>

      <AuthModal open={authOpen} onClose={() => setAuthOpen(false)} />

      <Modal
        open={personalizationModalOpen}
        onClose={() => closePersonalizationModal({ markSeen: true })}
        disableBodyScrollLock
        aria-labelledby="personalization-modal-title"
        style={{ "--g-modal-width": "620px" }}
      >
        <div style={{ padding: 24, display: "grid", gap: 12 }}>
          <h3 id="personalization-modal-title" style={{ margin: 0 }}>
            {legacyPersonalization
              ? "Нужно обновить данные профиля"
              : "Завершите регистрацию"}
          </h3>
          <p style={{ margin: 0, opacity: 0.9 }}>
            {legacyPersonalization
              ? "Мы обновили требования профиля. Чтобы использовать часть функций, нужно заполнить обязательные данные аккаунта."
              : "Чтобы открыть профиль и персональные функции, заполните 2 коротких шага персонализации."}
          </p>
          <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
            <Label theme="warning" size="s">
              Пока профиль базовый, часть действий будет ограничена
            </Label>
            {Array.isArray(profile?.missing_fields) &&
              profile.missing_fields.length > 0 && (
                <Label theme="danger" size="s">
                  Осталось заполнить: {profile.missing_fields.length}
                </Label>
              )}
          </div>
          <div
            style={{
              display: "flex",
              justifyContent: "flex-end",
              gap: 8,
              marginTop: 4,
            }}
          >
            <Button
              view="flat"
              onClick={() => closePersonalizationModal({ markSeen: true })}
            >
              Позже
            </Button>
            <Button view="action" onClick={openPersonalizationFlow}>
              {legacyPersonalization ? "Заполнить сейчас" : "Завершить"}
            </Button>
          </div>
        </div>
      </Modal>
    </>
  );
};

export default SimpleHeader;
