import { useEffect, useMemo, useState } from 'react';

import { Link } from 'react-router-dom';

import { useAuth } from '../../contexts/AuthContext.jsx';

import platformApi from '../../services/platformApi';

import ClinicalStatGrid from '../clinical/ClinicalStatGrid.jsx';

import '../clinical/clinical.css';

import './PlatformOwner.css';



function formatDate(value) {

  if (!value) return '—';

  try {

    return new Date(value).toLocaleDateString('fr-FR', {

      day: '2-digit',

      month: 'short',

      year: 'numeric',

    });

  } catch {

    return '—';

  }

}



export default function PlatformOwnerDashboard() {

  const { user } = useAuth();

  const [summary, setSummary] = useState(null);

  const [clinics, setClinics] = useState([]);



  useEffect(() => {

    Promise.all([

      platformApi.getSummary('production'),

      platformApi.listClinicDirectory({ category: 'production' }),

    ])

      .then(([sumRes, dirRes]) => {

        setSummary(sumRes.data);

        setClinics(Array.isArray(dirRes.data) ? dirRes.data : []);

      })

      .catch(() => {

        setSummary(null);

        setClinics([]);

      });

  }, []);



  const stats = useMemo(

    () =>

      summary

        ? [

            { label: 'Cliniques', value: summary.total_clinics, variant: 'accent' },

            { label: 'Cliniques actives', value: summary.active_clinics, variant: 'success' },

            { label: 'Personnel', value: summary.total_staff },

            { label: 'Patients', value: summary.total_patients },

            { label: 'Consultations (mois)', value: summary.monthly_consultations },

          ]

        : [],

    [summary]

  );



  return (

    <div className="platform-owner-page">

      <header className="platform-owner-header">

        <h1>Console Propriétaire Plateforme</h1>

        <p>

          Bienvenue, {user?.full_name || user?.email}. Vue d&apos;ensemble des cliniques en production.

        </p>

      </header>



      {stats.length > 0 && (

        <div className="platform-owner-stats">

          <ClinicalStatGrid stats={stats} />

        </div>

      )}



      <section className="clinical-card platform-owner-clinics-preview">

        <div className="platform-staff-header">

          <h2>Cliniques en production</h2>

          <Link to="/platform/clinics" className="platform-owner-link">

            Gérer toutes les cliniques →

          </Link>

        </div>

        {clinics.length === 0 ? (

          <p className="clinical-lead">Aucune clinique production pour le moment.</p>

        ) : (

          <div className="platform-clinic-grid">

            {clinics.map((clinic) => (

              <Link

                key={clinic.id}

                to={`/platform/clinics/${clinic.id}`}

                className="platform-clinic-card"

              >

                <div className="platform-clinic-card__header">

                  <h3>{clinic.name}</h3>

                  <span className={`platform-status platform-status--${clinic.is_active ? 'active' : 'archived'}`}>

                    {clinic.status}

                  </span>

                </div>

                <p className="platform-clinic-card__meta">

                  ID {clinic.id}

                  {clinic.city ? ` · ${clinic.city}` : ''}

                  {' · Créée '}

                  {formatDate(clinic.created_at)}

                </p>

                <div className="platform-clinic-card__stats">

                  <span>Personnel <strong>{clinic.staff_count}</strong></span>

                  <span>Patients <strong>{clinic.patient_count}</strong></span>

                  <span>Consultations <strong>{clinic.consultation_count}</strong></span>

                </div>

              </Link>

            ))}

          </div>

        )}

      </section>



      <div className="platform-owner-grid">

        <article className="platform-owner-card">

          <h2>Répertoire complet</h2>

          <p>

            Filtres production, démo, test et archivées. Recherche par nom, ville, ID ou email admin.

          </p>

          <Link to="/platform/clinics" className="platform-owner-link">

            Ouvrir le répertoire

          </Link>

        </article>

        <article className="platform-owner-card">

          <h2>Comptes techniques</h2>

          <p>

            Vue avancée des comptes plateforme et comptes orphelins. La gestion du personnel se fait par clinique.

          </p>

          <Link to="/platform/accounts" className="platform-owner-link">

            Comptes techniques

          </Link>

        </article>

      </div>

    </div>

  );

}


