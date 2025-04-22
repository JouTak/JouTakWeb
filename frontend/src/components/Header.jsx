import { useNavigate, useLocation } from "react-router-dom";
import { Select } from "@gravity-ui/uikit";
import { getProjectByPath, getPathByProject } from "../utils/projectUtils";
import DynamicMenu from "./DynamicMenu";

function ProjectSelect() {
  const navigate = useNavigate();
  const location = useLocation();

  const options = [
    { value: "jou_tak", content: "JouTak" },
    {
      value: "mini_games",
      content: "miniGAMES",
    },
    { value: "bed_rock", content: "Bedrock" },
    { value: "itmocraft", content: "ItmoCraft" },
  ];

  const selectedValue = [getProjectByPath(location.pathname)];

  const handleUpdate = (newVal) => {
    const chosen = newVal[0];
    if (!chosen) return;
    const target = getPathByProject(chosen);
    if (target !== location.pathname) {
      navigate(target);
    }
  };

  return (
    <div>
      сервер /&nbsp;
      <Select options={options} value={selectedValue} onUpdate={handleUpdate} />
    </div>
  );
}

const Header = () => {
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

            <button
              className="navbar-toggler"
              type="button"
              data-bs-toggle="offcanvas"
              data-bs-target="#offcanvasDarkNavbar"
              aria-controls="offcanvasDarkNavbar"
              aria-label="Toggle navigation"
            >
              <span className="navbar-toggler-icon"></span>
            </button>
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
          <div className="d-flex align-items-center">
            <button className="btn btn-outline-primary btn-sm" disabled>
              Авторизация
            </button>
          </div>
        </div>
      </div>
    </>
  );
};

export default Header;
