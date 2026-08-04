import httpClient from '../services/httpClient';

/** Download a protected PDF endpoint with credentialed Axios cookies. */
export async function downloadAuthenticatedPdf(relativePath, filename = 'document.pdf', params = undefined) {
  const { data } = await httpClient.get(relativePath, { responseType: 'blob', params });
  const url = window.URL.createObjectURL(new Blob([data], { type: 'application/pdf' }));
  const link = document.createElement('a');
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  window.URL.revokeObjectURL(url);
}
