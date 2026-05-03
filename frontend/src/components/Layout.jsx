import PropTypes from "prop-types";
import Footer from "./Footer/Footer";
import Header from "./Header";


const Layout = ({ children }) => {
  return (
    <>
      <Header />
      <main className="w-100">{children}</main>
      <Footer />
    </>
  );
};

Layout.propTypes = {
  children: PropTypes.node.isRequired,
};

export default Layout;
