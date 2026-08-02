import { Button } from "@gravity-ui/uikit";
import { useNavigate } from "react-router-dom";

import {
  PageActions,
  PagePanel,
  PageShell,
} from "../components/ui/PageShell.jsx";
import styles from "./Contact.module.css";

const communities = [
  {
    description: "Анонсы событий, быстрые обновления и общение участников.",
    href: "https://t.me/+HHAU5go3GqIzYmI6",
    icon: "/img/icons/tg.svg",
    label: "Telegram",
  },
  {
    description: "Новости клуба, фотографии и материалы ITMOcraft.",
    href: "https://vk.com/itmocraft",
    icon: "/img/icons/vk.svg",
    label: "VK",
  },
  {
    description: "Голосовые каналы, игровые сборы и живое сообщество.",
    href: "https://discord.gg/YVj5tckahA",
    icon: "/img/icons/discord.svg",
    label: "Discord",
  },
];

export default function Contact() {
  const navigate = useNavigate();

  return (
    <PageShell
      eyebrow="Сообщество"
      title="Остаёмся на связи"
      description="Выбирай удобную площадку, следи за событиями ITMOcraft и находи людей для следующей игры."
    >
      <div className={styles.grid}>
        {communities.map((community) => (
          <a
            key={community.label}
            className={styles.community}
            href={community.href}
            target="_blank"
            rel="noopener noreferrer"
          >
            <img src={community.icon} alt="" />
            <span className={styles.communityText}>
              <strong>{community.label}</strong>
              <span>{community.description}</span>
            </span>
            <span className={styles.external} aria-hidden="true">
              ↗
            </span>
          </a>
        ))}
      </div>

      <PagePanel className={styles.helpPanel}>
        <div>
          <h2>Ищешь конкретный проект?</h2>
          <p>
            У каждого направления своя роль: ITMOcraft объединяет сообщество,
            JouTak отвечает за survival-сервер, а MiniGames — за игровые
            события.
          </p>
        </div>
        <PageActions>
          <Button view="action" size="l" onClick={() => navigate("/")}>
            Об ITMOcraft
          </Button>
          <Button view="outlined" size="l" onClick={() => navigate("/joutak")}>
            О сервере JouTak
          </Button>
          <Button
            view="outlined"
            size="l"
            onClick={() => navigate("/minigames")}
          >
            MiniGames
          </Button>
        </PageActions>
      </PagePanel>
    </PageShell>
  );
}
