const ItmoCraft = () => {
  return (
    <div className="text-center">
      <div
        id="carouselExampleInterval"
        className="carousel slide"
        data-bs-ride="carousel"
      >
        <div className="carousel-inner">
          <div className="carousel-item active" data-bs-interval="10000">
            <img
              src="/img/itmo-meetup.jpeg"
              className="d-block w-100"
              alt="Сходка итмокрафта"
            />
          </div>
          <div className="carousel-item" data-bs-interval="10000">
            <img
              src="/img/itmo-comunity.jpeg"
              className="d-block w-100"
              alt="Сходка итмокрафта - комьюнити <3"
            />
          </div>
          <div className="carousel-item" data-bs-interval="10000">
            <img src="/img/cronva.png" className="d-block w-100" alt="Кронва" />
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
        <div className="container py-5">
          <h1 className="display-5 fw-bold">ITMOcraft</h1>
          <p className="col-md-8 fs-4 lh-1 mx-auto">
            Комьюнити итмошников, любящих майнкрафт и всё, что с ним связано.
            Орг. состав итмокрафта занимается разработкой плагинов,
            строительством ивентов, а также медиа. Подавай заявку:
          </p>
          <a
            className="btn btn-primary btn-lg"
            href="https://forms.yandex.ru/u/6501f64f43f74f18a8da28de/"
            target="_blank"
            rel="noopener noreferrer"
          >
            Заявка в клуб
          </a>
        </div>
      </div>
    </div>
  );
};

export default ItmoCraft;
