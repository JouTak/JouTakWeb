const ItmoCraft = () => {
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
              src="https://cloud.joutak.ru/s/pj8iiBCcDXabYWM/preview"
              className="d-block w-100"
              alt="Выезд клуба в Ягодное 2025"
            />
          </div>
          <div className="carousel-item" data-bs-interval="10000">
            <img
              src="https://cloud.joutak.ru/s/eZwEndZTJcogxTQ/preview"
              className="d-block w-100"
              alt="Сходка итмокрафта — комьюнити <3"
            />
          </div>
          <div className="carousel-item" data-bs-interval="10000">
            <img src="https://cloud.joutak.ru/s/59F3qBTsMbXm5KD/preview" className="d-block w-100" alt="Здание корпуса на Кронверкском, построенное на сервере" />
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
          <h1 className="display-5 fw-bold">ITMOcraft</h1>
          <p className="col-md-8 fs-4 lh-xs mx-auto">
            Комьюнити итмошников, любящих майнкрафт и&nbsp;всё, что с&nbsp;ним связано.
            Орг.&nbsp;состав итмокрафта занимается разработкой плагинов,
            строительством ивентов, а&nbsp;также медиа.<br />Подавай заявку:
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
