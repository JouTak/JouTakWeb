import { Link } from 'react-router-dom';
import './pay.css';

export default function Pay() {
  return (
    <section className="text-center mb-4">
      <h1 className="mt-4 display-5 fw-bold">Оплата проходочки</h1>
      <p className="mt-4 fs-4 lh-1 mx-auto">Теперь оплатить доступ к&nbsp;JouTak можно на&nbsp;этой странице!</p>
      <Link
        className="btn btn-primary btn-lg"
        to="/joutak/"
      >
        О сервере
      </Link>

      <p className="mt-4 col-md-9 fs-4 lh-1 mx-auto">
        Джоутек спонсируют только его&nbsp;игроки.
        <br />
        Каждый месяц мы&nbsp;скидываемся на&nbsp;хостинг&nbsp;— никто на&nbsp;этом ничего не&nbsp;зарабатывает, это&nbsp;способ существования сервера.
        Всё работает по&nbsp;принципам доната: вы&nbsp;оплачиваете любую сумму, но&nbsp;не&nbsp;меньше минимальной.
        Чем больше (в&nbsp;перерасчёте на&nbsp;месяц) присылают игроки, тем&nbsp;лучше себя чувствует сервер.
        За&nbsp;дополнительные донаты игроки не&nbsp;получают привилегий.
      </p>

      <script src="https://forms.yandex.ru/_static/embed.js"></script>
      <iframe
        className="pay"
        src="https://forms.yandex.ru/u/6515e3dcd04688fca3cc271b?iframe=1&theme=dark"
        name="ya-form-6515e3dcd04688fca3cc271b"
      />
    </section>
  );
}
