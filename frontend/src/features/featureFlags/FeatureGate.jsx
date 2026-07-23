/**
 * FeatureGate — Universal conditional rendering component for feature flags.
 *
 * Renders children only when a feature flag matches the expected condition.
 * Supports both boolean flags and variant-based flags.
 *
 * Usage (boolean flag):
 *   <FeatureGate flag="site_footer_v2" fallback={<LegacyFooter />}>
 *     <FooterV2 />
 *   </FeatureGate>
 *
 * Usage (variant flag):
 *   <FeatureGate flag="site_homepage_version" variant="v2" fallback={<Legacy />}>
 *     <HomepageV2 />
 *   </FeatureGate>
 *
 * Usage (inverted — show when flag is OFF):
 *   <FeatureGate flag="site_header_v2" expect={false}>
 *     <LegacyHeader />
 *   </FeatureGate>
 *
 * Props:
 *   - flag (string, required): Feature flag key from the registry
 *   - variant (string, optional): For variant flags — show children only
 *     when the flag value equals this variant
 *   - expect (boolean, optional): For boolean flags — expected value
 *     (defaults to true, set to false for inverted gates)
 *   - fallback (ReactNode, optional): Rendered when condition is NOT met
 *   - children (ReactNode): Rendered when condition IS met
 */
import {
  useBooleanFlagValue,
  useStringFlagValue,
} from "@openfeature/react-sdk";
import PropTypes from "prop-types";

const FeatureGate = ({
  flag,
  flag_type = "",
  variants = {},
  fallback = null,
}) => {
  const stringValue = useStringFlagValue(flag, "");
  const booleanValue = useBooleanFlagValue(flag, false);

  // For variant-based flags
  if (flag_type === "variant") {
    return variants[stringValue] || fallback;
  }
  // For boolean-based flags
  if (flag_type === "boolean") {
    return variants[String(booleanValue)] || fallback;
  }

  return fallback;
};

FeatureGate.propTypes = {
  flag: PropTypes.string.isRequired,
  flag_type: PropTypes.oneOf(["boolean", "variant"]).isRequired,
  variants: PropTypes.objectOf(PropTypes.element),
  fallback: PropTypes.oneOfType([PropTypes.element, PropTypes.oneOf([null])]),
};

export default FeatureGate;
