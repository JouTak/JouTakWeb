import ImageCarousel from "../components/ImageCarousel";

const PUBLIC_IMG_BASE = "https://storage.yandexcloud.net/joutak-public/img";

const LEGACY_CAROUSEL_ITEMS = [
  {
    src: `${PUBLIC_IMG_BASE}/legacy_1.png`,
    alt: "Сходка игроков в деревне",
  },
  {
    src: `${PUBLIC_IMG_BASE}/legacy_2.png`,
    alt: "Портал в рай",
  },
  {
    src: `${PUBLIC_IMG_BASE}/legacy_3.png`,
    alt: "Деревня",
  },
];

const Legacy = () => {
  return (
    <div className="text-center">
      <ImageCarousel items={LEGACY_CAROUSEL_ITEMS} />

      <div className="p-5 mb-4 rounded-3">
        <div className="container pb-5">
          <h1 className="display-5 fw-bold">ITMOcraft Legacy</h1>
          <p className="col-md-8 fs-4 lh-xs mx-auto">
            Наше ностальгическое направление. Тут проходят аутентичные ивенты.
            Доступ у всех игроков с Джоутека.
          </p>
          <p className="col-md-8 fs-4 lh-xs mx-auto fw-bold">
            IP: legacy.joutak.ru:42181
          </p>
          <a
            className="btn btn-primary btn-lg"
            href="https://forms.yandex.ru/u/6501f64f43f74f18a8da28de/"
            target="_blank"
            rel="noopener noreferrer"
          >
            Попасть на сервер
          </a>
        </div>
      </div>
    </div>
  );
};

export default Legacy;
