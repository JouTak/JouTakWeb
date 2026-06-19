import PropTypes from "prop-types";

import Footer from "./Footer";
import Header from "./Header";
import NotificationBanner from "./ui/Notification/NotificationBanner";

const Layout = ({ children }) => {
  return (
    <>
      <Header />
      <NotificationBanner
        title = "Системное уведомление" 
        message = "Сейчас действует повышенная нагрузка на сервер. Возможны кратковременные перебои."
        theme = "warning"
      />
      <main className="container my-4">{children}</main>
      <Footer />
    </>
  );
};

Layout.propTypes = {
  children: PropTypes.node.isRequired,
};

export default Layout;
