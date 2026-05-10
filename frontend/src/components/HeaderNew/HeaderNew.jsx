import { useNavigate, useLocation } from "react-router-dom";
import { DropdownMenu, Button, Loader, Modal, Label } from "@gravity-ui/uikit";
import { useState, useCallback, useEffect, useMemo, useRef } from "react";
import { getPathByProject } from "../../utils/projectUtils";
import AuthModal from "../AuthModal";
import ThemeSwitcher from "../ThemeSwitcher/ThemeSwitcher";
import { AUTH_STATE_EVENT, hasStoredAuth, logout, me } from "../../services/api";
import { isPersonalizedProfile, needsPersonalization } from "../../utils/profileState";
import {
  getProfileDisplayName,
  getProfileIdentityKey,
} from "../../utils/accountIdentity";
import styles from "./HeaderNew.module.css";

const PERSONALIZATION_NOTICE_KEY_PREFIX = "joutak_personalization_notice_v1:";

function ProjectSelect() {
  const navigate = useNavigate();
  const location = useLocation();
  const [isOpen, setIsOpen] = useState(false);
  const menuRef = useRef(null);

  const options = useMemo(
    () => [
      { value: "jou_tak", content: "JouTak" },
      { value: "mini_games", content: "miniGAMES" },
      { value: "legacy", content: "Legacy" },
      { value: "itmo_craft", content: "ITMOcraft" },
    ],
    [],
  );

  const onSelectServer = useCallback(
    (projectKey) => {
      const target = getPathByProject(projectKey);
      setIsOpen(false);
      if (target !== location.pathname) navigate(target);
    },
    [location.pathname, navigate],
  );

  useEffect(() => {
    const onDocumentClick = (event) => {
      if (!menuRef.current?.contains(event.target)) {
        setIsOpen(false);
      }
    };
    document.addEventListener("mousedown", onDocumentClick);
    return () => document.removeEventListener("mousedown", onDocumentClick);
  }, []);

  return (
    <div className={styles.serversSelectRoot} ref={menuRef}>
      <div className={styles.serversBlock}>
        <span>Сервера</span>
        <button
          type="button"
          className={`${styles.serversToggleBtn} ${isOpen ? styles.serversToggleBtnOpen : ""}`}
          aria-label="Открыть список серверов"
          title="Открыть список серверов"
          aria-expanded={isOpen}
          onClick={() => setIsOpen((prev) => !prev)}
        >
          <img src="/img/close-qa-btn.png" alt="" />
        </button>
      </div>

      <div className={`${styles.serversMenu} ${isOpen ? styles.serversMenuOpen : ""}`}>
        {options.map((option) => (
          <button
            key={option.value}
            type="button"
            className={styles.serverOption}
            onClick={() => onSelectServer(option.value)}
          >
            {option.content}
          </button>
        ))}
      </div>
    </div>
  );
}

export default function HeaderNew() {
  const navigate = useNavigate();
  const location = useLocation();

  const [authOpen, setAuthOpen] = useState(false);
  const [profile, setProfile] = useState(null);
  const [loadingProfile, setLoadingProfile] = useState(false);
  const [personalizationModalOpen, setPersonalizationModalOpen] =
    useState(false);

  const loadProfileIfTokens = useCallback(async () => {
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

  const personalizationNoticeKey = useMemo(() => {
    return `${PERSONALIZATION_NOTICE_KEY_PREFIX}${getProfileIdentityKey(profile)}`;
  }, [profile]);

  const closePersonalizationModal = useCallback(
    ({ markSeen = true } = {}) => {
      if (markSeen && getProfileIdentityKey(profile) !== "guest") {
        localStorage.setItem(personalizationNoticeKey, "1");
      }
      setPersonalizationModalOpen(false);
    },
    [personalizationNoticeKey, profile],
  );

  const openPersonalizationFlow = useCallback(() => {
    closePersonalizationModal({ markSeen: true });
    navigate("/account/complete-profile");
  }, [closePersonalizationModal, navigate]);

  useEffect(() => {
    if (!profile || authOpen) return;
    if (location.pathname.startsWith("/account/complete-registration")) return;
    if (location.pathname.startsWith("/account/complete-profile")) return;
    if (location.pathname.startsWith("/account/onboarding")) return;
    if (!needsPersonalization(profile)) return;
    if (profile?.personalization_interstitial_enabled === false) return;
    if (localStorage.getItem(personalizationNoticeKey) === "1") return;
    setPersonalizationModalOpen(true);
  }, [authOpen, location.pathname, personalizationNoticeKey, profile]);

  const renderAccountSwitcher = (switcherProps) => (
    <button
      {...switcherProps}
      type="button"
      aria-label={profile ? "Меню аккаунта" : "Войти"}
      title={profile ? "Меню аккаунта" : "Войти"}
      className={styles.avatarButton}
    >
      <span className={styles.avatarOuter}>
        <span className={styles.avatarInner}>
          {getProfileDisplayName(profile).slice(0, 1).toUpperCase()}
        </span>
      </span>
    </button>
  );

  return (
    <>
      <header className={styles.header}>
        <div className={styles.container}>
          <div className={styles.row}>
            <div className={styles.leftSide}>
              <ThemeSwitcher />
            </div>

            <div className={styles.centerGroup}>
              <button
                type="button"
                className={styles.navButton}
                onClick={() => navigate("/itmocraft")}
              >
                ITMOcraft
              </button>

              <ProjectSelect />

              <button
                type="button"
                className={styles.logoButton}
                onClick={() => navigate("/joutak")}
              >
                <img src="/img/logo-mini.svg" alt="Logo" />
              </button>

              <button type="button" className={styles.navButton}>
                Календарь
              </button>

              <button type="button" className={styles.navButton}>
                Новости
              </button>

            </div>

            <div className={styles.rightSide}>
              <div className={styles.accountArea}>
                {loadingProfile ? (
                  <Loader size="m" />
                ) : profile ? (
                  <DropdownMenu
                    size="m"
                    renderSwitcher={renderAccountSwitcher}
                    items={[
                      ...(!registrationCompleted
                        ? [[{ text: "Завершить профиль", action: goOnboarding }]]
                        : []),
                      [{ text: "Аккаунт и безопасность", action: goSecurity }],
                      { text: "Выйти", action: onLogout, theme: "danger" },
                    ]}
                  />
                ) : (
                  <button
                    type="button"
                    onClick={() => setAuthOpen(true)}
                    aria-label="Войти"
                    title="Войти"
                    className={styles.avatarButton}
                  >
                    <span className={styles.avatarOuter}>
                      <span className={styles.avatarInner} />
                    </span>
                  </button>
                )}
              </div>
            </div>
          </div>
        </div>
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
            Обязательная персонализация профиля
          </h3>
          <p style={{ margin: 0, opacity: 0.9 }}>
            Мы обновили требования профиля. Чтобы использовать часть функций,
            нужно заполнить обязательные данные аккаунта.
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
              Заполнить сейчас
            </Button>
          </div>
        </div>
      </Modal>
    </>
  );
}

