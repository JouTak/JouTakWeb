import {
  useNavigate,
  useLocation,
  useHref,
  useLinkClickHandler,
} from "react-router-dom";
import PropTypes from "prop-types";
import {
  unstable_Breadcrumbs as Breadcrumbs,
  unstable_BreadcrumbsItem as BreadcrumbsItem,
} from "@gravity-ui/uikit/unstable";
import { Select } from "@gravity-ui/uikit";
import { getProjectByPath, getPathByProject } from "../utils/projectUtils";
import DynamicMenu from "./DynamicMenu";

function RouterBreadcrumbItem({ to, children, ...props }) {
  const href = useHref(to);
  const onClick = useLinkClickHandler(to);
  return (
    <BreadcrumbsItem {...props} href={href} onClick={onClick}>
      {children}
    </BreadcrumbsItem>
  );
}

RouterBreadcrumbItem.propTypes = {
  to: PropTypes.oneOfType([PropTypes.string, PropTypes.object]).isRequired,
  children: PropTypes.node.isRequired,
};

function ProjectSelect() {
  const navigate = useNavigate();
  const location = useLocation();

  const options = [
    { value: "jou_tak", content: "JouTak" },
    { value: "mini_games", content: "MiniGame" },
    { value: "bed_rock", content: "Bedrock" },
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
    <Select
      options={options}
      value={selectedValue}
      onUpdate={handleUpdate}
      width="max"
    />
  );
}

const Header = () => {
  return (
    <header>
      <nav className="navbar navbar-expand-lg navbar-dark bg-dark">
        <div className="container">
          <Breadcrumbs
            className="text-white g-root_theme_dark"
            itemComponent={RouterBreadcrumbItem}
            popupStyle="inline"
            showRoot={false}
            separator="/"
            showMoreButton={false}
            style={{
              whiteSpace: "nowrap",
              maxWidth: "100%",
              minWidth: "200px",
            }}
          >
            <RouterBreadcrumbItem to="/" title="server">
              Сервер
            </RouterBreadcrumbItem>
            <BreadcrumbsItem title="Project Select">
              <ProjectSelect />
            </BreadcrumbsItem>
          </Breadcrumbs>

          <button
            className="navbar-toggler"
            type="button"
            data-bs-toggle="collapse"
            data-bs-target="#navbarNav"
            aria-controls="navbarNav"
            aria-expanded="false"
            aria-label="Toggle navigation"
          >
            <span className="navbar-toggler-icon"></span>
          </button>

          <div className="collapse navbar-collapse" id="navbarNav">
            <ul className="navbar-nav ms-auto">
              <DynamicMenu />
            </ul>
          </div>
        </div>
      </nav>
    </header>
  );
};

export default Header;
