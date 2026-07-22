import PropTypes from "prop-types";
import { Suspense } from "react";

import FeatureGate from "../features/featureFlags/FeatureGate";
import Footer from "../Legacy/frontend/src/components/Footer";
import FooterNew from "./Footer/Footer";
import Header from "./Header";
import HeaderNew from "./HeaderNew/HeaderNew";

function LoadingFallback() {
  return <div className="py-5 text-center text-secondary">Загрузка...</div>;
}

const Layout = ({ children }) => {
  return (
    <Suspense fallback={<LoadingFallback />}>
      <FeatureGate
        flag="site_header_version"
        flag_type="variant"
        variants={{
          legacy: <Header />,
          v2: <HeaderNew />,
        }}
        fallback={<Header />}
      />
      <main className="w-100">{children}</main>
      <FeatureGate
        flag="site_footer_version"
        flag_type="variant"
        variants={{
          legacy: <Footer />,
          v2: <FooterNew />,
        }}
        fallback={<Footer />}
      />
    </Suspense>
  );
};

Layout.propTypes = {
  children: PropTypes.node.isRequired,
};

export default Layout;
