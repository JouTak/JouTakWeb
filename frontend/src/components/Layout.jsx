import PropTypes from "prop-types";
import Header from "./Header";
import Footer from "./Footer";
import { useLocation } from "react-router-dom";

const Layout = ({ children }) => {
  const location = useLocation(); 
  const isSpecialPage = ['/404'].includes(location.pathname);

  if (isSpecialPage) { 
    return <>{children}</>; 
  }

  return (
    <>
      <Header />
      <main className="container my-4">{children}</main>
      <Footer />
    </>
  );
};

Layout.propTypes = {
  children: PropTypes.node.isRequired,
};

export default Layout;
