const Contact = () => {
  return (
    <div
      className="p-5 mb-4 bg-light shadow-lg position-relative"
      style={{
        backgroundImage: "url(/img/river.png)",
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
        <p className="col-md-10 fs-4 lh-1">
          Подпишись, чтобы быть в курсе новостей Джоутека, <br></br>ИТМОкрафта и
          майнкрафта!
        </p>
        <div className="d-flex justify-content-center gap-3 my-4">
          <a
            href="https://t.me/+HHAU5go3GqIzYmI6"
            target="_blank"
            rel="noopener noreferrer"
          >
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
};

export default Contact;
