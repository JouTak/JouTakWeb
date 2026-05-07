import { InMemoryProvider, OpenFeature } from "@openfeature/react-sdk";

const provider = new InMemoryProvider({});
let initialized = false;

function toFlagConfiguration(features) {
  return Object.fromEntries(
    Object.entries(features || {}).map(([key, value]) => {
      const variant = String(value);
      return [
        key,
        {
          disabled: false,
          variants: { [variant]: variant },
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
