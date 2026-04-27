import { useEffect, useMemo, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { appointmentsAPI, messagesAPI } from '../services/api.js';
import { API_BASE_URL } from '../services/httpClient.js';
import './DoctorMessages.css';

const DoctorMessages = () => {
  const [searchParams] = useSearchParams();
  const [appointments, setAppointments] = useState([]);
  const [selectedAppointmentId, setSelectedAppointmentId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [loadingConversations, setLoadingConversations] = useState(true);
  const [loadingMessages, setLoadingMessages] = useState(false);
  const [sending, setSending] = useState(false);
  const [error, setError] = useState('');
  const [text, setText] = useState('');
  const [file, setFile] = useState(null);
  const [showPrescriptionModal, setShowPrescriptionModal] = useState(false);
  const [prescriptionText, setPrescriptionText] = useState('');
  const [prescriptionFile, setPrescriptionFile] = useState(null);

  const getErrorMessage = (err, fallback) => {
    const detail = err?.response?.data?.detail;
    if (typeof detail === 'string' && detail.trim()) {
      return detail;
    }
    return err?.message || fallback;
  };

  const loadAppointments = async () => {
    setLoadingConversations(true);
    try {
      const { data } = await appointmentsAPI.getAll();
      const list = Array.isArray(data) ? data : [];
      setAppointments(list);

      const fromQuery = Number(searchParams.get('appointmentId'));
      if (Number.isInteger(fromQuery) && fromQuery > 0 && list.some((a) => a.id === fromQuery)) {
        setSelectedAppointmentId(fromQuery);
      } else if (list.length > 0 && !selectedAppointmentId) {
        setSelectedAppointmentId(list[0].id);
      }
      setError('');
    } catch (err) {
      setError(getErrorMessage(err, 'Impossible de charger les conversations.'));
    } finally {
      setLoadingConversations(false);
    }
  };

  const loadMessages = async (appointmentId) => {
    if (!appointmentId) return;

    setLoadingMessages(true);
    try {
      const { data } = await messagesAPI.getByAppointment(appointmentId);
      setMessages(Array.isArray(data) ? data : []);
      setError('');
    } catch (err) {
      setError(getErrorMessage(err, 'Impossible de charger les messages.'));
    } finally {
      setLoadingMessages(false);
    }
  };

  useEffect(() => {
    loadAppointments();
  }, []);

  useEffect(() => {
    if (selectedAppointmentId) {
      loadMessages(selectedAppointmentId);
    }
  }, [selectedAppointmentId]);

  useEffect(() => {
    if (!selectedAppointmentId) return;
    const intervalId = setInterval(() => loadMessages(selectedAppointmentId), 12000);
    return () => clearInterval(intervalId);
  }, [selectedAppointmentId]);

  const selectedAppointment = useMemo(
    () => appointments.find((appointment) => appointment.id === selectedAppointmentId) || null,
    [appointments, selectedAppointmentId]
  );

  const sendMessage = async ({ content, attachment }) => {
    if (!selectedAppointmentId) {
      return;
    }

    const formData = new FormData();
    if (content?.trim()) formData.append('content', content.trim());
    if (attachment) formData.append('attachment', attachment);

    setSending(true);
    try {
      await messagesAPI.sendToAppointment(selectedAppointmentId, formData);
      await loadMessages(selectedAppointmentId);
      setError('');
    } catch (err) {
      setError(getErrorMessage(err, 'Impossible d’envoyer le message.'));
    } finally {
      setSending(false);
    }
  };

  const handleSend = async (e) => {
    e.preventDefault();
    if (!text.trim() && !file) return;

    await sendMessage({ content: text, attachment: file });
    setText('');
    setFile(null);
  };

  const handleSendPrescription = async (e) => {
    e.preventDefault();
    if (!prescriptionText.trim() && !prescriptionFile) return;

    await sendMessage({
      content: prescriptionText ? `Ordonnance: ${prescriptionText}` : 'Ordonnance en pièce jointe',
      attachment: prescriptionFile,
    });

    setPrescriptionText('');
    setPrescriptionFile(null);
    setShowPrescriptionModal(false);
  };

  const resolveAttachmentHref = (url) => {
    if (!url) return null;
    if (/^https?:\/\//i.test(url)) return url;
    return `${API_BASE_URL}${url}`;
  };

  return (
    <div className="doctor-messages-page">
      <header className="doctor-messages-header">
        <div>
          <h1>Messagerie médecin</h1>
          <p>Communiquez avec vos patients depuis vos rendez-vous.</p>
        </div>
        <Link className="button-secondary" to="/doctor/dashboard">Retour au tableau de bord</Link>
      </header>

      {error && <p className="error">{error}</p>}

      <div className="doctor-messages-layout">
        <aside className="conversation-panel">
          <h2>Conversations</h2>
          {loadingConversations && <p>Chargement...</p>}
          <ul>
            {appointments.map((appointment) => (
              <li key={appointment.id}>
                <button
                  type="button"
                  className={`conversation-btn ${selectedAppointmentId === appointment.id ? 'active' : ''}`}
                  onClick={() => setSelectedAppointmentId(appointment.id)}
                >
                  <span>{appointment?.patient?.first_name || 'Patient'} {appointment?.patient?.last_name || ''}</span>
                  <small>{new Date(appointment.date).toLocaleDateString('fr-FR')}</small>
                </button>
              </li>
            ))}
          </ul>
        </aside>

        <section className="chat-panel">
          <div className="chat-header">
            <h3>
              {selectedAppointment
                ? `${selectedAppointment?.patient?.first_name || 'Patient'} ${selectedAppointment?.patient?.last_name || ''}`
                : 'Sélectionnez une conversation'}
            </h3>
            {selectedAppointment && (
              <div className="chat-header-actions">
                <button type="button" className="button-secondary" onClick={() => setShowPrescriptionModal(true)}>
                  Envoyer une ordonnance
                </button>
                <Link className="button-secondary" to={`/doctor/patient/${selectedAppointment.patient_id}`}>
                  Dossier patient
                </Link>
              </div>
            )}
          </div>

          <div className="chat-thread">
            {loadingMessages && <p>Chargement des messages...</p>}
            {!loadingMessages && messages.length === 0 && <p>Aucun message.</p>}

            {!loadingMessages && messages.map((message) => (
              <div
                key={message.id}
                className={`chat-row ${message.sender_role === 'doctor' ? 'mine' : 'other'}`}
              >
                <div className="chat-bubble">
                  <p className="chat-meta">
                    {message.sender_role === 'doctor' ? 'Vous' : 'Patient'} · {new Date(message.created_at).toLocaleString('fr-FR')}
                  </p>
                  {message.content && <p className="chat-content">{message.content}</p>}
                  {message.attachment_url && (
                    <a href={resolveAttachmentHref(message.attachment_url)} target="_blank" rel="noreferrer" className="chat-attachment">
                      {message.attachment_name || 'Pièce jointe'}
                    </a>
                  )}
                </div>
              </div>
            ))}
          </div>

          <form className="chat-composer" onSubmit={handleSend}>
            <textarea
              value={text}
              onChange={(e) => setText(e.target.value)}
              rows={3}
              placeholder="Écrire un message..."
              disabled={!selectedAppointmentId}
            />
            <div className="composer-actions">
              <input
                type="file"
                accept=".pdf,image/*"
                onChange={(e) => setFile(e.target.files?.[0] || null)}
                disabled={!selectedAppointmentId}
              />
              <button type="submit" className="button-pay" disabled={!selectedAppointmentId || sending}>
                {sending ? 'Envoi...' : 'Envoyer'}
              </button>
            </div>
          </form>
        </section>
      </div>

      {showPrescriptionModal && (
        <div className="prescription-overlay" onClick={() => setShowPrescriptionModal(false)}>
          <form className="prescription-modal" onClick={(e) => e.stopPropagation()} onSubmit={handleSendPrescription}>
            <h3>Envoyer une ordonnance</h3>
            <textarea
              rows={4}
              placeholder="Détails de l'ordonnance"
              value={prescriptionText}
              onChange={(e) => setPrescriptionText(e.target.value)}
            />
            <input type="file" accept=".pdf,image/*" onChange={(e) => setPrescriptionFile(e.target.files?.[0] || null)} />
            <div className="modal-actions">
              <button type="button" className="button-secondary" onClick={() => setShowPrescriptionModal(false)}>
                Fermer
              </button>
              <button type="submit" className="button-pay" disabled={sending}>
                {sending ? 'Envoi...' : 'Envoyer'}
              </button>
            </div>
          </form>
        </div>
      )}
    </div>
  );
};

export default DoctorMessages;
