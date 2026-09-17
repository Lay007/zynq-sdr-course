function mermaidIsDark() {
  return document.body.getAttribute("data-md-color-scheme") === "slate";
}

function mermaidThemeVariables(dark) {
  return dark
    ? {
        fontFamily: "Inter, Roboto, Arial, sans-serif",
        primaryColor: "#123a4a",
        primaryTextColor: "#e2f4ff",
        primaryBorderColor: "#38bdf8",
        lineColor: "#94a3b8",
        secondaryColor: "#123a2e",
        tertiaryColor: "#161b22",
        clusterBkg: "#161b22",
        clusterBorder: "#334155",
        edgeLabelBackground: "#161b22",
      }
    : {
        fontFamily: "Inter, Roboto, Arial, sans-serif",
        primaryColor: "#E0F2FE",
        primaryTextColor: "#0F172A",
        primaryBorderColor: "#0284C7",
        lineColor: "#475569",
        secondaryColor: "#DCFCE7",
        tertiaryColor: "#F8FAFC",
        clusterBkg: "#F8FAFC",
        clusterBorder: "#CBD5E1",
        edgeLabelBackground: "#FFFFFF",
      };
}

function renderMermaidDiagrams() {
  const diagrams = document.querySelectorAll(".mermaid");
  if (diagrams.length === 0 || typeof mermaid === "undefined") {
    return;
  }

  const dark = mermaidIsDark();

  // Mermaid replaces .mermaid innerHTML with rendered SVG and marks the node
  // "data-processed". Cache the original source once so a later theme switch
  // can restore the source text and re-render instead of re-rendering an SVG.
  diagrams.forEach(function (el) {
    if (el.dataset.mermaidSource === undefined) {
      el.dataset.mermaidSource = el.textContent;
    }
    el.removeAttribute("data-processed");
    el.innerHTML = el.dataset.mermaidSource;
  });

  mermaid.initialize({
    startOnLoad: false,
    theme: dark ? "dark" : "base",
    securityLevel: "loose",
    flowchart: {
      curve: "basis",
      htmlLabels: true,
      nodeSpacing: 38,
      rankSpacing: 52,
      padding: 12,
    },
    themeVariables: mermaidThemeVariables(dark),
  });

  mermaid.run({
    nodes: diagrams,
  });
}

document$.subscribe(renderMermaidDiagrams);

// The light/dark toggle changes document.body's data-md-color-scheme without
// a page navigation, so document$ alone never fires for it. Re-render any
// diagrams already on screen so they do not stay stuck in the old theme.
new MutationObserver(function (mutations) {
  for (const mutation of mutations) {
    if (mutation.attributeName === "data-md-color-scheme") {
      renderMermaidDiagrams();
      return;
    }
  }
}).observe(document.body, { attributes: true });
