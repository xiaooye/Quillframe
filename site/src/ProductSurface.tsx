import type { JSX } from "solid-js";

export type SurfaceTone = "project" | "runtime" | "editorial" | "evidence" | "validated" | "publication";

type HeroProps = {
  class?: string;
  tone?: SurfaceTone;
  eyebrow: JSX.Element;
  title: JSX.Element;
  lede: JSX.Element;
  badges?: JSX.Element;
  actions?: JSX.Element;
  visual?: JSX.Element;
};

export function ProductSurfaceHero(props: HeroProps) {
  return (
    <section class={`product-surface-hero ${props.class ?? ""}`} data-tone={props.tone ?? "runtime"}>
      <div class="product-surface-hero__copy">
        <div class="product-surface-hero__eyebrow">{props.eyebrow}</div>
        {props.badges ? <div class="product-surface-hero__badges">{props.badges}</div> : null}
        <h1>{props.title}</h1>
        <div class="product-surface-hero__lede">{props.lede}</div>
        {props.actions ? <div class="product-surface-hero__actions">{props.actions}</div> : null}
      </div>
      {props.visual ? <div class="product-surface-hero__visual">{props.visual}</div> : null}
    </section>
  );
}

type SectionHeadingProps = {
  eyebrow: JSX.Element;
  title: JSX.Element;
  aside?: JSX.Element;
};

export function ProductSectionHeading(props: SectionHeadingProps) {
  return (
    <div class="product-section-heading">
      <div>
        <small>{props.eyebrow}</small>
        <h2>{props.title}</h2>
      </div>
      {props.aside ? <div class="product-section-heading__aside">{props.aside}</div> : null}
    </div>
  );
}
