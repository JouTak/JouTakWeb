import ImageCarousel from "../components/ImageCarousel";

const ITMOCRAFT_CAROUSEL_ITEMS = [
  {
    src: "https://cloud.joutak.ru/s/pj8iiBCcDXabYWM/preview",
    alt: "Выезд клуба в Ягодное 2025",
  },
  {
    src: "https://cloud.joutak.ru/s/eZwEndZTJcogxTQ/preview",
    alt: "Сходка итмокрафта — комьюнити <3",
  },
  {
    src: "https://cloud.joutak.ru/s/59F3qBTsMbXm5KD/preview",
    alt: "Здание корпуса на Кронверкском, построенное на сервере",
  },
];

const ItmoCraft = () => {
  return (
    <div className="text-center">
      <ImageCarousel items={ITMOCRAFT_CAROUSEL_ITEMS} />

      <div className="p-5 mb-4 rounded-3">
        <div className="container pb-5">
          <h1 className="display-5 fw-bold">ITMOcraft</h1>
          <p className="col-md-8 fs-4 lh-xs mx-auto">
            Комьюнити итмошников, любящих майнкрафт и&nbsp;всё, что с&nbsp;ним
            связано. Орг.&nbsp;состав итмокрафта занимается разработкой плагинов,
            строительством ивентов, а&nbsp;также медиа.
            <br />
            Подавай заявку:
          </p>
          <a
            className="btn btn-primary btn-lg"
            href="https://forms.yandex.ru/u/67773408068ff0452320c8b4/"
            target="_blank"
            rel="noopener noreferrer"
          >
            Подать заявку в команду организаторов
          </a>
        </div>
      </div>
    </div>
  );
};

export default ItmoCraft;
