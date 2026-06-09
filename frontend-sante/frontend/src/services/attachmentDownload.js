import httpClient from './httpClient.js';

/**
 * Download a clinical message attachment via the authenticated API endpoint.
 * Never uses public /uploads URLs.
 */
export async function downloadMessageAttachment(messageId, filename = 'attachment') {
  const response = await httpClient.get(`/messages/attachments/${messageId}/download`, {
    responseType: 'blob',
  });

  const contentType = response.headers['content-type'] || 'application/octet-stream';
  const blob = new Blob([response.data], { type: contentType });
  const objectUrl = window.URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = objectUrl;
  link.download = filename || 'attachment';
  link.rel = 'noopener noreferrer';
  document.body.appendChild(link);
  link.click();
  link.remove();
  window.setTimeout(() => window.URL.revokeObjectURL(objectUrl), 60_000);
}

export async function openMessageAttachment(messageId) {
  const response = await httpClient.get(`/messages/attachments/${messageId}/download`, {
    responseType: 'blob',
  });
  const contentType = response.headers['content-type'] || 'application/octet-stream';
  const blob = new Blob([response.data], { type: contentType });
  const objectUrl = window.URL.createObjectURL(blob);
  window.open(objectUrl, '_blank', 'noopener,noreferrer');
  window.setTimeout(() => window.URL.revokeObjectURL(objectUrl), 120_000);
}
