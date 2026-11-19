const backToTop = document.querySelector("#back-to-top");
if (backToTop) {
  const updateBackToTop = () => {
    backToTop.hidden = window.scrollY < 240;
  };
  window.addEventListener("scroll", updateBackToTop, { passive: true });
  backToTop.addEventListener("click", () => {
    window.scrollTo({ top: 0, behavior: window.matchMedia("(prefers-reduced-motion: reduce)").matches ? "instant" : "smooth" });
  });
  updateBackToTop();
}
