import PropTypes from "prop-types";

import FeatureGate from "../features/featureFlags/FeatureGate.jsx";
import Footer from "./Footer";
import FooterV2 from "./FooterV2/FooterV2.jsx";
import Header from "./Header";

const Layout = ({ children }) => {
  return (
    <>
      <Header />
      <main className="container my-4">{children}</main>
      <FeatureGate flag="site_footer_v2" fallback={<Footer />}>
        <FooterV2 />
      </FeatureGate>
    </>
  );
};

Layout.propTypes = {
  children: PropTypes.node.isRequired,
};

export default Layout;
