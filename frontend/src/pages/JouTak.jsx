import { Link } from "react-router-dom";

const JouTak = () => {
  return (
    <div className="text-center">
      <div
        id="carouselExampleInterval"
        className="carousel slide"
        data-bs-ride="carousel"
      >
        <div className="carousel-inner w-100" style={{
          "aspectRatio": "16 / 9"
        }}>
          <div className="carousel-item active" data-bs-interval="10000">
            <img
              src="https://cloud.joutak.ru/s/2oQALeqNkndEQMw/preview"
              className="d-block w-100"
              alt="Центральный район сервера"
            />
          </div>
          <div className="carousel-item" data-bs-interval="10000">
            <img src="https://cloud.joutak.ru/s/fAn6tq8jn3wcbzy/preview" className="d-block w-100" alt="Большой гриб на нулевых координатах" />
          </div>
          <div className="carousel-item" data-bs-interval="10000">
            <img
              src="https://cloud.joutak.ru/s/oD9SmGSnqGCYqLP/preview"
              className="d-block w-100"
              alt="Летучий Голландец в Казахстане"
            />
          </div>
          <div className="carousel-item" data-bs-interval="10000">
            <img
              src="https://cloud.joutak.ru/s/D8MH8Bmia4f6Ab5/preview"
              className="d-block w-100"
              alt="Крупная сходка новых игроков 2025"
            />
          </div>
          <div className="carousel-item" data-bs-interval="10000">
            <img
              src="https://cloud.joutak.ru/s/3ebFJexTFSntZmL/preview"
              className="d-block w-100"
              alt="Центральный хаб в Нижнем мире"
            />
          </div>
        </div>
        <button
          className="carousel-control-prev"
          type="button"
          data-bs-target="#carouselExampleInterval"
          data-bs-slide="prev"
        >
          <span
            className="carousel-control-prev-icon"
            aria-hidden="true"
          ></span>
          <span className="visually-hidden">Previous</span>
        </button>
        <button
          className="carousel-control-next"
          type="button"
          data-bs-target="#carouselExampleInterval"
          data-bs-slide="next"
        >
          <span
            className="carousel-control-next-icon"
            aria-hidden="true"
          ></span>
          <span className="visually-hidden">Next</span>
        </button>
      </div>

      <div className="p-5 mb-4 rounded-3">
        <div className="container pb-5">
          <h1 className="display-5 fw-bold">JouTak</h1>
          <p className="col-md-8 fs-4 lh-xs mx-auto">
            Джоутек&nbsp;&mdash; колыбель итмокрафта. Запускавшийся парой
            школьников как летсплей в&nbsp;2018 году, этот сервер смог пройти
            сквозь года без вайпов, сохранить память и&nbsp;честность. Здесь нет
            ни&nbsp;приватов, ни доната, зато полно историй, построек
            и&nbsp;души. Станешь жить в&nbsp;одном из районов центрального
            города Джойтак или заведёшь друзей, чтобы вместе строить империю?
            Вне зависимости от&nbsp;того, кто ты&nbsp;и&nbsp;откуда, для тебя
            и&nbsp;твоих друзей найдётся место на&nbsp;нашем проекте.
            Регистрируйся, и&nbsp;мы&nbsp;расскажем всё подробнее.
          </p>
          <p className="col-md-8 fs-4 lh-xs mx-auto fw-bold">
            IP: mc.joutak.ru
          </p>
          <a
            className="btn btn-primary btn-lg mt-4"
            href="https://forms.yandex.ru/u/6501f64f43f74f18a8da28de/"
            target="_blank"
            rel="noopener noreferrer"
          >
            Зарегистрироваться на приватном сервере
          </a>
          <br></br>
          <Link className="btn btn-primary btn-lg mt-3" to="/joutak/pay">
            Оплатить проходку
          </Link>
        </div>
      </div>
    </div>
  );
};

export default JouTak;
