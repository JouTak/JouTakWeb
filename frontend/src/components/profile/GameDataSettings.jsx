import { Button } from "@gravity-ui/uikit";
import { useState } from "react";

import { getGameData } from "../../services/api/profilesApi";
import { ResourceState } from "../hub/HubShell";
import useResource from "../hub/useResource";
import GameDataEditor from "./GameDataEditor";

export default function GameDataSettings({ onSaved }) {
  const resource = useResource(getGameData);
  const [section, setSection] = useState(null);
  return (
    <section className="hub-panel">
      <h2>Игровые и учётные данные</h2>
      <p className="hub-muted">
        Данные прежней анкеты аккаунта. Их изменение не меняет аудиторию
        профиля.
      </p>
      <ResourceState resource={resource}>
        {resource.data && (
          <>
            {[
              {
                key: "game",
                title: "Minecraft",
                value: resource.data.minecraft_nick || "Ник не указан",
              },
              {
                key: "itmo",
                title: "ИТМО",
                value:
                  resource.data.is_itmo_student === true
                    ? "Студент ИТМО"
                    : resource.data.is_itmo_student === false
                      ? "Не студент ИТМО"
                      : "Не указано",
              },
            ].map((item) => (
              <div key={item.key} className="hub-row">
                <div>
                  <b>{item.title}</b>
                  <p className="hub-muted">{item.value}</p>
                </div>
                <Button size="s" onClick={() => setSection(item.key)}>
                  Изменить {item.title}
                </Button>
              </div>
            ))}
            <details>
              <summary>VK из прежней анкеты</summary>
              <p>
                Сохранён для учётных процессов. Публикацией управляет раздел
                контактов выше.
              </p>
              <Button size="s" onClick={() => setSection("social")}>
                Изменить учётный VK
              </Button>
            </details>
            {section && (
              <GameDataEditor
                key={`${resource.data.username}:${section}`}
                profile={resource.data}
                section={section}
                onClose={() => setSection(null)}
                onSaved={() => {
                  setSection(null);
                  resource.reload();
                  onSaved?.();
                }}
              />
            )}
          </>
        )}
      </ResourceState>
    </section>
  );
}
