const Contact = () => {
    return (
        <div className="p-5 mb-4 rounded-3">
            
        <div className="container py-5">
          <h1 className="display-5 fw-bold">Наши сообщества</h1>
          <p className="col-md-10 fs-4 lh-1">
            Подпишись, чтобы быть в курсе новостей Джоутека, ИТМОкрафта и майнкрафта!
          </p>
          <div className="d-flex flex-column gap-2">
            <a
                className="btn btn-info btn-lg"
                href="https://t.me/+HHAU5go3GqIzYmI6"
                target="_blank"
                rel="noopener noreferrer"
            >
                <i className="fab fa-telegram-plane me-2"></i>
                Наш ТГ
            </a>
            <a
                className="btn btn-info btn-lg"
                href="https://vk.com/itmocraft"
                target="_blank"
                rel="noopener noreferrer"
            >
                <i className="fab fa-vk me-2"></i>
                Наш ВК
            </a>
            <a
                className="btn btn-info btn-lg"
                href="https://discord.gg/YVj5tckahA"
                target="_blank"
                rel="noopener noreferrer"
            >
                <i className="fab fa-discord me-2"></i>
                Дискорд Джоутека
            </a>
          </div>
        </div>
      </div>
    );
};

export default Contact;