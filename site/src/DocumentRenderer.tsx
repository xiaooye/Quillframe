import { A } from "@solidjs/router";
import { For, Match, Show, Switch, createSignal } from "solid-js";
import { Dynamic } from "solid-js/web";
import type { DocumentBlock, InlineNode, ProductDocument } from "./knowledge";
import { humanDocKind, knowledgeJourneyDefinition, knowledgeJourneyFor } from "./knowledgePresentation";

function InlineView(props: { nodes: InlineNode[] }) {
  return (
    <For each={props.nodes}>{(node) => (
      <Switch>
        <Match when={node.type === "text"}>{(node as Extract<InlineNode, { type: "text" }>).text}</Match>
        <Match when={node.type === "code"}><code>{(node as Extract<InlineNode, { type: "code" }>).text}</code></Match>
        <Match when={node.type === "strong"}><strong><InlineView nodes={(node as Extract<InlineNode, { type: "strong" }>).children} /></strong></Match>
        <Match when={node.type === "em"}><em><InlineView nodes={(node as Extract<InlineNode, { type: "em" }>).children} /></em></Match>
        <Match when={node.type === "del"}><del><InlineView nodes={(node as Extract<InlineNode, { type: "del" }>).children} /></del></Match>
        <Match when={node.type === "br"}><br /></Match>
        <Match when={node.type === "link"}>
          {(() => {
            const link = node as Extract<InlineNode, { type: "link" }>;
            return link.href.startsWith("/") ? (
              <A href={link.href} title={link.title ?? undefined}><InlineView nodes={link.children} /></A>
            ) : (
              <a href={link.href} title={link.title ?? undefined} target={link.href.startsWith("#") ? undefined : "_blank"} rel={link.href.startsWith("#") ? undefined : "noreferrer"}><InlineView nodes={link.children} /></a>
            );
          })()}
        </Match>
        <Match when={node.type === "image"}>
          {(() => {
            const image = node as Extract<InlineNode, { type: "image" }>;
            const external = Boolean(image.href && /^https?:/i.test(image.href));
            return external ? (
              <figure class="doc-inline-image"><img src={image.href!} alt={image.alt} loading="lazy" /><Show when={image.title}><figcaption>{image.title}</figcaption></Show></figure>
            ) : (
              <span class="doc-image-fallback" title={image.title ?? undefined}>🖼️ {image.alt || "image"}</span>
            );
          })()}
        </Match>
      </Switch>
    )}</For>
  );
}

function CodeBlock(props: { lang: string; text: string; copiedLabel: string; copyLabel: string }) {
  const [copied, setCopied] = createSignal(false);
  const copy = async () => {
    try {
      await navigator.clipboard.writeText(props.text);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 1400);
    } catch {
      setCopied(false);
    }
  };
  return (
    <div class="doc-code-shell">
      <div class="doc-code-toolbar">
        <span>{props.lang || "text"}</span>
        <button type="button" class="wui-button wui-button--soft wui-button--sm doc-copy" onClick={copy}>
          {copied() ? props.copiedLabel : props.copyLabel}
        </button>
      </div>
      <pre class="wui-code-block"><code>{props.text}</code></pre>
    </div>
  );
}

function BlockView(props: { block: DocumentBlock; copyLabel: string; copiedLabel: string }) {
  const block = () => props.block;
  return (
    <Switch>
      <Match when={block().type === "heading"}>
        {(() => {
          const heading = block() as Extract<DocumentBlock, { type: "heading" }>;
          const level = Math.max(1, Math.min(6, heading.level));
          return <Dynamic component={`h${level}`} id={heading.id} class="doc-heading"><a class="doc-heading-anchor" href={`#${heading.id}`} aria-label={`# ${heading.id}`}>#</a><InlineView nodes={heading.inlines} /></Dynamic>;
        })()}
      </Match>
      <Match when={block().type === "paragraph"}><p><InlineView nodes={(block() as Extract<DocumentBlock, { type: "paragraph" }>).inlines} /></p></Match>
      <Match when={block().type === "code"}>{(() => { const code = block() as Extract<DocumentBlock, { type: "code" }>; return <CodeBlock lang={code.lang} text={code.text} copyLabel={props.copyLabel} copiedLabel={props.copiedLabel} />; })()}</Match>
      <Match when={block().type === "blockquote"}><blockquote><For each={(block() as Extract<DocumentBlock, { type: "blockquote" }>).blocks}>{(child) => <BlockView block={child} copyLabel={props.copyLabel} copiedLabel={props.copiedLabel} />}</For></blockquote></Match>
      <Match when={block().type === "list"}>
        {(() => {
          const list = block() as Extract<DocumentBlock, { type: "list" }>;
          const Tag = list.ordered ? "ol" : "ul";
          return <Dynamic component={Tag} start={list.ordered && list.start ? list.start : undefined}><For each={list.items}>{(item) => <li><For each={item}>{(child) => <BlockView block={child} copyLabel={props.copyLabel} copiedLabel={props.copiedLabel} />}</For></li>}</For></Dynamic>;
        })()}
      </Match>
      <Match when={block().type === "table"}>
        {(() => {
          const table = block() as Extract<DocumentBlock, { type: "table" }>;
          return (
            <div class="doc-table-scroll" tabindex="0">
              <table>
                <thead><tr><For each={table.header}>{(cell) => <th><InlineView nodes={cell} /></th>}</For></tr></thead>
                <tbody><For each={table.rows}>{(row) => <tr><For each={row}>{(cell) => <td><InlineView nodes={cell} /></td>}</For></tr>}</For></tbody>
              </table>
            </div>
          );
        })()}
      </Match>
      <Match when={block().type === "hr"}><hr /></Match>
    </Switch>
  );
}

export default function DocumentRenderer(props: { document: ProductDocument; locale: "en-US" | "zh-CN" }) {
  const zh = () => props.locale === "zh-CN";
  const docIndexShape = () => ({
    id: props.document.id,
    locale: props.document.locale,
    tier: props.document.tier,
    status: props.document.status,
    title: props.document.title,
    purpose: props.document.purpose,
    audience: props.document.audience,
    sourcePath: props.document.sourcePath,
    sourceFingerprint: props.document.sourceFingerprint,
    freshnessOwner: props.document.freshnessOwner,
    excerpt: props.document.purpose,
    headings: props.document.toc.map((item) => item.text),
    searchText: "",
  });
  const journey = () => knowledgeJourneyDefinition(knowledgeJourneyFor(docIndexShape()));
  return (
    <article class="product-document">
      <header class="document-header">
        <div class="document-human-meta"><span>{journey().icon}</span><strong>{journey().label[props.locale]}</strong><span>·</span><span>{humanDocKind(docIndexShape(), props.locale)}</span></div>
        <h1>{props.document.title}</h1>
        <p>{props.document.purpose}</p>
      </header>
      <div class="document-body">
        <For each={props.document.blocks}>{(block) => <BlockView block={block} copyLabel={zh() ? "复制" : "Copy"} copiedLabel={zh() ? "复制好啦 (｡•̀ᴗ-)✧" : "Copied ✨"} />}</For>
      </div>
    </article>
  );
}
