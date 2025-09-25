import { useNavigate, useLocation } from "react-router-dom";
import {
  Select,
  DropdownMenu,
  Button,
  Avatar,
  Loader,
} from "@gravity-ui/uikit";
import { useState, useCallback, useEffect, useMemo } from "react";
import { getProjectByPath, getPathByProject } from "../utils/projectUtils";
import DynamicMenu from "./DynamicMenu";
import AuthModal from "./AuthModal";
import { me, tokenStore, logout } from "../services/api";

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
  const [profile, setProfile] = useState(null);
  const [loadingProfile, setLoadingProfile] = useState(false);

  const hasAnyToken = () => {
    const saved = tokenStore.get();
    return Boolean(saved?.access || saved?.refresh);
  };

  const closeOffcanvas = useCallback(() => {
    const el = document.getElementById("offcanvasDarkNavbar");
    const bs = window.bootstrap;
    if (el && bs?.Offcanvas) {
      let inst = bs.Offcanvas.getInstance(el);
      if (!inst) inst = new bs.Offcanvas(el);
      inst.hide();
    } else {
      document.querySelector("#offcanvasDarkNavbar .btn-close")?.click();
    }
  }, []);

  const openAuth = useCallback(() => {
    closeOffcanvas();
    setAuthOpen(true);
  }, [closeOffcanvas]);

  useEffect(() => {
    const el = document.getElementById("offcanvasDarkNavbar");
    if (el && el.classList.contains("show")) closeOffcanvas();
  }, [location.pathname, closeOffcanvas]);

  const loadProfileIfTokens = useCallback(async () => {
    if (!hasAnyToken()) {
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

  const goSecurity = () => navigate("/account/security");
  const onLogout = () => {
    logout();
    setProfile(null);
  };

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
        text={profile?.username || "?"}
        imgUrl={profile?.avatar_url}
        view="outlined"
        title={profile?.username || "Гость"}
      />
    </Button>
  );

  return (
    <>
      <header>
        <nav className="navbar navbar-dark bg-dark">
          <div className="container container-fluid d-flex justify-content-between align-items-center">
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
                data-bs-toggle="offcanvas"
                data-bs-target="#offcanvasDarkNavbar"
                aria-controls="offcanvasDarkNavbar"
                aria-label="Toggle navigation"
              >
                <span className="navbar-toggler-icon"></span>
              </button>
            </div>
          </div>
        </nav>
      </header>

      <div
        className="offcanvas offcanvas-start text-bg-dark"
        tabIndex="-1"
        id="offcanvasDarkNavbar"
        aria-labelledby="offcanvasDarkNavbarLabel"
      >
        <div className="offcanvas-header">
          <h5 className="offcanvas-title" id="offcanvasDarkNavbarLabel">
            Меню
          </h5>
          <button
            type="button"
            className="btn-close btn-close-white"
            data-bs-dismiss="offcanvas"
            aria-label="Close"
          ></button>
        </div>
        <div className="offcanvas-body">
          <ul className="navbar-nav me-auto mb-2 mb-lg-0">
            <DynamicMenu />
          </ul>
        </div>
      </div>

      <AuthModal open={authOpen} onClose={() => setAuthOpen(false)} />
    </>
  );
};

export default Header;
