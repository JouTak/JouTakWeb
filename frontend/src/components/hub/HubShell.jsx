import "./hub.css";

import { Button, Loader } from "@gravity-ui/uikit";
import { useEffect } from "react";
import { Link } from "react-router-dom";

import { useHub } from "../../features/hub/context";
import { extractErrorMessage } from "../../services/errors";

export function HubPage({
  title,
  intro,
  children,
  account = false,
  hero = false,
}) {
  useEffect(() => {
    const before = document.title;
    document.title = `${title} · JouTak`;
    return () => {
      document.title = before;
    };
  }, [title]);
  return (
    <div className="hub-page">
      {account && (
        <Link className="hub-back" to="/account">
          ← Личный кабинет
        </Link>
      )}
      {!hero && (
        <header className="hub-heading">
          <h1>{title}</h1>
          {intro && <p>{intro}</p>}
        </header>
      )}
      {children}
    </div>
  );
}

export function ResourceState({ resource, children }) {
  if (resource.loading)
    return (
      <div role="status" className="hub-state">
        <Loader />
        <span>Загрузка…</span>
      </div>
    );
  if (resource.error)
    return (
      <div role="alert" className="hub-panel">
        <h2>Не удалось открыть раздел</h2>
        <p>{extractErrorMessage(resource.error)}</p>
        <Button onClick={resource.reload}>Повторить</Button>
      </div>
    );
  return children;
}

export function HubGate({ flag, children }) {
  const { flags, loading, error, reload } = useHub();
  if (loading)
    return (
      <div className="hub-state" role="status">
        <Loader />
        <span>Загрузка…</span>
      </div>
    );
  if (!flags[flag])
    return (
      <HubPage title="Раздел пока недоступен">
        <p>
          {error
            ? "Не удалось проверить доступность раздела. Обновите страницу."
            : "Этот раздел ещё не включён для вашего аккаунта."}
        </p>
        {error && <Button onClick={reload}>Повторить проверку</Button>}
        <Link to="/">На главную</Link>
      </HubPage>
    );
  return children;
}

export function Pager({ page, total, onChange, size = 24 }) {
  if (total <= size) return null;
  return (
    <nav className="hub-actions" aria-label="Страницы списка">
      <Button disabled={page <= 1} onClick={() => onChange(page - 1)}>
        Назад
      </Button>
      <span>Страница {page}</span>
      <Button
        disabled={page * size >= total}
        onClick={() => onChange(page + 1)}
      >
        Далее
      </Button>
    </nav>
  );
}
