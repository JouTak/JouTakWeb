import "react";

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
              alt="Top Players"
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

      <div className="container py-3">
        <div className="my-4">
          <img
            src="/img/logoMiniGames.jpg"
            alt="MiniGames Logo"
            style={{ height: "100px" }}
          />
        </div>
        <p className="col-md-8 fs-4 lh-1 mx-auto">
          Мини-игры стали неотъемлемой частью Minecraft, и наш сервер приглашает
          вас окунуться в мир соревнований на спартакиаде от{" "}
          <a
            href="https://vk.com/kb_esports"
            target="_blank"
            rel="noopener noreferrer"
          >
            Кронверскских барсов
          </a>
          . Здесь вас ждут проверенные классические режимы, разработанные с нуля
          от наших разработчиков:<br></br> <b>Block Party, Ace Race, UHC</b>.
        </p>

        <div className="my-4 d-flex justify-content-center">
          <a
            className="btn btn-secondary btn-lg mx-2"
            href="https://vk.me/join/WDyZMd4pF8Xhu/egqaDnrHmbajAmm0cZ2og="
            target="_blank"
            rel="noopener noreferrer"
          >
            Вступить в беседу
          </a>
          <a
            className="btn btn-primary btn-lg mx-2"
            href="https://docs.google.com/forms/d/e/1FAIpQLSfX7C2f1WII6Ak_me3onbRAcb71MSEap51MS-Hic4XYg915MA/viewform"
            target="_blank"
            rel="noopener noreferrer"
          >
            Зарегистрироваться
          </a>
        </div>
        <a
          href="https://docs.google.com/document/d/1TasKKNFDkostGTnX0SsSpCzvgKw7tITA/edit?tab=t.0"
          target="_blank"
          rel="noopener noreferrer"
        >
          Читать регламент спартакиады
        </a>
      </div>
    </div>
  );
};

export default MiniGames;
