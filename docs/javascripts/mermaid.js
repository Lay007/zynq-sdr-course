document$.subscribe(function () {
  const diagrams = document.querySelectorAll(".mermaid");
  if (diagrams.length === 0 || typeof mermaid === "undefined") {
    return;
  }

  mermaid.initialize({
    startOnLoad: false,
    theme: "default",
    securityLevel: "loose",
  });

  mermaid.run({
    nodes: diagrams,
  });
});
