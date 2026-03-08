import PropTypes from "prop-types";

import FeatureGate from "../features/featureFlags/FeatureGate.jsx";
import Footer from "./Footer";
import FooterV2 from "./FooterV2/FooterV2.jsx";
import Header from "./Header";

const Layout = ({ children }) => {
  return (
    <>
      <Header />
      <main className="my-4 w-100">{children}</main>
      <Footer />
    </>
  );
};

Layout.propTypes = {
  children: PropTypes.node.isRequired,
};

export default Layout;
