/** Resolve extensionless TypeScript imports for the Node test runner. */

const EXTENSION = /\.[cm]?[jt]s$/;

export async function resolve(specifier, context, nextResolve) {
  if ((specifier.startsWith("./") || specifier.startsWith("../")) && !EXTENSION.test(specifier)) {
    return nextResolve(`${specifier}.ts`, context);
  }
  return nextResolve(specifier, context);
}
