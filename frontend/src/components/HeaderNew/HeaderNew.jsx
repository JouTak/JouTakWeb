import { Button, DropdownMenu, Label, Loader, Modal } from "@gravity-ui/uikit";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";

import { useAuthProfile } from "../../hooks/useAuthProfile";
import { logout } from "../../services/api";
import { getProfileDisplayName } from "../../utils/accountIdentity";
import {
  getPersonalizationNoticeKey,
  hasSeenPersonalizationNotice,
  markPersonalizationNoticeSeen,
} from "../../utils/personalizationNotice";
import {
  isPersonalizedProfile,
  needsPersonalization,
} from "../../utils/profileState";
import { getPathByProject } from "../../utils/projectUtils";
import AuthModal from "../AuthModal";
import ThemeSwitcher from "../ThemeSwitcher/ThemeSwitcher";
import styles from "./HeaderNew.module.scss";

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
      { value: "modex", content: "Modex" },
    ],
    [],
  );

  const onSelectServer = useCallback(
    (projectKey) => {
      const target = getPathByProject(projectKey);
      setIsOpen(false);
      if (!target) return;
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

      <div
        className={`${styles.serversMenu} ${isOpen ? styles.serversMenuOpen : ""}`}
        aria-hidden={!isOpen}
      >
        {options.map((option) => (
          <button
            key={option.value}
            type="button"
            className={styles.serverOption}
            tabIndex={isOpen ? 0 : -1}
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
  const { profile, loadingProfile } = useAuthProfile(authOpen);
  const [dismissedNoticeKey, setDismissedNoticeKey] = useState(null);
  const personalizationNoticeKey = getPersonalizationNoticeKey(profile);

  const goSecurity = () => navigate("/account/security");
  const goOnboarding = () => navigate("/account/complete-profile");

  const onLogout = useCallback(async () => {
    setAuthOpen(false);
    try {
      await logout();
    } finally {
      navigate("/joutak", { replace: true });
    }
  }, [navigate]);

  const registrationCompleted = useMemo(
    () => isPersonalizedProfile(profile),
    [profile],
  );

  const closePersonalizationModal = useCallback(
    ({ markSeen = true } = {}) => {
      if (markSeen) {
        markPersonalizationNoticeSeen(profile);
      }
      setDismissedNoticeKey(getPersonalizationNoticeKey(profile));
    },
    [profile],
  );

  const openPersonalizationFlow = useCallback(() => {
    closePersonalizationModal({ markSeen: true });
    navigate("/account/complete-profile");
  }, [closePersonalizationModal, navigate]);

  const personalizationModalOpen = Boolean(
    profile &&
    !authOpen &&
    !/^\/account\/(complete-registration|complete-profile|onboarding)/.test(
      location.pathname,
    ) &&
    needsPersonalization(profile) &&
    profile.personalization_interstitial_enabled !== false &&
    dismissedNoticeKey !== personalizationNoticeKey &&
    !hasSeenPersonalizationNotice(profile),
  );

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
            <div className={styles.side}>
              <ThemeSwitcher />
            </div>

            <div className={styles.centerGroup}>
              <div className={styles.leftNavGroup}>
                <button
                  type="button"
                  className={styles.navButton}
                  onClick={() => navigate("/")}
                >
                  ITMOcraft
                </button>

                <ProjectSelect />
              </div>

              <button
                type="button"
                className={styles.logoButton}
                onClick={() => navigate("/joutak")}
              >
                <img src="/img/logo-mini.svg" alt="Logo" />
              </button>

              <div className={styles.rightNavGroup}>
                <button type="button" className={styles.navButton}>
                  Календарь
                </button>

                <button type="button" className={styles.navButton}>
                  Новости
                </button>
              </div>
            </div>

            <div className={styles.sideRight}>
              <div className={styles.accountArea}>
                {loadingProfile ? (
                  <Loader size="m" />
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
