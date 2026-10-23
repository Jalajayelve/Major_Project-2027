// Warn before closing/reloading a page with an unsaved dossier draft.
window.addEventListener("beforeunload", (event) => {
  if (document.querySelector('[data-unsaved-profile="true"]')) {
    event.preventDefault();
    event.returnValue = "";
  }
});
