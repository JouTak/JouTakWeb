import PropTypes from "prop-types";

import FeatureGate from "../features/featureFlags/FeatureGate";
import Footer from "../Legacy/frontend/src/components/Footer";
import FooterNew from "./Footer/Footer";
import Header from "./Header";
import HeaderNew from "./HeaderNew/HeaderNew";

const Layout = ({ children }) => {
  return (
    <>
      <FeatureGate flag="site_new_header" fallback={<Header />}>
        <HeaderNew />
      </FeatureGate>
      <main className="w-100">{children}</main>
      <FeatureGate flag="site_new_footer" fallback={<Footer />}>
        <FooterNew />
      </FeatureGate>
    </>
  );
};

Layout.propTypes = {
  children: PropTypes.node.isRequired,
};

export default Layout;
