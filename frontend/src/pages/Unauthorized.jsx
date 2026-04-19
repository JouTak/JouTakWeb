import { useLocation } from "react-router-dom";
import { useState } from "react";
import { Button, ThemeProvider } from "@gravity-ui/uikit";
import { Link } from "react-router-dom";
import { Container } from "react-bootstrap";

const Unauthorized = () => {
  const location = useLocation();
  const params = new URLSearchParams(location.search);

  const reason = params.get("reason");
  const next = params.get("next");

  const [theme, setTheme] = useState("dark");

  return (
    <ThemeProvider theme={theme}>
      <Container className="d-flex flex-column align-items-center gap-2 p-2">
        <h2 className="m-0">401 - Unauthorized</h2>
        <p className="m-0">
          {reason === "auth_required"
            ? "Вы пытаетесь открыть раздел доступный только после входа"
            : "У вас нет доступа к этой странице"}
        </p>
        <div className="d-flex gap-2">
          <Button
            as={Link}
            href={`/login?next=${encodeURIComponent(next)}`}
            view="action"
          >
            Войти
          </Button>
          <Button as={Link} href="/">
            На главную
          </Button>
          <Button
            as={Link}
            onClick={() => setTheme(theme === "dark" ? "light" : "dark")}
          >
            Toggle theme
          </Button>
        </div>
      </Container>
    </ThemeProvider>
  );
};

export default Unauthorized;
