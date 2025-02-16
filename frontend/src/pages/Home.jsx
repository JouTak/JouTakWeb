const Home = () => {
  return (
    <div className="text-center">
      <div
        id="carouselExampleInterval"
        className="carousel slide"
        data-bs-ride="carousel"
      >
        <div className="carousel-inner">
          <div className="carousel-item active" data-bs-interval="10000">
            <img src="/img/cronva.png" className="d-block w-100" alt="Кронва" />
          </div>
          <div className="carousel-item" data-bs-interval="10000">
            <img src="/img/forest.png" className="d-block w-100" alt="лес" />
          </div>
          <div className="carousel-item" data-bs-interval="10000">
            <img
              src="/img/mushroom.png"
              className="d-block w-100"
              alt="грибы"
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
        <div className="container py-5">
          <h1 className="display-5 fw-bold">JouTak</h1>
          <p className="col-md-8 fs-4 lh-1 mx-auto">
            JouTak это в первую очередь наш SMP/анархия сервер — место, где
            стабильность важнее всего! Здесь нет вайпов, поэтому ваши постройки
            и достижения остаются с вами навсегда.
          </p>
          <a
            className="btn btn-primary btn-lg"
            href="https://forms.yandex.ru/u/6501f64f43f74f18a8da28de/"
            target="_blank"
            rel="noopener noreferrer"
          >
            Проходка
          </a>
        </div>
      </div>
    </div>
  );
};

export default Home;
