import { Button, TextInput } from "@gravity-ui/uikit";
import { useCallback, useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";

import { HubPage, Pager, ResourceState } from "../../components/hub/HubShell";
import useResource from "../../components/hub/useResource";
import PlayerCard from "../../components/profile/PlayerCard";
import { useHub } from "../../features/hub/context";
import { findPlayers } from "../../services/api/playersApi";

export default function Players() {
  const [params, setParams] = useSearchParams();
  const { viewer } = useHub();
  const q = params.get("q") || "";
  const following = params.get("view") === "following";
  const page = Math.max(1, Math.min(1000, Number(params.get("page")) || 1));
  const [query, setQuery] = useState(q);
  useEffect(() => setQuery(q), [q]);
  const resource = useResource(
    useCallback(
      () => findPlayers({ q, page, following }),
      [q, page, following],
    ),
  );
  function changePage(next) {
    const nextParams = new URLSearchParams(params);
    nextParams.set("page", String(next));
    setParams(nextParams);
  }
  function search(event) {
    event.preventDefault();
    const next = new URLSearchParams();
    if (query.trim()) next.set("q", query.trim());
    if (following) next.set("view", "following");
    setParams(next);
  }
  return (
    <HubPage
      title="Игроки"
      intro="Найдите знакомых, познакомьтесь с соседями и соберите свой круг общения."
    >
      <nav className="hub-tabs" aria-label="Поиск игроков">
        <Link to="/players" aria-current={!following ? "page" : undefined}>
          Все игроки
        </Link>
        {viewer?.is_authenticated && (
          <Link
            to="/players?view=following"
            aria-current={following ? "page" : undefined}
          >
            Мои подписки
          </Link>
        )}
      </nav>
      <form className="player-search" onSubmit={search} role="search">
        <label htmlFor="player-search">
          Имя, логин или ник Minecraft
          <TextInput
            id="player-search"
            value={query}
            onUpdate={setQuery}
            maxLength={100}
            placeholder="Найти игрока"
            hasClear
          />
        </label>
        <Button type="submit" view="action" size="l">
          Найти
        </Button>
      </form>
      <p className="hub-muted">
        Здесь видны только профили, доступные вам. Контакты открываются на
        странице игрока.
      </p>
      <ResourceState resource={resource}>
        {resource.data && (
          <>
            <p role="status">
              {following ? "В ваших подписках" : "Найдено игроков"}:{" "}
              {resource.data.total}
            </p>
            <div className="players-grid">
              {resource.data.items.map((player) => (
                <PlayerCard
                  key={player.username}
                  player={player}
                  onFollowChanged={following ? resource.reload : undefined}
                />
              ))}
            </div>
            {!resource.data.total && (
              <div className="hub-empty">
                <h2>
                  {following
                    ? "Здесь появятся ваши знакомые"
                    : "Никого не нашли"}
                </h2>
                <p>
                  {following
                    ? "Подпишитесь на игрока в его профиле, чтобы быстро находить его снова."
                    : "Попробуйте другое имя. Закрытые профили не отображаются в поиске."}
                </p>
                <Link to="/players">Показать всех игроков →</Link>
              </div>
            )}
            <Pager
              page={page}
              total={resource.data.total}
              onChange={changePage}
            />
          </>
        )}
      </ResourceState>
    </HubPage>
  );
}
