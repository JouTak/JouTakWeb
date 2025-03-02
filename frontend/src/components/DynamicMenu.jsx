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
          <Link className="nav-link" to="http://map.joutak.ru">
            Онлайн карта
          </Link>
        </li>
      </>
    );
  } else if (currentProject === "mini_games" || currentProject === "bed_rock") {
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
