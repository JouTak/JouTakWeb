import { InMemoryProvider, OpenFeature } from "@openfeature/react-sdk";

const provider = new InMemoryProvider({});
let initialized = false;

function getVariantKey(value) {
  if (typeof value === "string") {
    return value;
  }
  if (typeof value === "boolean") {
    return value ? "true" : "false";
  }
  return String(value);
}

export function toFlagConfiguration(features) {
  return Object.fromEntries(
    Object.entries(features || {}).map(([key, value]) => {
      const variant = getVariantKey(value);
      return [
        key,
        {
          disabled: false,
          variants: { [variant]: value },
          defaultVariant: variant,
        },
      ];
    }),
  );
}

export function initializeOpenFeature() {
  if (initialized) {
    return;
  }
  OpenFeature.setProvider(provider);
  initialized = true;
}

export async function updateFeatureConfiguration(features) {
  await provider.putConfiguration(toFlagConfiguration(features));
}
