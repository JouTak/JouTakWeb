import {
  Avatar,
  Button,
  DropdownMenu,
  Label,
  Loader,
  Modal,
  Select,
} from "@gravity-ui/uikit";
import { useCallback, useEffect, useMemo, useState } from "react";
import Offcanvas from "react-bootstrap/Offcanvas";
import { useLocation, useNavigate } from "react-router-dom";

import {
  AUTH_STATE_EVENT,
  hasStoredAuth,
  logout,
  me,
  readStoredTokens,
} from "../services/api";
import { getProfileDisplayName } from "../utils/accountIdentity";
import {
  getPersonalizationNoticeKey,
  hasSeenPersonalizationNotice,
  isPostSignupPersonalizationSession,
  markPersonalizationNoticeSeen,
} from "../utils/personalizationNotice";
import {
  isLegacyPersonalization,
  isNewRegistrationPersonalization,
  isPersonalizedProfile,
  needsPersonalization,
} from "../utils/profileState";
import { getPathByProject, getProjectByPath } from "../utils/projectUtils";
import AuthModal from "./AuthModal";
import DynamicMenu from "./DynamicMenu";

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
      сервер /&nbsp;
      <Select options={options} value={selectedValue} onUpdate={handleUpdate} />
    </div>
  );
}

const Header = () => {
  const navigate = useNavigate();
  const location = useLocation();

  const [authOpen, setAuthOpen] = useState(false);
  const [menuOpen, setMenuOpen] = useState(false);
  const [profile, setProfile] = useState(null);
  const [loadingProfile, setLoadingProfile] = useState(false);
  const [personalizationModalOpen, setPersonalizationModalOpen] =
    useState(false);
  const [postSignupBannerDismissed, setPostSignupBannerDismissed] =
    useState(false);

  const closeOffcanvas = useCallback(() => setMenuOpen(false), []);

  const openAuth = useCallback(() => {
    closeOffcanvas();
    setAuthOpen(true);
  }, [closeOffcanvas]);

  useEffect(() => {
    setMenuOpen(false);
  }, [location.pathname]);

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
    return () => {
      window.removeEventListener(AUTH_STATE_EVENT, onAuthStateChanged);
    };
  }, [loadProfileIfTokens]);

  const goSecurity = () => navigate("/account/security");
  const goOnboarding = () => navigate("/account/complete-profile");
  const onLogout = useCallback(async () => {
    closeOffcanvas();
    setAuthOpen(false);
    setPersonalizationModalOpen(false);
    try {
      await logout();
    } finally {
      setProfile(null);
      navigate("/joutak", { replace: true });
    }
  }, [closeOffcanvas, navigate]);

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
    isPostSignupPersonalizationSession(profile);

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
      isPostSignupPersonalizationSession(profile)
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
        imgUrl={profile?.avatar_url}
        view="outlined"
        title={getProfileDisplayName(profile)}
      />
    </Button>
  );

  return (
    <>
      <header>
        <nav className="navbar navbar-dark bg-dark">
          <div className="container-fluid d-flex justify-content-between align-items-center px-3 px-lg-4">
            <a className="navbar-brand" href="https://joutak.ru">
              <img
                src="/img/icons/logo.png"
                alt="Logo"
                width="30"
                height="30"
                className="d-inline-block align-text-top"
              />
            </a>

            <div className="mx-auto g-root_theme_dark text-light">
              <ProjectSelect />
            </div>

            <div className="d-flex align-items-center">
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
                    [{ text: "Аккаунт и безопасность", action: goSecurity }],
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

              <button
                className="navbar-toggler ms-2"
                type="button"
                onClick={() => setMenuOpen(true)}
                aria-controls="offcanvasDarkNavbar"
                aria-label="Toggle navigation"
              >
                <span className="navbar-toggler-icon"></span>
              </button>
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

      <Offcanvas
        show={menuOpen}
        onHide={closeOffcanvas}
        placement="start"
        scroll
        id="offcanvasDarkNavbar"
        className="text-bg-dark"
      >
        <Offcanvas.Header closeButton closeVariant="white">
          <Offcanvas.Title id="offcanvasDarkNavbarLabel">Меню</Offcanvas.Title>
        </Offcanvas.Header>
        <Offcanvas.Body>
          <ul className="navbar-nav me-auto mb-2 mb-lg-0">
            <DynamicMenu />
          </ul>
        </Offcanvas.Body>
      </Offcanvas>

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

export default Header;
