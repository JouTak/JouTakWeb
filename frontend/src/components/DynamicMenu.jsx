import { Button, DropdownMenu } from "@gravity-ui/uikit";
import { useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";

import { useHub } from "../features/hub/context";
import { normalizeRoutePath } from "../routing/pageRegistry";

function NavigationDropdown({ items }) {
  const [open, setOpen] = useState(false);

  return (
    <DropdownMenu
      items={items}
      open={open}
      onOpenToggle={setOpen}
      renderSwitcher={(switcherProps) => (
        <Button
          {...switcherProps}
          view="flat"
          size="m"
          aria-haspopup="menu"
          aria-expanded={open}
        >
          Разделы
        </Button>
      )}
    />
  );
}

export default function DynamicMenu() {
  const { flags } = useHub();
  const location = useLocation();
  const navigate = useNavigate();
  const items = [];

  if (flags.cities_ui) {
    items.push({ text: "Города", action: () => navigate("/cities") });
  }
  if (flags.community_profiles_ui) {
    items.push({ text: "Игроки", action: () => navigate("/players") });
  }
  if (flags.communities_ui) {
    items.push({ text: "Сообщества", action: () => navigate("/communities") });
  }
  if (normalizeRoutePath(location.pathname) === "/joutak") {
    items.push({
      text: "Онлайн-карта JouTak",
      href: "https://map.joutak.ru",
      target: "_blank",
      rel: "noopener noreferrer",
    });
  }

  if (!items.length) return null;

  return <NavigationDropdown key={location.pathname} items={items} />;
}
