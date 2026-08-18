import { useEffect, useMemo, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext.jsx';
import { appointmentsAPI, messagesAPI } from '../services/api.js';
import { openMessageAttachment } from '../services/attachmentDownload.js';
import './Messages.css';

const Messages = () => {
  const { appointmentId } = useParams();
  const { user } = useAuth();
  const [appointment, setAppointment] = useState(null);
  const [messages, setMessages] = useState([]);
  const [loading, setLoading] = useState(true);
  const [sending, setSending] = useState(false);
  const [error, setError] = useState('');
  const [text, setText] = useState('');
  const [file, setFile] = useState(null);

  const getErrorMessage = (err, fallback) => {
    const detail = err?.response?.data?.detail;
    if (typeof detail === 'string' && detail.trim()) {
      return detail;
    }
    return err?.message || fallback;
  };

  const loadMessages = async () => {
    try {
      const [appointmentResponse, messageResponse] = await Promise.all([
        appointmentsAPI.getById(appointmentId),
        messagesAPI.getByAppointment(appointmentId),
      ]);
      setAppointment(appointmentResponse.data);
      setMessages(Array.isArray(messageResponse.data) ? messageResponse.data : []);
      setError('');
    } catch (err) {
      setError(getErrorMessage(err, 'Impossible de charger la conversation.'));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    setLoading(true);
    loadMessages();
  }, [appointmentId]);

  useEffect(() => {
    const intervalId = setInterval(() => {
      loadMessages();
    }, 12000);

    return () => clearInterval(intervalId);
  }, [appointmentId]);

  const headerTitle = useMemo(() => {
    if (!appointment) return 'Conversation';
    const doctorName = appointment?.doctor?.name || `Dr #${appointment?.doctor_id ?? '-'}`;
    const patientName = `${appointment?.patient?.first_name || ''} ${appointment?.patient?.last_name || ''}`.trim() || 'Patient';
    return user?.role === 'doctor' ? patientName : doctorName;
  }, [appointment, user]);

  const handleOpenAttachment = async (message) => {
    try {
      await openMessageAttachment(message.id);
    } catch (err) {
      setError(getErrorMessage(err, 'Impossible d’ouvrir la pièce jointe.'));
    }
  };

  const handleSend = async (e) => {
    e.preventDefault();

    const trimmed = text.trim();
    if (!trimmed && !file) {
      return;
    }

    setSending(true);
    setError('');

    try {
      const formData = new FormData();
      if (trimmed) formData.append('content', trimmed);
      if (file) formData.append('attachment', file);

      await messagesAPI.sendToAppointment(appointmentId, formData);
      setText('');
      setFile(null);
      await loadMessages();
    } catch (err) {
      setError(getErrorMessage(err, 'Impossible d’envoyer le message.'));
    } finally {
      setSending(false);
    }
  };

  return (
    <div className="messages-page ds-page">
      <header className="messages-header">
        <div>
          <h1>Messagerie</h1>
          <p>{headerTitle}</p>
        </div>
        <Link to={user?.role === 'doctor' ? '/doctor/dashboard' : '/appointments'} className="button-secondary">
          Retour
        </Link>
      </header>

      {error && <p className="error">{error}</p>}

      <div className="messages-thread">
        {loading && <p>Chargement de la conversation...</p>}

        {!loading && messages.length === 0 && (
          <p className="messages-empty">Aucun message pour le moment. Démarrez la conversation.</p>
        )}

        {!loading && messages.map((message) => {
          const isCurrentUser = Number(message.sender_user_id) === Number(user?.id);
          return (
            <div key={message.id} className={`message-row ${isCurrentUser ? 'mine' : 'other'}`}>
              <div className="message-bubble">
                <p className="message-meta">
                  {isCurrentUser ? 'Vous' : message.sender_role === 'doctor' ? 'Médecin' : 'Patient'} · {new Date(message.created_at).toLocaleString('fr-FR')}
                </p>
                {message.content && <p className="message-content">{message.content}</p>}
                {message.has_attachment && (
                  <button
                    type="button"
                    className="message-attachment"
                    onClick={() => handleOpenAttachment(message)}
                  >
                    {message.attachment_name || 'Pièce jointe'}
                  </button>
                )}
              </div>
            </div>
          );
        })}
      </div>

      <form className="message-composer" onSubmit={handleSend}>
        <textarea
          value={text}
          onChange={(e) => setText(e.target.value)}
          placeholder="Écrivez votre message…"
          rows={3}
        />
        <div className="composer-actions">
          <input
            type="file"
            accept=".pdf,image/*"
            onChange={(e) => setFile(e.target.files?.[0] || null)}
          />
          <button type="submit" disabled={sending} className="button-pay">
            {sending ? 'Envoi...' : 'Envoyer'}
          </button>
        </div>
      </form>
    </div>
  );
};

export default Messages;
