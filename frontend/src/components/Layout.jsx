import PropTypes from "prop-types";
import Header from "./Header";
import Footer from "./Footer/Footer";
import HeaderNew from "./HeaderNew/HeaderNew";

const Layout = ({ children }) => {
  return (
    <>
      <HeaderNew />
      <main className="w-100">{children}</main>
      <Footer />
    </>
  );
};

Layout.propTypes = {
  children: PropTypes.node.isRequired,
};

export default Layout;
