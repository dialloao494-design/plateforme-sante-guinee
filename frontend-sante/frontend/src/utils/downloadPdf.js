import httpClient from '../services/httpClient';

/** Download a protected PDF endpoint (Bearer and/or credentialed cookies). */
export async function downloadAuthenticatedPdf(relativePath, filename = 'document.pdf', params = undefined) {
  try {
    const { data, headers } = await httpClient.get(relativePath, { responseType: 'blob', params });
    const contentType = String(headers?.['content-type'] || '');
    if (contentType.includes('application/json')) {
      const text = await data.text();
      let detail = 'Impression impossible';
      try {
        detail = JSON.parse(text)?.detail || detail;
      } catch {
        /* ignore */
      }
      throw new Error(typeof detail === 'string' ? detail : 'Impression impossible');
    }
    const url = window.URL.createObjectURL(new Blob([data], { type: 'application/pdf' }));
    const link = document.createElement('a');
    link.href = url;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    link.remove();
    window.URL.revokeObjectURL(url);
  } catch (err) {
    const status = err?.response?.status;
    if (status === 401 || status === 403) {
      throw new Error('Session expirée : reconnectez-vous puis réessayez l’impression.');
    }
    throw err;
  }
}
