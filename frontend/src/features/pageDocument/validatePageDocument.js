import Ajv2020 from "ajv/dist/2020";
import addFormats from "ajv-formats";

import pageDocumentSchema from "../../../../contracts/page-document.schema.json";

function withoutOpenApiDiscriminators(value) {
  if (Array.isArray(value)) {
    return value.map(withoutOpenApiDiscriminators);
  }
  if (!value || typeof value !== "object") return value;
  return Object.fromEntries(
    Object.entries(value)
      .filter(([key]) => key !== "discriminator")
      .map(([key, child]) => [key, withoutOpenApiDiscriminators(child)]),
  );
}

const ajv = new Ajv2020({
  allErrors: true,
  strict: true,
  strictTypes: false,
});
addFormats(ajv);
const validate = ajv.compile(withoutOpenApiDiscriminators(pageDocumentSchema));

export function validatePageDocument(value) {
  if (!validate(value)) {
    const details = ajv.errorsText(validate.errors, {
      separator: "; ",
    });
    throw new TypeError(`Invalid PageDocument: ${details}`);
  }
  return value;
}
