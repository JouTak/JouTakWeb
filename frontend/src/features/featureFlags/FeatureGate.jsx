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

export default function FeatureGate({
  flag,
  variant,
  expect = true,
  fallback = null,
  children,
}) {
  // For variant-based flags
  if (variant !== undefined) {
    return (
      <VariantGate flag={flag} variant={variant} fallback={fallback}>
        {children}
      </VariantGate>
    );
  }

  // For boolean flags
  return (
    <BooleanGate flag={flag} expect={expect} fallback={fallback}>
      {children}
    </BooleanGate>
  );
}

function BooleanGate({ flag, expect, fallback, children }) {
  const value = useBooleanFlagValue(flag, !expect);
  return value === expect ? children : fallback;
}

function VariantGate({ flag, variant, fallback, children }) {
  const value = useStringFlagValue(flag, "");
  return value === variant ? children : fallback;
}
