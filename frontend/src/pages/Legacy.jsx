const Legacy = () => {
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
              src="https://cloud.joutak.ru/s/2nmyGq7ayfQpWfe/download"
              className="d-block w-100"
              alt="Сходка игроков в деревне"
            />
          </div>
          <div className="carousel-item" data-bs-interval="10000">
            <img src="https://cloud.joutak.ru/s/DBJpmG2DjrSnXyS/download" className="d-block w-100" alt="Портал в рай" />
          </div>
          <div className="carousel-item" data-bs-interval="10000">
            <img src="https://cloud.joutak.ru/s/6BgqZdrr9LyinAB/download" className="d-block w-100" alt="Деревня" />
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
          <h1 className="display-5 fw-bold">ITMOcraft Legacy</h1>
          <p className="col-md-8 fs-4 lh-xs mx-auto">
            Наше ностальгическое направление. Тут проходят аутентичные ивенты.
            Доступ у всех игроков с Джоутека.
          </p>
          <p className="col-md-8 fs-4 lh-xs mx-auto fw-bold">IP: legacy.joutak.ru:42181</p>
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
