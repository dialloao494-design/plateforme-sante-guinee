/** Print one document without letting hidden application UI create blank pages. */
export async function printIsolatedDocument(element) {
  if (!element) throw new Error('Document à imprimer introuvable');

  const frame = document.createElement('iframe');
  frame.title = 'Document prêt à imprimer';
  frame.setAttribute('aria-hidden', 'true');
  frame.style.cssText = 'position:fixed;right:0;bottom:0;width:1px;height:1px;border:0;opacity:0;pointer-events:none';
  document.body.appendChild(frame);

  const printDocument = frame.contentDocument;
  const styleMarkup = [...document.querySelectorAll('link[rel="stylesheet"], style')]
    .map((node) => node.outerHTML)
    .join('\n');
  printDocument.open();
  printDocument.write(`<!doctype html><html lang="fr"><head><meta charset="utf-8"><base href="${document.baseURI}">${styleMarkup}<style>@page{size:A4;margin:12mm}html,body{margin:0!important;min-height:0!important;background:#fff!important}.clinical-print-target{display:block!important;position:static!important;width:auto!important}</style></head><body>${element.outerHTML}</body></html>`);
  printDocument.close();

  await new Promise((resolve) => {
    if (printDocument.readyState === 'complete') resolve();
    else frame.addEventListener('load', resolve, { once: true });
  });
  await printDocument.fonts?.ready;
  await Promise.all([...printDocument.images].map((image) => image.complete
    ? Promise.resolve()
    : new Promise((resolve) => {
      image.addEventListener('load', resolve, { once: true });
      image.addEventListener('error', resolve, { once: true });
    })));

  const cleanup = () => frame.remove();
  frame.contentWindow.onafterprint = cleanup;
  frame.contentWindow.focus();
  window.dispatchEvent(new CustomEvent('clinical:isolated-print', {
    detail: { title: element.getAttribute('aria-label') || printDocument.title || 'Document clinique' },
  }));
  frame.contentWindow.print();
  window.setTimeout(cleanup, 30_000);
}
