import type { Locale } from "./content";
import { ProductSurfaceHero } from "./ProductSurface";

/**
 * The public site never compiles manuscripts. Publication owns consequential
 * project reads and filesystem writes, so the executable surface lives in the
 * desktop Studio and calls the linked Rust Core directly.
 */
export default function PublicationWorkbench(props: { locale: Locale }) {
  const zh = () => props.locale === "zh-CN";
  return <div class="page-width section-compact unified-route-page publication-workbench-entry publication-playground">
    <ProductSurfaceHero
      class="kawaii-publication-hero"
      tone="publication"
      eyebrow={<span>PUBLICATION · RUST CORE</span>}
      badges={<><span class="wui-badge wui-badge--outline">native/quillframe-core</span><span class="wui-badge wui-badge--outline">Studio required</span></>}
      title={zh() ? <>出版编译已归入<span>本地 Rust 生产链路。</span></> : <>Publication compilation belongs to the <span>local Rust production chain.</span></>}
      lede={<p>{zh()
        ? "为避免网页演示冒充权威生产执行，本页不接收正文，也不生成文件。请在 Quillframe Studio 中从已验收或已结算章节建立出版计划；Studio 会直接调用 Rust Core，校验来源、原子发布文件并保存可恢复的 manifest。"
        : "To keep a website demo from impersonating authoritative production execution, this page accepts no manuscript and creates no file. Build from accepted or settled chapters in Quillframe Studio, which calls Rust Core directly, verifies provenance, publishes atomically, and stores a recoverable manifest."}</p>}
    />
    <section class="publication-empty-result" aria-label={zh() ? "出版边界" : "Publication boundary"}>
      <span>QF</span>
      <div>
        <strong>{zh() ? "网页端仅解释能力边界" : "The website documents the capability boundary"}</strong>
        <p>{zh()
          ? "真实 TXT / Web / Print / EPUB 产物只由 Studio → Rust Core → SQLite / 本地文件系统链路生成。"
          : "Real TXT, Web, Print, and EPUB artifacts are generated only through Studio → Rust Core → SQLite / local filesystem."}</p>
      </div>
    </section>
  </div>;
}
