import { Link } from "react-router-dom";

const Footer = () => {
  return (
    <footer className="bg-dark text-light py-3 mt-4">
      <div className="container text-center">
        <div>© 2025 JoyTak</div>
        <div className="mb-2">
          <Link to="/privacy-policy" className="text-light mx-2">
            Политика конфиденциальности
          </Link>
          <Link to="/terms" className="text-light mx-2">
            Условия использования
          </Link>
          <Link to="/contact" className="text-light mx-2">
            Контакты
          </Link>
        </div>
      </div>
    </footer>
  );
};

export default Footer;
