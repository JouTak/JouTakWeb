import { Link, useLocation } from "react-router-dom";

import { getProjectByPath } from "../utils/projectUtils";

const DynamicMenu = () => {
  const location = useLocation();
  const currentProject = getProjectByPath(location.pathname);

  if (currentProject === "jou_tak") {
    return (
      <>
        <li className="nav-item">
          <Link className="nav-link" to="#server-info">
            О сервере
          </Link>
        </li>
        <li className="nav-item">
          <a
            className="nav-link"
            href="https://map.joutak.ru"
            rel="noopener noreferrer"
            target="_blank"
          >
            Онлайн карта
          </a>
        </li>
      </>
    );
  } else if (currentProject === "mini_games" || currentProject === "legacy") {
    return (
      <>
        <li className="nav-item">
          <Link className="nav-link" to="#server-info">
            О сервере
          </Link>
        </li>
        <li className="nav-item">
          <Link className="nav-link" to="#server-load">
            Нагрузка сервера
          </Link>
        </li>
      </>
    );
  }
  return null;
};

export default DynamicMenu;
