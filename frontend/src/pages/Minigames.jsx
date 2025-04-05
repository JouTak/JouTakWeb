const MiniGames = () => {
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
              src="/img/aether-portal.png"
              className="d-block w-100"
              alt="Aether Portal"
            />
          </div>
          <div className="carousel-item" data-bs-interval="10000">
            <img
              src="/img/final-stage.png"
              className="d-block w-100"
              alt="Final Stage"
            />
          </div>
          <div className="carousel-item" data-bs-interval="10000">
            <img
              src="/img/top-players.png"
              className="d-block w-100"
              alt="top players"
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
            Мини-игры — неотъемлемая часть майнкрафта. Сервер JouTak MINIGAMES
            представляет собой как классические игры (тут будут игры), так и
            полностью написанные с нуля. Более того, именно здесь проходит
            спартакиада по майнкрафту!
          </p>
          <a
            className="btn btn-primary btn-lg disabled"
            href="#"
            style={{ pointerEvents: "none" }}
            title="Регистрация еще не началась"
          >
            Зарегистрироаться на спартакиаду
          </a>
          <div className="alert alert-warning mt-3">
            Регистрация пока еще не началась
          </div>
        </div>
      </div>
    </div>
  );
};

export default MiniGames;
