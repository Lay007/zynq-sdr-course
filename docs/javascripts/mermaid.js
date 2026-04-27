document$.subscribe(function () {
  const diagrams = document.querySelectorAll(".mermaid");
  if (diagrams.length === 0 || typeof mermaid === "undefined") {
    return;
  }

  mermaid.initialize({
    startOnLoad: false,
    theme: "base",
    securityLevel: "loose",
    flowchart: {
      curve: "basis",
      htmlLabels: true,
      nodeSpacing: 38,
      rankSpacing: 52,
      padding: 12,
    },
    themeVariables: {
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
    },
  });

  mermaid.run({
    nodes: diagrams,
  });
});
