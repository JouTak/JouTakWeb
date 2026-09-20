import GithubSlugger from "github-slugger";
import remarkGfm from "remark-gfm";
import remarkParse from "remark-parse";
import { unified } from "unified";

function textContent(node) {
  return (
    node.value ?? node.alt ?? (node.children ?? []).map(textContent).join("")
  );
}

// The TOC and rendered headings use the same parser and slug rules.
export function remarkDocumentHeadings() {
  return (tree, file) => {
    const slugger = new GithubSlugger();
    const headings = [];
    function walk(node) {
      if (node.type === "heading") {
        const text = textContent(node);
        const id = `document-${slugger.slug(text)}`;
        node.data = {
          ...node.data,
          hProperties: { ...node.data?.hProperties, id },
        };
        if (node.depth <= 3) headings.push({ id, text, depth: node.depth });
      }
      node.children?.forEach(walk);
    }
    walk(tree);
    file.data.headings = headings;
  };
}

export function getDocumentHeadings(markdown) {
  const processor = unified()
    .use(remarkParse)
    .use(remarkGfm)
    .use(remarkDocumentHeadings);
  const file = { data: {} };
  processor.runSync(processor.parse(markdown), file);
  return file.data.headings;
}
