import { Button } from "@gravity-ui/uikit";
import { useNavigate } from "react-router-dom";

import { StatePage } from "../components/ui/PageShell.jsx";

export default function NotFound() {
  const navigate = useNavigate();

  return (
    <StatePage
      eyebrow="Ошибка 404"
      icon="404"
      title="Такой страницы нет"
      description="Возможно, адрес устарел или в нём есть опечатка. Вернись в ITMOcraft или выбери нужный проект."
      actions={
        <>
          <Button view="action" size="l" onClick={() => navigate("/")}>
            На главную ITMOcraft
          </Button>
          <Button view="outlined" size="l" onClick={() => navigate("/joutak")}>
            Перейти к JouTak
          </Button>
        </>
      }
    />
  );
}
