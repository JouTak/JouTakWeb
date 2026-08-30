import ContactCategory from "../../components/ContactElements/ContactCategory";
import { usePageDocument } from "../../features/pageDocument/pageDocumentContext";
import styles from "./Contact.module.scss";

const PUBLIC_IMG_BASE = "https://storage.yandexcloud.net/joutak-public/img";

const CONTACTS_DATA = [
  {
    title: "Самые свежие новости:",
    contactsData: [
      {
        link: "https://t.me/+HHAU5go3GqIzYmI6",
        label: "телеграм-канал",
        iconPath: "/img/icons/new-telegram.svg",
      },
      {
        link: "https://vk.ru/itmocraft",
        label: "группа вконтакте",
        iconPath: "/img/icons/new-vk.svg",
      },
    ],
  },
  {
    title: "Стать частью комьюнити:",
    contactsData: [
      {
        link: "https://forms.yandex.ru/u/6501f64f43f74f18a8da28de/",
        label: "как игрок",
        iconPath: "/img/icons/new-site.svg",
      },
      {
        link: "https://github.com/JouTak",
        label: "нечто большее",
        iconPath: "/img/icons/new-github.svg",
      },
    ],
  },
  {
    title: "Игровое сообщество:",
    contactsData: [
      {
        link: "https://discord.gg/hb39z5TfBW",
        label: "сервер в дискорд",
        iconPath: "/img/icons/new-discord.svg",
      },
      {
        link: "https://wiki.joutak.ru",
        label: "наша wiki",
        iconPath: "/img/icons/new-wiki.svg",
      },
    ],
  },
  {
    title: "Интересные видео от нас:",
    contactsData: [
      {
        link: "https://www.tiktok.com/@joutaksmp",
        label: "аккаунт в тиктоке",
        iconPath: "/img/icons/new-tiktok.svg",
      },
      {
        link: "https://www.youtube.com/@itmocraft",
        label: "ютуб-канал",
        iconPath: "/img/icons/new-youtube.svg",
      },
    ],
  },
];

export default function Contact() {
  const { document, loading } = usePageDocument();
  if (loading && !document) {
    return <div className="py-5 text-center text-secondary">Загрузка...</div>;
  }

  return document?.effective_page_variant === "v2" ? (
    <div className={styles.contactMain}>
      <h1>НАШИ КОНТАКТЫ</h1>
      {CONTACTS_DATA.map((contactData, index) => {
        return <ContactCategory {...contactData} key={index} />;
      })}
    </div>
  ) : (
    <div
      className="p-5 mb-4 bg-light shadow-lg position-relative"
      style={{
        backgroundImage: `url(${PUBLIC_IMG_BASE}/joutak_1.png)`,
        backgroundSize: "cover",
        backgroundPosition: "center",
        position: "relative",
      }}
    >
      <div
        style={{
          position: "absolute",
          top: 0,
          left: 0,
          width: "100%",
          height: "100%",
          backgroundColor: "rgba(0, 0, 0, 0.5)",
          zIndex: 1,
        }}
      ></div>

      <div
        className="container pt-5 text-white position-relative"
        style={{ zIndex: 2 }}
      >
        <h1 className="display-5 fw-bold">Наши сообщества</h1>
        <p className="col-md-10 fs-4 lh-xs">
          Подпишись, чтобы быть в курсе новостей Джоутека, <br></br>ИТМОкрафта и
          майнкрафта!
        </p>
        <div className="d-flex justify-content-center gap-3 my-4">
          <a href="https://t.me/+HHAU5go3GqIzYmI6" rel="noopener noreferrer">
            <img
              src="/img/icons/tg.svg"
              alt="Telegram"
              className="social-icon"
            />
          </a>
          <a
            href="https://vk.com/itmocraft"
            target="_blank"
            rel="noopener noreferrer"
          >
            <img src="/img/icons/vk.svg" alt="VK" className="social-icon" />
          </a>
          <a
            href="https://discord.gg/YVj5tckahA"
            target="_blank"
            rel="noopener noreferrer"
          >
            <img
              src="/img/icons/discord.svg"
              alt="Discord"
              className="social-icon"
            />
          </a>
        </div>
        <div className="container position-relative d-flex justify-content-end mt-3">
          <a className="btn btn-primary btn-lg" href="https://joutak.ru/joutak">
            Узнать больше о JouTak
          </a>
        </div>
      </div>
    </div>
  );
}
