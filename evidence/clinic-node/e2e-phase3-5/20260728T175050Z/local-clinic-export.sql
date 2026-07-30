--
-- PostgreSQL database dump
--

\restrict jHle7GiIWHCGbkqBgozFtGVp0Zv649fov6glBcjapoSXwShvSNSGB8MUFxglcMw

-- Dumped from database version 16.14
-- Dumped by pg_dump version 16.14

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: admissions; Type: TABLE; Schema: public; Owner: sante
--

CREATE TABLE public.admissions (
    id integer NOT NULL,
    clinic_id integer NOT NULL,
    patient_id integer NOT NULL,
    consultation_id integer,
    admission_number character varying(32) NOT NULL,
    department character varying(128),
    services_json text,
    admission_type character varying(32),
    status character varying(32) NOT NULL,
    reason text,
    diagnosis_summary text,
    outcome character varying(64),
    notes text,
    specialty_code character varying(64),
    specialty_other character varying(255),
    admitted_by_user_id integer,
    attending_clinician_user_id integer,
    admitted_at timestamp without time zone,
    discharged_at timestamp without time zone,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL
);


ALTER TABLE public.admissions OWNER TO sante;

--
-- Name: admissions_id_seq; Type: SEQUENCE; Schema: public; Owner: sante
--

CREATE SEQUENCE public.admissions_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.admissions_id_seq OWNER TO sante;

--
-- Name: admissions_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: sante
--

ALTER SEQUENCE public.admissions_id_seq OWNED BY public.admissions.id;


--
-- Name: appointment_reminders; Type: TABLE; Schema: public; Owner: sante
--

CREATE TABLE public.appointment_reminders (
    id integer NOT NULL,
    appointment_id integer NOT NULL,
    patient_id integer NOT NULL,
    channel character varying(32) NOT NULL,
    reminder_type character varying(16) NOT NULL,
    scheduled_at timestamp without time zone NOT NULL,
    sent_at timestamp without time zone,
    status character varying(32) NOT NULL,
    whatsapp_message_id character varying(128),
    created_at timestamp without time zone NOT NULL
);


ALTER TABLE public.appointment_reminders OWNER TO sante;

--
-- Name: appointment_reminders_id_seq; Type: SEQUENCE; Schema: public; Owner: sante
--

CREATE SEQUENCE public.appointment_reminders_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.appointment_reminders_id_seq OWNER TO sante;

--
-- Name: appointment_reminders_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: sante
--

ALTER SEQUENCE public.appointment_reminders_id_seq OWNED BY public.appointment_reminders.id;


--
-- Name: attachment_access_logs; Type: TABLE; Schema: public; Owner: sante
--

CREATE TABLE public.attachment_access_logs (
    id integer NOT NULL,
    message_id integer NOT NULL,
    appointment_id integer NOT NULL,
    user_id integer NOT NULL,
    user_role character varying(32) NOT NULL,
    client_ip character varying(64),
    storage_kind character varying(16) NOT NULL,
    created_at timestamp without time zone NOT NULL
);


ALTER TABLE public.attachment_access_logs OWNER TO sante;

--
-- Name: attachment_access_logs_id_seq; Type: SEQUENCE; Schema: public; Owner: sante
--

CREATE SEQUENCE public.attachment_access_logs_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.attachment_access_logs_id_seq OWNER TO sante;

--
-- Name: attachment_access_logs_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: sante
--

ALTER SEQUENCE public.attachment_access_logs_id_seq OWNED BY public.attachment_access_logs.id;


--
-- Name: clinic_charge_payments; Type: TABLE; Schema: public; Owner: sante
--

CREATE TABLE public.clinic_charge_payments (
    id integer NOT NULL,
    charge_id integer NOT NULL,
    amount_gnf integer NOT NULL,
    payment_method character varying(32) NOT NULL,
    reference character varying(128),
    recorded_by_user_id integer,
    created_at timestamp without time zone NOT NULL
);


ALTER TABLE public.clinic_charge_payments OWNER TO sante;

--
-- Name: clinic_charge_payments_id_seq; Type: SEQUENCE; Schema: public; Owner: sante
--

CREATE SEQUENCE public.clinic_charge_payments_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.clinic_charge_payments_id_seq OWNER TO sante;

--
-- Name: clinic_charge_payments_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: sante
--

ALTER SEQUENCE public.clinic_charge_payments_id_seq OWNED BY public.clinic_charge_payments.id;


--
-- Name: clinic_charges; Type: TABLE; Schema: public; Owner: sante
--

CREATE TABLE public.clinic_charges (
    id integer NOT NULL,
    clinic_id integer NOT NULL,
    patient_id integer NOT NULL,
    charge_type character varying(32) NOT NULL,
    source_type character varying(32) NOT NULL,
    source_id integer NOT NULL,
    description text NOT NULL,
    subtotal_amount_gnf integer,
    exemption_percent integer NOT NULL,
    exemption_amount_gnf integer NOT NULL,
    amount_gnf integer NOT NULL,
    payment_status character varying(32) NOT NULL,
    payment_method character varying(32),
    visit_id integer,
    invoice_id integer,
    recorded_by_user_id integer,
    paid_at timestamp without time zone,
    paid_amount_gnf integer NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL
);


ALTER TABLE public.clinic_charges OWNER TO sante;

--
-- Name: clinic_charges_id_seq; Type: SEQUENCE; Schema: public; Owner: sante
--

CREATE SEQUENCE public.clinic_charges_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.clinic_charges_id_seq OWNER TO sante;

--
-- Name: clinic_charges_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: sante
--

ALTER SEQUENCE public.clinic_charges_id_seq OWNED BY public.clinic_charges.id;


--
-- Name: clinic_lab_tests; Type: TABLE; Schema: public; Owner: sante
--

CREATE TABLE public.clinic_lab_tests (
    id integer NOT NULL,
    clinic_id integer NOT NULL,
    code character varying(64) NOT NULL,
    name character varying(255) NOT NULL,
    category character varying(64) NOT NULL,
    category_label character varying(128) NOT NULL,
    price_gnf integer,
    sort_order integer NOT NULL,
    active boolean NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL
);


ALTER TABLE public.clinic_lab_tests OWNER TO sante;

--
-- Name: clinic_lab_tests_id_seq; Type: SEQUENCE; Schema: public; Owner: sante
--

CREATE SEQUENCE public.clinic_lab_tests_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.clinic_lab_tests_id_seq OWNER TO sante;

--
-- Name: clinic_lab_tests_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: sante
--

ALTER SEQUENCE public.clinic_lab_tests_id_seq OWNED BY public.clinic_lab_tests.id;


--
-- Name: clinic_node_heartbeats; Type: TABLE; Schema: public; Owner: sante
--

CREATE TABLE public.clinic_node_heartbeats (
    id integer NOT NULL,
    clinic_id integer NOT NULL,
    node_id character varying(64) NOT NULL,
    software_version character varying(64),
    schema_version character varying(64),
    disk_free_bytes bigint,
    disk_total_bytes bigint,
    outbox_depth integer,
    last_backup_local_at timestamp without time zone,
    last_sync_success_at timestamp without time zone,
    license_state character varying(32),
    payload_json text,
    received_at timestamp without time zone NOT NULL
);


ALTER TABLE public.clinic_node_heartbeats OWNER TO sante;

--
-- Name: clinic_node_heartbeats_id_seq; Type: SEQUENCE; Schema: public; Owner: sante
--

CREATE SEQUENCE public.clinic_node_heartbeats_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.clinic_node_heartbeats_id_seq OWNER TO sante;

--
-- Name: clinic_node_heartbeats_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: sante
--

ALTER SEQUENCE public.clinic_node_heartbeats_id_seq OWNED BY public.clinic_node_heartbeats.id;


--
-- Name: clinic_node_licenses; Type: TABLE; Schema: public; Owner: sante
--

CREATE TABLE public.clinic_node_licenses (
    id integer NOT NULL,
    clinic_id integer NOT NULL,
    node_id character varying(64),
    plan character varying(64) NOT NULL,
    issued_at timestamp without time zone NOT NULL,
    valid_until timestamp without time zone NOT NULL,
    grace_until timestamp without time zone NOT NULL,
    token_json text NOT NULL,
    is_active boolean NOT NULL,
    created_at timestamp without time zone NOT NULL
);


ALTER TABLE public.clinic_node_licenses OWNER TO sante;

--
-- Name: clinic_node_licenses_id_seq; Type: SEQUENCE; Schema: public; Owner: sante
--

CREATE SEQUENCE public.clinic_node_licenses_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.clinic_node_licenses_id_seq OWNER TO sante;

--
-- Name: clinic_node_licenses_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: sante
--

ALTER SEQUENCE public.clinic_node_licenses_id_seq OWNED BY public.clinic_node_licenses.id;


--
-- Name: clinic_refunds; Type: TABLE; Schema: public; Owner: sante
--

CREATE TABLE public.clinic_refunds (
    id integer NOT NULL,
    clinic_id integer NOT NULL,
    patient_id integer NOT NULL,
    invoice_id integer NOT NULL,
    refund_number character varying(32) NOT NULL,
    original_amount_paid_gnf integer NOT NULL,
    service_paid_for text,
    amount_consumed_gnf integer NOT NULL,
    refund_amount_gnf integer NOT NULL,
    reason character varying(32) NOT NULL,
    reason_notes text,
    recipient_name character varying(255),
    recipient_relationship character varying(128),
    recipient_phone character varying(32),
    refund_method character varying(32),
    status character varying(32) NOT NULL,
    approved_by_user_id integer,
    paid_by_user_id integer,
    approved_at timestamp without time zone,
    paid_at timestamp without time zone,
    created_by_user_id integer,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL
);


ALTER TABLE public.clinic_refunds OWNER TO sante;

--
-- Name: clinic_refunds_id_seq; Type: SEQUENCE; Schema: public; Owner: sante
--

CREATE SEQUENCE public.clinic_refunds_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.clinic_refunds_id_seq OWNER TO sante;

--
-- Name: clinic_refunds_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: sante
--

ALTER SEQUENCE public.clinic_refunds_id_seq OWNED BY public.clinic_refunds.id;


--
-- Name: clinic_service_requests; Type: TABLE; Schema: public; Owner: sante
--

CREATE TABLE public.clinic_service_requests (
    id integer NOT NULL,
    clinic_id integer NOT NULL,
    patient_id integer NOT NULL,
    admission_id integer,
    request_number character varying(32) NOT NULL,
    service_category character varying(32) NOT NULL,
    service_name character varying(255) NOT NULL,
    department character varying(128),
    status character varying(32) NOT NULL,
    notes text,
    created_by_user_id integer,
    updated_by_user_id integer,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL
);


ALTER TABLE public.clinic_service_requests OWNER TO sante;

--
-- Name: clinic_service_requests_id_seq; Type: SEQUENCE; Schema: public; Owner: sante
--

CREATE SEQUENCE public.clinic_service_requests_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.clinic_service_requests_id_seq OWNER TO sante;

--
-- Name: clinic_service_requests_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: sante
--

ALTER SEQUENCE public.clinic_service_requests_id_seq OWNED BY public.clinic_service_requests.id;


--
-- Name: clinic_staff; Type: TABLE; Schema: public; Owner: sante
--

CREATE TABLE public.clinic_staff (
    id integer NOT NULL,
    clinic_id integer NOT NULL,
    user_id integer NOT NULL,
    is_active boolean NOT NULL,
    created_at timestamp without time zone NOT NULL
);


ALTER TABLE public.clinic_staff OWNER TO sante;

--
-- Name: clinic_staff_id_seq; Type: SEQUENCE; Schema: public; Owner: sante
--

CREATE SEQUENCE public.clinic_staff_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.clinic_staff_id_seq OWNER TO sante;

--
-- Name: clinic_staff_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: sante
--

ALTER SEQUENCE public.clinic_staff_id_seq OWNED BY public.clinic_staff.id;


--
-- Name: clinical_audit_logs; Type: TABLE; Schema: public; Owner: sante
--

CREATE TABLE public.clinical_audit_logs (
    id integer NOT NULL,
    actor_id integer NOT NULL,
    actor_role character varying(32) NOT NULL,
    clinic_id integer,
    patient_id integer,
    action character varying(32) NOT NULL,
    resource_type character varying(64) NOT NULL,
    resource_id integer,
    "timestamp" timestamp without time zone NOT NULL,
    ip character varying(64)
);


ALTER TABLE public.clinical_audit_logs OWNER TO sante;

--
-- Name: clinical_audit_logs_id_seq; Type: SEQUENCE; Schema: public; Owner: sante
--

CREATE SEQUENCE public.clinical_audit_logs_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.clinical_audit_logs_id_seq OWNER TO sante;

--
-- Name: clinical_audit_logs_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: sante
--

ALTER SEQUENCE public.clinical_audit_logs_id_seq OWNED BY public.clinical_audit_logs.id;


--
-- Name: clinical_notes; Type: TABLE; Schema: public; Owner: sante
--

CREATE TABLE public.clinical_notes (
    id integer NOT NULL,
    patient_id integer NOT NULL,
    doctor_id integer,
    appointment_id integer,
    note_type character varying(32) NOT NULL,
    contenu text NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL
);


ALTER TABLE public.clinical_notes OWNER TO sante;

--
-- Name: clinical_notes_id_seq; Type: SEQUENCE; Schema: public; Owner: sante
--

CREATE SEQUENCE public.clinical_notes_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.clinical_notes_id_seq OWNER TO sante;

--
-- Name: clinical_notes_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: sante
--

ALTER SEQUENCE public.clinical_notes_id_seq OWNED BY public.clinical_notes.id;


--
-- Name: clinical_visits; Type: TABLE; Schema: public; Owner: sante
--

CREATE TABLE public.clinical_visits (
    id integer NOT NULL,
    clinic_id integer NOT NULL,
    patient_id integer NOT NULL,
    appointment_id integer,
    consultation_id integer,
    admission_id integer,
    status character varying(32) NOT NULL,
    started_at timestamp without time zone NOT NULL,
    closed_at timestamp without time zone,
    discharged_at timestamp without time zone,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL
);


ALTER TABLE public.clinical_visits OWNER TO sante;

--
-- Name: clinical_visits_id_seq; Type: SEQUENCE; Schema: public; Owner: sante
--

CREATE SEQUENCE public.clinical_visits_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.clinical_visits_id_seq OWNER TO sante;

--
-- Name: clinical_visits_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: sante
--

ALTER SEQUENCE public.clinical_visits_id_seq OWNED BY public.clinical_visits.id;


--
-- Name: clinics; Type: TABLE; Schema: public; Owner: sante
--

CREATE TABLE public.clinics (
    id integer NOT NULL,
    name character varying(255) NOT NULL,
    address text,
    city character varying(128),
    phone character varying(32),
    email character varying(255),
    is_active boolean NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL
);


ALTER TABLE public.clinics OWNER TO sante;

--
-- Name: clinics_id_seq; Type: SEQUENCE; Schema: public; Owner: sante
--

CREATE SEQUENCE public.clinics_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.clinics_id_seq OWNER TO sante;

--
-- Name: clinics_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: sante
--

ALTER SEQUENCE public.clinics_id_seq OWNED BY public.clinics.id;


--
-- Name: consultation_summaries; Type: TABLE; Schema: public; Owner: sante
--

CREATE TABLE public.consultation_summaries (
    id integer NOT NULL,
    patient_id integer NOT NULL,
    doctor_id integer,
    appointment_id integer,
    diagnostic text,
    traitement text,
    recommandations text,
    created_at timestamp without time zone NOT NULL
);


ALTER TABLE public.consultation_summaries OWNER TO sante;

--
-- Name: consultation_summaries_id_seq; Type: SEQUENCE; Schema: public; Owner: sante
--

CREATE SEQUENCE public.consultation_summaries_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.consultation_summaries_id_seq OWNER TO sante;

--
-- Name: consultation_summaries_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: sante
--

ALTER SEQUENCE public.consultation_summaries_id_seq OWNED BY public.consultation_summaries.id;


--
-- Name: consultations; Type: TABLE; Schema: public; Owner: sante
--

CREATE TABLE public.consultations (
    id integer NOT NULL,
    clinic_id integer NOT NULL,
    appointment_id integer NOT NULL,
    patient_id integer NOT NULL,
    doctor_id integer NOT NULL,
    status character varying(32) NOT NULL,
    chief_complaint text,
    history text,
    examination text,
    diagnosis text,
    treatment_plan text,
    medical_history text,
    surgical_history text,
    gyneco_history text,
    allergies text,
    current_treatments text,
    observations text,
    target_specialty_code character varying(64),
    target_specialty_other character varying(255),
    hospitalized_vitals text,
    post_op_report text,
    discharge_summary_text text,
    discharge_authorization text,
    discharge_against_advice text,
    prescription_text text,
    discharge_form_json text,
    started_at timestamp without time zone,
    completed_at timestamp without time zone,
    deleted_at timestamp without time zone,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL
);


ALTER TABLE public.consultations OWNER TO sante;

--
-- Name: consultations_id_seq; Type: SEQUENCE; Schema: public; Owner: sante
--

CREATE SEQUENCE public.consultations_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.consultations_id_seq OWNER TO sante;

--
-- Name: consultations_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: sante
--

ALTER SEQUENCE public.consultations_id_seq OWNED BY public.consultations.id;


--
-- Name: discharge_summaries; Type: TABLE; Schema: public; Owner: sante
--

CREATE TABLE public.discharge_summaries (
    id integer NOT NULL,
    clinic_id integer NOT NULL,
    patient_id integer NOT NULL,
    visit_id integer,
    admission_id integer,
    consultation_id integer,
    invoice_id integer,
    discharge_type character varying(32) NOT NULL,
    status character varying(32) NOT NULL,
    diagnoses text,
    procedures text,
    medications text,
    clinical_summary text,
    follow_up_instructions text,
    invoice_validated boolean NOT NULL,
    archived_to_emr boolean NOT NULL,
    discharged_by_user_id integer,
    discharged_at timestamp without time zone,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL
);


ALTER TABLE public.discharge_summaries OWNER TO sante;

--
-- Name: discharge_summaries_id_seq; Type: SEQUENCE; Schema: public; Owner: sante
--

CREATE SEQUENCE public.discharge_summaries_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.discharge_summaries_id_seq OWNER TO sante;

--
-- Name: discharge_summaries_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: sante
--

ALTER SEQUENCE public.discharge_summaries_id_seq OWNED BY public.discharge_summaries.id;


--
-- Name: doctor_availabilities; Type: TABLE; Schema: public; Owner: sante
--

CREATE TABLE public.doctor_availabilities (
    id integer NOT NULL,
    doctor_id integer NOT NULL,
    day_of_week integer NOT NULL,
    start_time time without time zone NOT NULL,
    end_time time without time zone NOT NULL,
    is_active boolean
);


ALTER TABLE public.doctor_availabilities OWNER TO sante;

--
-- Name: doctor_availabilities_id_seq; Type: SEQUENCE; Schema: public; Owner: sante
--

CREATE SEQUENCE public.doctor_availabilities_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.doctor_availabilities_id_seq OWNER TO sante;

--
-- Name: doctor_availabilities_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: sante
--

ALTER SEQUENCE public.doctor_availabilities_id_seq OWNED BY public.doctor_availabilities.id;


--
-- Name: doctor_medicine_deliveries; Type: TABLE; Schema: public; Owner: sante
--

CREATE TABLE public.doctor_medicine_deliveries (
    id integer NOT NULL,
    clinic_id integer NOT NULL,
    patient_id integer,
    patient_name character varying(255) NOT NULL,
    medicine_name character varying(255) NOT NULL,
    quantity integer NOT NULL,
    doctor_name character varying(255) NOT NULL,
    reason text,
    source character varying(32) NOT NULL,
    delivered_at timestamp without time zone NOT NULL,
    recorded_by_user_id integer,
    created_at timestamp without time zone NOT NULL,
    deleted_at timestamp without time zone
);


ALTER TABLE public.doctor_medicine_deliveries OWNER TO sante;

--
-- Name: doctor_medicine_deliveries_id_seq; Type: SEQUENCE; Schema: public; Owner: sante
--

CREATE SEQUENCE public.doctor_medicine_deliveries_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.doctor_medicine_deliveries_id_seq OWNER TO sante;

--
-- Name: doctor_medicine_deliveries_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: sante
--

ALTER SEQUENCE public.doctor_medicine_deliveries_id_seq OWNED BY public.doctor_medicine_deliveries.id;


--
-- Name: doctors; Type: TABLE; Schema: public; Owner: sante
--

CREATE TABLE public.doctors (
    id integer NOT NULL,
    user_id integer NOT NULL,
    first_name character varying NOT NULL,
    last_name character varying NOT NULL,
    specialty character varying NOT NULL,
    city character varying NOT NULL,
    phone character varying NOT NULL,
    photo_url character varying,
    consultation_fee double precision NOT NULL,
    latitude double precision,
    longitude double precision,
    clinic_id integer
);


ALTER TABLE public.doctors OWNER TO sante;

--
-- Name: doctors_id_seq; Type: SEQUENCE; Schema: public; Owner: sante
--

CREATE SEQUENCE public.doctors_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.doctors_id_seq OWNER TO sante;

--
-- Name: doctors_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: sante
--

ALTER SEQUENCE public.doctors_id_seq OWNED BY public.doctors.id;


--
-- Name: email_verification_tokens; Type: TABLE; Schema: public; Owner: sante
--

CREATE TABLE public.email_verification_tokens (
    id integer NOT NULL,
    user_id integer NOT NULL,
    token_hash character varying(128) NOT NULL,
    expires_at timestamp without time zone NOT NULL,
    used_at timestamp without time zone,
    created_at timestamp without time zone NOT NULL
);


ALTER TABLE public.email_verification_tokens OWNER TO sante;

--
-- Name: email_verification_tokens_id_seq; Type: SEQUENCE; Schema: public; Owner: sante
--

CREATE SEQUENCE public.email_verification_tokens_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.email_verification_tokens_id_seq OWNER TO sante;

--
-- Name: email_verification_tokens_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: sante
--

ALTER SEQUENCE public.email_verification_tokens_id_seq OWNED BY public.email_verification_tokens.id;


--
-- Name: follow_up_schedules; Type: TABLE; Schema: public; Owner: sante
--

CREATE TABLE public.follow_up_schedules (
    id integer NOT NULL,
    patient_id integer NOT NULL,
    clinic_id integer NOT NULL,
    consultation_id integer,
    doctor_id integer NOT NULL,
    scheduled_date date NOT NULL,
    interval_type character varying(16) NOT NULL,
    visit_type character varying(32) NOT NULL,
    reason text,
    clinical_notes text,
    status character varying(32) NOT NULL,
    follow_up_appointment_id integer,
    created_by_user_id integer,
    deleted_at timestamp without time zone,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL
);


ALTER TABLE public.follow_up_schedules OWNER TO sante;

--
-- Name: follow_up_schedules_id_seq; Type: SEQUENCE; Schema: public; Owner: sante
--

CREATE SEQUENCE public.follow_up_schedules_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.follow_up_schedules_id_seq OWNER TO sante;

--
-- Name: follow_up_schedules_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: sante
--

ALTER SEQUENCE public.follow_up_schedules_id_seq OWNED BY public.follow_up_schedules.id;


--
-- Name: hospital_beds; Type: TABLE; Schema: public; Owner: sante
--

CREATE TABLE public.hospital_beds (
    id integer NOT NULL,
    room_id integer NOT NULL,
    bed_number character varying(32) NOT NULL,
    status character varying(32) NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL
);


ALTER TABLE public.hospital_beds OWNER TO sante;

--
-- Name: hospital_beds_id_seq; Type: SEQUENCE; Schema: public; Owner: sante
--

CREATE SEQUENCE public.hospital_beds_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.hospital_beds_id_seq OWNER TO sante;

--
-- Name: hospital_beds_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: sante
--

ALTER SEQUENCE public.hospital_beds_id_seq OWNED BY public.hospital_beds.id;


--
-- Name: hospital_rooms; Type: TABLE; Schema: public; Owner: sante
--

CREATE TABLE public.hospital_rooms (
    id integer NOT NULL,
    clinic_id integer NOT NULL,
    ward_name character varying(128) NOT NULL,
    room_number character varying(32) NOT NULL,
    room_type character varying(64) NOT NULL,
    capacity integer NOT NULL,
    status character varying(32) NOT NULL,
    notes text,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL
);


ALTER TABLE public.hospital_rooms OWNER TO sante;

--
-- Name: hospital_rooms_id_seq; Type: SEQUENCE; Schema: public; Owner: sante
--

CREATE SEQUENCE public.hospital_rooms_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.hospital_rooms_id_seq OWNER TO sante;

--
-- Name: hospital_rooms_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: sante
--

ALTER SEQUENCE public.hospital_rooms_id_seq OWNED BY public.hospital_rooms.id;


--
-- Name: imaging_orders; Type: TABLE; Schema: public; Owner: sante
--

CREATE TABLE public.imaging_orders (
    id integer NOT NULL,
    clinic_id integer NOT NULL,
    patient_id integer NOT NULL,
    consultation_id integer NOT NULL,
    modality character varying(32) NOT NULL,
    body_part character varying(128),
    clinical_indication text,
    priority character varying(16) NOT NULL,
    status character varying(32) NOT NULL,
    scheduled_at timestamp without time zone,
    ordered_by_user_id integer,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL
);


ALTER TABLE public.imaging_orders OWNER TO sante;

--
-- Name: imaging_orders_id_seq; Type: SEQUENCE; Schema: public; Owner: sante
--

CREATE SEQUENCE public.imaging_orders_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.imaging_orders_id_seq OWNER TO sante;

--
-- Name: imaging_orders_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: sante
--

ALTER SEQUENCE public.imaging_orders_id_seq OWNED BY public.imaging_orders.id;


--
-- Name: imaging_results; Type: TABLE; Schema: public; Owner: sante
--

CREATE TABLE public.imaging_results (
    id integer NOT NULL,
    order_id integer NOT NULL,
    findings text,
    impression text,
    recommendations text,
    attachment_url text,
    reported_by_user_id integer,
    validated_by_user_id integer,
    reported_at timestamp without time zone,
    validated_at timestamp without time zone,
    status character varying(32) NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL
);


ALTER TABLE public.imaging_results OWNER TO sante;

--
-- Name: imaging_results_id_seq; Type: SEQUENCE; Schema: public; Owner: sante
--

CREATE SEQUENCE public.imaging_results_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.imaging_results_id_seq OWNER TO sante;

--
-- Name: imaging_results_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: sante
--

ALTER SEQUENCE public.imaging_results_id_seq OWNED BY public.imaging_results.id;


--
-- Name: immunization_records; Type: TABLE; Schema: public; Owner: sante
--

CREATE TABLE public.immunization_records (
    id integer NOT NULL,
    clinic_id integer NOT NULL,
    patient_id integer NOT NULL,
    vaccine_code character varying(32) NOT NULL,
    vaccine_name character varying(128) NOT NULL,
    dose_label character varying(64),
    dose_number integer,
    batch_number character varying(64),
    vaccine_expiry_date date,
    injection_site character varying(64),
    vaccination_strategy character varying(32),
    age_at_vaccination_months integer,
    age_at_vaccination_days integer,
    aefi_notes text,
    administered_at date NOT NULL,
    next_appointment_date date,
    vaccinator_name character varying(128),
    administered_by_user_id integer,
    notes text,
    created_at timestamp without time zone NOT NULL,
    deleted_at timestamp without time zone
);


ALTER TABLE public.immunization_records OWNER TO sante;

--
-- Name: immunization_records_id_seq; Type: SEQUENCE; Schema: public; Owner: sante
--

CREATE SEQUENCE public.immunization_records_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.immunization_records_id_seq OWNER TO sante;

--
-- Name: immunization_records_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: sante
--

ALTER SEQUENCE public.immunization_records_id_seq OWNED BY public.immunization_records.id;


--
-- Name: invoice_items; Type: TABLE; Schema: public; Owner: sante
--

CREATE TABLE public.invoice_items (
    id integer NOT NULL,
    invoice_id integer NOT NULL,
    charge_type character varying(32) NOT NULL,
    source_type character varying(32) NOT NULL,
    source_id integer NOT NULL,
    description text NOT NULL,
    quantity integer NOT NULL,
    unit_price_gnf integer NOT NULL,
    amount_gnf integer NOT NULL,
    clinic_charge_id integer,
    created_at timestamp without time zone NOT NULL
);


ALTER TABLE public.invoice_items OWNER TO sante;

--
-- Name: invoice_items_id_seq; Type: SEQUENCE; Schema: public; Owner: sante
--

CREATE SEQUENCE public.invoice_items_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.invoice_items_id_seq OWNER TO sante;

--
-- Name: invoice_items_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: sante
--

ALTER SEQUENCE public.invoice_items_id_seq OWNED BY public.invoice_items.id;


--
-- Name: invoices; Type: TABLE; Schema: public; Owner: sante
--

CREATE TABLE public.invoices (
    id integer NOT NULL,
    clinic_id integer NOT NULL,
    patient_id integer NOT NULL,
    visit_id integer,
    invoice_number character varying(32) NOT NULL,
    department character varying(128),
    status character varying(32) NOT NULL,
    subtotal_amount_gnf integer NOT NULL,
    exemption_percent integer NOT NULL,
    exemption_amount_gnf integer NOT NULL,
    total_amount_gnf integer NOT NULL,
    paid_amount_gnf integer NOT NULL,
    notes text,
    issued_at timestamp without time zone,
    paid_at timestamp without time zone,
    created_by_user_id integer,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL
);


ALTER TABLE public.invoices OWNER TO sante;

--
-- Name: invoices_id_seq; Type: SEQUENCE; Schema: public; Owner: sante
--

CREATE SEQUENCE public.invoices_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.invoices_id_seq OWNER TO sante;

--
-- Name: invoices_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: sante
--

ALTER SEQUENCE public.invoices_id_seq OWNED BY public.invoices.id;


--
-- Name: lab_orders; Type: TABLE; Schema: public; Owner: sante
--

CREATE TABLE public.lab_orders (
    id integer NOT NULL,
    clinic_id integer NOT NULL,
    consultation_id integer NOT NULL,
    patient_id integer NOT NULL,
    ordered_by_user_id integer NOT NULL,
    doctor_id integer NOT NULL,
    test_code character varying(64) NOT NULL,
    test_name character varying(255) NOT NULL,
    priority character varying(16) NOT NULL,
    status character varying(32) NOT NULL,
    clinical_notes text,
    deleted_at timestamp without time zone,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL
);


ALTER TABLE public.lab_orders OWNER TO sante;

--
-- Name: lab_orders_id_seq; Type: SEQUENCE; Schema: public; Owner: sante
--

CREATE SEQUENCE public.lab_orders_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.lab_orders_id_seq OWNER TO sante;

--
-- Name: lab_orders_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: sante
--

ALTER SEQUENCE public.lab_orders_id_seq OWNED BY public.lab_orders.id;


--
-- Name: lab_results; Type: TABLE; Schema: public; Owner: sante
--

CREATE TABLE public.lab_results (
    id integer NOT NULL,
    lab_order_id integer NOT NULL,
    recorded_by_user_id integer NOT NULL,
    result_summary text NOT NULL,
    result_data text,
    reference_range text,
    interpretation text,
    status character varying(16) NOT NULL,
    validated_at timestamp without time zone,
    validated_by_user_id integer,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL
);


ALTER TABLE public.lab_results OWNER TO sante;

--
-- Name: lab_results_id_seq; Type: SEQUENCE; Schema: public; Owner: sante
--

CREATE SEQUENCE public.lab_results_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.lab_results_id_seq OWNER TO sante;

--
-- Name: lab_results_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: sante
--

ALTER SEQUENCE public.lab_results_id_seq OWNED BY public.lab_results.id;


--
-- Name: messages; Type: TABLE; Schema: public; Owner: sante
--

CREATE TABLE public.messages (
    id integer NOT NULL,
    appointment_id integer NOT NULL,
    sender_user_id integer NOT NULL,
    content text,
    attachment_name character varying,
    attachment_url character varying,
    attachment_storage_key character varying,
    attachment_mime_type character varying,
    attachment_size_bytes integer,
    created_at timestamp without time zone NOT NULL
);


ALTER TABLE public.messages OWNER TO sante;

--
-- Name: messages_id_seq; Type: SEQUENCE; Schema: public; Owner: sante
--

CREATE SEQUENCE public.messages_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.messages_id_seq OWNER TO sante;

--
-- Name: messages_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: sante
--

ALTER SEQUENCE public.messages_id_seq OWNED BY public.messages.id;


--
-- Name: notification_events; Type: TABLE; Schema: public; Owner: sante
--

CREATE TABLE public.notification_events (
    id integer NOT NULL,
    user_id integer NOT NULL,
    channel character varying(32) NOT NULL,
    subject character varying(255) NOT NULL,
    body text NOT NULL,
    meta character varying(1024),
    created_at timestamp without time zone NOT NULL
);


ALTER TABLE public.notification_events OWNER TO sante;

--
-- Name: notification_events_id_seq; Type: SEQUENCE; Schema: public; Owner: sante
--

CREATE SEQUENCE public.notification_events_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.notification_events_id_seq OWNER TO sante;

--
-- Name: notification_events_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: sante
--

ALTER SEQUENCE public.notification_events_id_seq OWNED BY public.notification_events.id;


--
-- Name: nurse_assessments; Type: TABLE; Schema: public; Owner: sante
--

CREATE TABLE public.nurse_assessments (
    id integer NOT NULL,
    clinic_id integer NOT NULL,
    patient_id integer NOT NULL,
    admission_id integer,
    appointment_id integer,
    consultation_id integer,
    nurse_user_id integer,
    nurse_name character varying(128),
    temperature_c double precision,
    bp_systolic integer,
    bp_diastolic integer,
    heart_rate integer,
    respiratory_rate integer,
    height_cm double precision,
    weight_kg double precision,
    bmi double precision,
    vitals_observations text,
    reason_for_consultation text,
    history_of_present_illness text,
    medical_history text,
    surgical_history text,
    gynecological_history text,
    allergies text,
    current_treatments text,
    hospitalized_daily_vitals text,
    prescription text,
    nurse_notes text,
    recorded_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    deleted_at timestamp without time zone
);


ALTER TABLE public.nurse_assessments OWNER TO sante;

--
-- Name: nurse_assessments_id_seq; Type: SEQUENCE; Schema: public; Owner: sante
--

CREATE SEQUENCE public.nurse_assessments_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.nurse_assessments_id_seq OWNER TO sante;

--
-- Name: nurse_assessments_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: sante
--

ALTER SEQUENCE public.nurse_assessments_id_seq OWNED BY public.nurse_assessments.id;


--
-- Name: nursing_procedures; Type: TABLE; Schema: public; Owner: sante
--

CREATE TABLE public.nursing_procedures (
    id integer NOT NULL,
    clinic_id integer NOT NULL,
    patient_id integer NOT NULL,
    procedure_type character varying(32) NOT NULL,
    procedure_date date NOT NULL,
    procedure_time character varying(8),
    nurse_user_id integer,
    nurse_name character varying(128),
    notes text,
    created_at timestamp without time zone NOT NULL,
    deleted_at timestamp without time zone
);


ALTER TABLE public.nursing_procedures OWNER TO sante;

--
-- Name: nursing_procedures_id_seq; Type: SEQUENCE; Schema: public; Owner: sante
--

CREATE SEQUENCE public.nursing_procedures_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.nursing_procedures_id_seq OWNER TO sante;

--
-- Name: nursing_procedures_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: sante
--

ALTER SEQUENCE public.nursing_procedures_id_seq OWNED BY public.nursing_procedures.id;


--
-- Name: nutrition_assessments; Type: TABLE; Schema: public; Owner: sante
--

CREATE TABLE public.nutrition_assessments (
    id integer NOT NULL,
    clinic_id integer NOT NULL,
    patient_id integer NOT NULL,
    consultation_id integer,
    age_months integer,
    weight_kg double precision,
    height_cm double precision,
    muac_cm double precision,
    nutritional_status character varying(32),
    nutritional_diagnosis text,
    is_follow_up boolean NOT NULL,
    follow_up_date date,
    recommendations text,
    notes text,
    recorded_by_user_id integer,
    recorded_at timestamp without time zone NOT NULL,
    deleted_at timestamp without time zone
);


ALTER TABLE public.nutrition_assessments OWNER TO sante;

--
-- Name: nutrition_assessments_id_seq; Type: SEQUENCE; Schema: public; Owner: sante
--

CREATE SEQUENCE public.nutrition_assessments_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.nutrition_assessments_id_seq OWNER TO sante;

--
-- Name: nutrition_assessments_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: sante
--

ALTER SEQUENCE public.nutrition_assessments_id_seq OWNED BY public.nutrition_assessments.id;


--
-- Name: password_reset_tokens; Type: TABLE; Schema: public; Owner: sante
--

CREATE TABLE public.password_reset_tokens (
    id integer NOT NULL,
    user_id integer NOT NULL,
    token_hash character varying(128) NOT NULL,
    expires_at timestamp without time zone NOT NULL,
    used_at timestamp without time zone,
    created_at timestamp without time zone NOT NULL
);


ALTER TABLE public.password_reset_tokens OWNER TO sante;

--
-- Name: password_reset_tokens_id_seq; Type: SEQUENCE; Schema: public; Owner: sante
--

CREATE SEQUENCE public.password_reset_tokens_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.password_reset_tokens_id_seq OWNER TO sante;

--
-- Name: password_reset_tokens_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: sante
--

ALTER SEQUENCE public.password_reset_tokens_id_seq OWNED BY public.password_reset_tokens.id;


--
-- Name: patient_allergies; Type: TABLE; Schema: public; Owner: sante
--

CREATE TABLE public.patient_allergies (
    id integer NOT NULL,
    patient_id integer NOT NULL,
    allergen character varying(255) NOT NULL,
    severity character varying(32) NOT NULL,
    reaction text,
    recorded_by_user_id integer,
    is_active boolean NOT NULL,
    deleted_at timestamp without time zone,
    created_at timestamp without time zone NOT NULL
);


ALTER TABLE public.patient_allergies OWNER TO sante;

--
-- Name: patient_allergies_id_seq; Type: SEQUENCE; Schema: public; Owner: sante
--

CREATE SEQUENCE public.patient_allergies_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.patient_allergies_id_seq OWNER TO sante;

--
-- Name: patient_allergies_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: sante
--

ALTER SEQUENCE public.patient_allergies_id_seq OWNED BY public.patient_allergies.id;


--
-- Name: patient_chronic_conditions; Type: TABLE; Schema: public; Owner: sante
--

CREATE TABLE public.patient_chronic_conditions (
    id integer NOT NULL,
    patient_id integer NOT NULL,
    condition_name character varying(255) NOT NULL,
    diagnosed_at date,
    status character varying(32) NOT NULL,
    notes text,
    recorded_by_user_id integer,
    deleted_at timestamp without time zone,
    created_at timestamp without time zone NOT NULL
);


ALTER TABLE public.patient_chronic_conditions OWNER TO sante;

--
-- Name: patient_chronic_conditions_id_seq; Type: SEQUENCE; Schema: public; Owner: sante
--

CREATE SEQUENCE public.patient_chronic_conditions_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.patient_chronic_conditions_id_seq OWNER TO sante;

--
-- Name: patient_chronic_conditions_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: sante
--

ALTER SEQUENCE public.patient_chronic_conditions_id_seq OWNED BY public.patient_chronic_conditions.id;


--
-- Name: patient_documents; Type: TABLE; Schema: public; Owner: sante
--

CREATE TABLE public.patient_documents (
    id integer NOT NULL,
    patient_id integer NOT NULL,
    uploaded_by integer NOT NULL,
    type_document character varying(64) NOT NULL,
    file_path character varying(255) NOT NULL,
    created_at timestamp without time zone NOT NULL
);


ALTER TABLE public.patient_documents OWNER TO sante;

--
-- Name: patient_documents_id_seq; Type: SEQUENCE; Schema: public; Owner: sante
--

CREATE SEQUENCE public.patient_documents_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.patient_documents_id_seq OWNER TO sante;

--
-- Name: patient_documents_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: sante
--

ALTER SEQUENCE public.patient_documents_id_seq OWNED BY public.patient_documents.id;


--
-- Name: patient_medical_records; Type: TABLE; Schema: public; Owner: sante
--

CREATE TABLE public.patient_medical_records (
    id integer NOT NULL,
    patient_id integer NOT NULL,
    blood_type character varying(8),
    general_notes text,
    last_specialty character varying(255),
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL
);


ALTER TABLE public.patient_medical_records OWNER TO sante;

--
-- Name: patient_medical_records_id_seq; Type: SEQUENCE; Schema: public; Owner: sante
--

CREATE SEQUENCE public.patient_medical_records_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.patient_medical_records_id_seq OWNER TO sante;

--
-- Name: patient_medical_records_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: sante
--

ALTER SEQUENCE public.patient_medical_records_id_seq OWNED BY public.patient_medical_records.id;


--
-- Name: patient_stays; Type: TABLE; Schema: public; Owner: sante
--

CREATE TABLE public.patient_stays (
    id integer NOT NULL,
    admission_id integer NOT NULL,
    bed_id integer NOT NULL,
    assigned_at timestamp without time zone NOT NULL,
    released_at timestamp without time zone,
    is_current boolean NOT NULL,
    transfer_reason text,
    assigned_by_user_id integer,
    created_at timestamp without time zone NOT NULL
);


ALTER TABLE public.patient_stays OWNER TO sante;

--
-- Name: patient_stays_id_seq; Type: SEQUENCE; Schema: public; Owner: sante
--

CREATE SEQUENCE public.patient_stays_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.patient_stays_id_seq OWNER TO sante;

--
-- Name: patient_stays_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: sante
--

ALTER SEQUENCE public.patient_stays_id_seq OWNED BY public.patient_stays.id;


--
-- Name: patient_visit_workflow_steps; Type: TABLE; Schema: public; Owner: sante
--

CREATE TABLE public.patient_visit_workflow_steps (
    id integer NOT NULL,
    workflow_id integer NOT NULL,
    department character varying(32) NOT NULL,
    step_order integer NOT NULL,
    status character varying(32) NOT NULL,
    started_at timestamp without time zone,
    completed_at timestamp without time zone,
    completed_by_user_id integer
);


ALTER TABLE public.patient_visit_workflow_steps OWNER TO sante;

--
-- Name: patient_visit_workflow_steps_id_seq; Type: SEQUENCE; Schema: public; Owner: sante
--

CREATE SEQUENCE public.patient_visit_workflow_steps_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.patient_visit_workflow_steps_id_seq OWNER TO sante;

--
-- Name: patient_visit_workflow_steps_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: sante
--

ALTER SEQUENCE public.patient_visit_workflow_steps_id_seq OWNED BY public.patient_visit_workflow_steps.id;


--
-- Name: patient_visit_workflows; Type: TABLE; Schema: public; Owner: sante
--

CREATE TABLE public.patient_visit_workflows (
    id integer NOT NULL,
    clinic_id integer NOT NULL,
    patient_id integer NOT NULL,
    clinical_visit_id integer,
    workflow_type character varying(32) NOT NULL,
    current_department character varying(32) NOT NULL,
    status character varying(32) NOT NULL,
    notes text,
    created_by_user_id integer,
    started_at timestamp without time zone NOT NULL,
    completed_at timestamp without time zone,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL
);


ALTER TABLE public.patient_visit_workflows OWNER TO sante;

--
-- Name: patient_visit_workflows_id_seq; Type: SEQUENCE; Schema: public; Owner: sante
--

CREATE SEQUENCE public.patient_visit_workflows_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.patient_visit_workflows_id_seq OWNER TO sante;

--
-- Name: patient_visit_workflows_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: sante
--

ALTER SEQUENCE public.patient_visit_workflows_id_seq OWNED BY public.patient_visit_workflows.id;


--
-- Name: patient_vital_signs; Type: TABLE; Schema: public; Owner: sante
--

CREATE TABLE public.patient_vital_signs (
    id integer NOT NULL,
    patient_id integer NOT NULL,
    consultation_id integer,
    bp_systolic integer,
    bp_diastolic integer,
    heart_rate integer,
    temperature_c double precision,
    weight_kg double precision,
    height_cm double precision,
    respiratory_rate integer,
    bmi double precision,
    spo2 integer,
    notes text,
    recorded_by_user_id integer,
    recorded_at timestamp without time zone NOT NULL,
    deleted_at timestamp without time zone
);


ALTER TABLE public.patient_vital_signs OWNER TO sante;

--
-- Name: patient_vital_signs_id_seq; Type: SEQUENCE; Schema: public; Owner: sante
--

CREATE SEQUENCE public.patient_vital_signs_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.patient_vital_signs_id_seq OWNER TO sante;

--
-- Name: patient_vital_signs_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: sante
--

ALTER SEQUENCE public.patient_vital_signs_id_seq OWNED BY public.patient_vital_signs.id;


--
-- Name: patients; Type: TABLE; Schema: public; Owner: sante
--

CREATE TABLE public.patients (
    id integer NOT NULL,
    clinic_id integer,
    user_id integer,
    first_name character varying,
    last_name character varying,
    age integer,
    gender character varying,
    date_of_birth date,
    date_of_birth_precision character varying(16) NOT NULL,
    patient_number character varying(32),
    qr_token character varying(64),
    photo_url text,
    phone character varying(32),
    phone_secondary character varying(32),
    email character varying(255),
    address text,
    commune character varying(128),
    city character varying(128),
    region character varying(128),
    country character varying(128),
    place_of_birth character varying(255),
    nationality character varying(128),
    marital_status character varying(64),
    preferred_language character varying(64),
    emergency_contact character varying(255),
    emergency_contact_json text,
    payer_json text,
    mother_name character varying(255),
    mother_first_name character varying(128),
    mother_last_name character varying(128),
    profession character varying(128),
    quartier character varying(255),
    visit_destination character varying(255),
    is_newborn boolean NOT NULL,
    registration_date date,
    is_archived boolean NOT NULL,
    archived_at timestamp without time zone,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL
);


ALTER TABLE public.patients OWNER TO sante;

--
-- Name: patients_id_seq; Type: SEQUENCE; Schema: public; Owner: sante
--

CREATE SEQUENCE public.patients_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.patients_id_seq OWNER TO sante;

--
-- Name: patients_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: sante
--

ALTER SEQUENCE public.patients_id_seq OWNED BY public.patients.id;


--
-- Name: payment_records; Type: TABLE; Schema: public; Owner: sante
--

CREATE TABLE public.payment_records (
    id integer NOT NULL,
    invoice_id integer NOT NULL,
    amount_gnf integer NOT NULL,
    payment_method character varying(32) NOT NULL,
    reference character varying(128),
    recorded_by_user_id integer,
    paid_at timestamp without time zone NOT NULL,
    created_at timestamp without time zone NOT NULL
);


ALTER TABLE public.payment_records OWNER TO sante;

--
-- Name: payment_records_id_seq; Type: SEQUENCE; Schema: public; Owner: sante
--

CREATE SEQUENCE public.payment_records_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.payment_records_id_seq OWNER TO sante;

--
-- Name: payment_records_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: sante
--

ALTER SEQUENCE public.payment_records_id_seq OWNED BY public.payment_records.id;


--
-- Name: payments; Type: TABLE; Schema: public; Owner: sante
--

CREATE TABLE public.payments (
    id integer NOT NULL,
    appointment_id integer NOT NULL,
    payment_id character varying,
    stripe_session_id character varying,
    amount integer NOT NULL,
    amount_refunded integer NOT NULL,
    currency character varying,
    status character varying NOT NULL,
    refund_status character varying NOT NULL,
    settlement_channel character varying,
    last_stripe_event_id character varying,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL
);


ALTER TABLE public.payments OWNER TO sante;

--
-- Name: payments_id_seq; Type: SEQUENCE; Schema: public; Owner: sante
--

CREATE SEQUENCE public.payments_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.payments_id_seq OWNER TO sante;

--
-- Name: payments_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: sante
--

ALTER SEQUENCE public.payments_id_seq OWNED BY public.payments.id;


--
-- Name: pharmacy_inventory; Type: TABLE; Schema: public; Owner: sante
--

CREATE TABLE public.pharmacy_inventory (
    id integer NOT NULL,
    clinic_id integer NOT NULL,
    sku character varying(64) NOT NULL,
    medication_name character varying(255) NOT NULL,
    quantity integer NOT NULL,
    reorder_level integer NOT NULL,
    unit_price_gnf integer NOT NULL,
    purchase_price_gnf integer,
    batch_number character varying(64),
    expiry_date date,
    supplier character varying(128),
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL
);


ALTER TABLE public.pharmacy_inventory OWNER TO sante;

--
-- Name: pharmacy_inventory_id_seq; Type: SEQUENCE; Schema: public; Owner: sante
--

CREATE SEQUENCE public.pharmacy_inventory_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.pharmacy_inventory_id_seq OWNER TO sante;

--
-- Name: pharmacy_inventory_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: sante
--

ALTER SEQUENCE public.pharmacy_inventory_id_seq OWNED BY public.pharmacy_inventory.id;


--
-- Name: pharmacy_orders; Type: TABLE; Schema: public; Owner: sante
--

CREATE TABLE public.pharmacy_orders (
    id integer NOT NULL,
    clinic_id integer NOT NULL,
    prescription_id integer NOT NULL,
    patient_id integer NOT NULL,
    status character varying(32) NOT NULL,
    prepared_by_user_id integer,
    dispensed_at timestamp without time zone,
    notes text,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL
);


ALTER TABLE public.pharmacy_orders OWNER TO sante;

--
-- Name: pharmacy_orders_id_seq; Type: SEQUENCE; Schema: public; Owner: sante
--

CREATE SEQUENCE public.pharmacy_orders_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.pharmacy_orders_id_seq OWNER TO sante;

--
-- Name: pharmacy_orders_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: sante
--

ALTER SEQUENCE public.pharmacy_orders_id_seq OWNED BY public.pharmacy_orders.id;


--
-- Name: prescription_items; Type: TABLE; Schema: public; Owner: sante
--

CREATE TABLE public.prescription_items (
    id integer NOT NULL,
    prescription_id integer NOT NULL,
    medication_name character varying(255) NOT NULL,
    dosage character varying(128) NOT NULL,
    route character varying(64) NOT NULL,
    frequency character varying(128) NOT NULL,
    duration_days integer,
    quantity integer,
    instructions text
);


ALTER TABLE public.prescription_items OWNER TO sante;

--
-- Name: prescription_items_id_seq; Type: SEQUENCE; Schema: public; Owner: sante
--

CREATE SEQUENCE public.prescription_items_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.prescription_items_id_seq OWNER TO sante;

--
-- Name: prescription_items_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: sante
--

ALTER SEQUENCE public.prescription_items_id_seq OWNED BY public.prescription_items.id;


--
-- Name: prescriptions; Type: TABLE; Schema: public; Owner: sante
--

CREATE TABLE public.prescriptions (
    id integer NOT NULL,
    clinic_id integer NOT NULL,
    consultation_id integer NOT NULL,
    patient_id integer NOT NULL,
    prescriber_doctor_id integer NOT NULL,
    status character varying(32) NOT NULL,
    notes text,
    deleted_at timestamp without time zone,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL
);


ALTER TABLE public.prescriptions OWNER TO sante;

--
-- Name: prescriptions_id_seq; Type: SEQUENCE; Schema: public; Owner: sante
--

CREATE SEQUENCE public.prescriptions_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.prescriptions_id_seq OWNER TO sante;

--
-- Name: prescriptions_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: sante
--

ALTER SEQUENCE public.prescriptions_id_seq OWNED BY public.prescriptions.id;


--
-- Name: reminder_events; Type: TABLE; Schema: public; Owner: sante
--

CREATE TABLE public.reminder_events (
    id integer NOT NULL,
    reminder_id integer NOT NULL,
    event_type character varying(32) NOT NULL,
    payload text,
    created_at timestamp without time zone NOT NULL
);


ALTER TABLE public.reminder_events OWNER TO sante;

--
-- Name: reminder_events_id_seq; Type: SEQUENCE; Schema: public; Owner: sante
--

CREATE SEQUENCE public.reminder_events_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.reminder_events_id_seq OWNER TO sante;

--
-- Name: reminder_events_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: sante
--

ALTER SEQUENCE public.reminder_events_id_seq OWNED BY public.reminder_events.id;


--
-- Name: rendezvous; Type: TABLE; Schema: public; Owner: sante
--

CREATE TABLE public.rendezvous (
    id integer NOT NULL,
    date timestamp without time zone NOT NULL,
    duration_minutes integer NOT NULL,
    status character varying NOT NULL,
    payment_status character varying NOT NULL,
    price double precision NOT NULL,
    payment_intent_id character varying,
    consultation_type character varying NOT NULL,
    meeting_link character varying,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    doctor_id integer NOT NULL,
    patient_id integer NOT NULL,
    clinic_id integer NOT NULL,
    clinical_status character varying(32) NOT NULL
);


ALTER TABLE public.rendezvous OWNER TO sante;

--
-- Name: rendezvous_id_seq; Type: SEQUENCE; Schema: public; Owner: sante
--

CREATE SEQUENCE public.rendezvous_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.rendezvous_id_seq OWNER TO sante;

--
-- Name: rendezvous_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: sante
--

ALTER SEQUENCE public.rendezvous_id_seq OWNED BY public.rendezvous.id;


--
-- Name: sync_conflicts; Type: TABLE; Schema: public; Owner: sante
--

CREATE TABLE public.sync_conflicts (
    id integer NOT NULL,
    clinic_id integer NOT NULL,
    entity_type character varying(64) NOT NULL,
    entity_uid character varying(64),
    local_json text NOT NULL,
    remote_json text NOT NULL,
    status character varying(32) NOT NULL,
    created_at timestamp without time zone NOT NULL,
    resolved_at timestamp without time zone,
    resolution_note text
);


ALTER TABLE public.sync_conflicts OWNER TO sante;

--
-- Name: sync_conflicts_id_seq; Type: SEQUENCE; Schema: public; Owner: sante
--

CREATE SEQUENCE public.sync_conflicts_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.sync_conflicts_id_seq OWNER TO sante;

--
-- Name: sync_conflicts_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: sante
--

ALTER SEQUENCE public.sync_conflicts_id_seq OWNED BY public.sync_conflicts.id;


--
-- Name: sync_outbox_events; Type: TABLE; Schema: public; Owner: sante
--

CREATE TABLE public.sync_outbox_events (
    id integer NOT NULL,
    event_id character varying(64) NOT NULL,
    clinic_id integer NOT NULL,
    node_id character varying(64),
    entity_type character varying(64) NOT NULL,
    entity_uid character varying(64),
    operation character varying(32) NOT NULL,
    payload_json text NOT NULL,
    created_at timestamp without time zone NOT NULL,
    acked_at timestamp without time zone,
    ack_error text
);


ALTER TABLE public.sync_outbox_events OWNER TO sante;

--
-- Name: sync_outbox_events_id_seq; Type: SEQUENCE; Schema: public; Owner: sante
--

CREATE SEQUENCE public.sync_outbox_events_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.sync_outbox_events_id_seq OWNER TO sante;

--
-- Name: sync_outbox_events_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: sante
--

ALTER SEQUENCE public.sync_outbox_events_id_seq OWNED BY public.sync_outbox_events.id;


--
-- Name: users; Type: TABLE; Schema: public; Owner: sante
--

CREATE TABLE public.users (
    id integer NOT NULL,
    email character varying NOT NULL,
    hashed_password character varying NOT NULL,
    role character varying NOT NULL,
    clinic_id integer,
    is_active boolean NOT NULL,
    must_change_password boolean NOT NULL,
    email_verified_at timestamp without time zone,
    CONSTRAINT ck_users_role_allowed CHECK (((role)::text = ANY ((ARRAY['patient'::character varying, 'doctor'::character varying, 'platform_owner'::character varying, 'platform_admin'::character varying, 'clinic_admin'::character varying, 'admin'::character varying, 'receptionist'::character varying, 'cashier'::character varying, 'lab_technician'::character varying, 'pharmacist'::character varying, 'nutritionist'::character varying, 'midwife'::character varying, 'pev_agent'::character varying, 'nurse'::character varying])::text[])))
);


ALTER TABLE public.users OWNER TO sante;

--
-- Name: users_id_seq; Type: SEQUENCE; Schema: public; Owner: sante
--

CREATE SEQUENCE public.users_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.users_id_seq OWNER TO sante;

--
-- Name: users_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: sante
--

ALTER SEQUENCE public.users_id_seq OWNED BY public.users.id;


--
-- Name: vaccine_schedule_items; Type: TABLE; Schema: public; Owner: sante
--

CREATE TABLE public.vaccine_schedule_items (
    id integer NOT NULL,
    vaccine_code character varying(32) NOT NULL,
    vaccine_name character varying(128) NOT NULL,
    dose_label character varying(64) NOT NULL,
    age_months integer NOT NULL,
    grace_days integer NOT NULL,
    is_active boolean NOT NULL
);


ALTER TABLE public.vaccine_schedule_items OWNER TO sante;

--
-- Name: vaccine_schedule_items_id_seq; Type: SEQUENCE; Schema: public; Owner: sante
--

CREATE SEQUENCE public.vaccine_schedule_items_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.vaccine_schedule_items_id_seq OWNER TO sante;

--
-- Name: vaccine_schedule_items_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: sante
--

ALTER SEQUENCE public.vaccine_schedule_items_id_seq OWNED BY public.vaccine_schedule_items.id;


--
-- Name: admissions id; Type: DEFAULT; Schema: public; Owner: sante
--

ALTER TABLE ONLY public.admissions ALTER COLUMN id SET DEFAULT nextval('public.admissions_id_seq'::regclass);


--
-- Name: appointment_reminders id; Type: DEFAULT; Schema: public; Owner: sante
--

ALTER TABLE ONLY public.appointment_reminders ALTER COLUMN id SET DEFAULT nextval('public.appointment_reminders_id_seq'::regclass);


--
-- Name: attachment_access_logs id; Type: DEFAULT; Schema: public; Owner: sante
--

ALTER TABLE ONLY public.attachment_access_logs ALTER COLUMN id SET DEFAULT nextval('public.attachment_access_logs_id_seq'::regclass);


--
-- Name: clinic_charge_payments id; Type: DEFAULT; Schema: public; Owner: sante
--

ALTER TABLE ONLY public.clinic_charge_payments ALTER COLUMN id SET DEFAULT nextval('public.clinic_charge_payments_id_seq'::regclass);


--
-- Name: clinic_charges id; Type: DEFAULT; Schema: public; Owner: sante
--

ALTER TABLE ONLY public.clinic_charges ALTER COLUMN id SET DEFAULT nextval('public.clinic_charges_id_seq'::regclass);


--
-- Name: clinic_lab_tests id; Type: DEFAULT; Schema: public; Owner: sante
--

ALTER TABLE ONLY public.clinic_lab_tests ALTER COLUMN id SET DEFAULT nextval('public.clinic_lab_tests_id_seq'::regclass);


--
-- Name: clinic_node_heartbeats id; Type: DEFAULT; Schema: public; Owner: sante
--

ALTER TABLE ONLY public.clinic_node_heartbeats ALTER COLUMN id SET DEFAULT nextval('public.clinic_node_heartbeats_id_seq'::regclass);


--
-- Name: clinic_node_licenses id; Type: DEFAULT; Schema: public; Owner: sante
--

ALTER TABLE ONLY public.clinic_node_licenses ALTER COLUMN id SET DEFAULT nextval('public.clinic_node_licenses_id_seq'::regclass);


--
-- Name: clinic_refunds id; Type: DEFAULT; Schema: public; Owner: sante
--

ALTER TABLE ONLY public.clinic_refunds ALTER COLUMN id SET DEFAULT nextval('public.clinic_refunds_id_seq'::regclass);


--
-- Name: clinic_service_requests id; Type: DEFAULT; Schema: public; Owner: sante
--

ALTER TABLE ONLY public.clinic_service_requests ALTER COLUMN id SET DEFAULT nextval('public.clinic_service_requests_id_seq'::regclass);


--
-- Name: clinic_staff id; Type: DEFAULT; Schema: public; Owner: sante
--

ALTER TABLE ONLY public.clinic_staff ALTER COLUMN id SET DEFAULT nextval('public.clinic_staff_id_seq'::regclass);


--
-- Name: clinical_audit_logs id; Type: DEFAULT; Schema: public; Owner: sante
--

ALTER TABLE ONLY public.clinical_audit_logs ALTER COLUMN id SET DEFAULT nextval('public.clinical_audit_logs_id_seq'::regclass);


--
-- Name: clinical_notes id; Type: DEFAULT; Schema: public; Owner: sante
--

ALTER TABLE ONLY public.clinical_notes ALTER COLUMN id SET DEFAULT nextval('public.clinical_notes_id_seq'::regclass);


--
-- Name: clinical_visits id; Type: DEFAULT; Schema: public; Owner: sante
--

ALTER TABLE ONLY public.clinical_visits ALTER COLUMN id SET DEFAULT nextval('public.clinical_visits_id_seq'::regclass);


--
-- Name: clinics id; Type: DEFAULT; Schema: public; Owner: sante
--

ALTER TABLE ONLY public.clinics ALTER COLUMN id SET DEFAULT nextval('public.clinics_id_seq'::regclass);


--
-- Name: consultation_summaries id; Type: DEFAULT; Schema: public; Owner: sante
--

ALTER TABLE ONLY public.consultation_summaries ALTER COLUMN id SET DEFAULT nextval('public.consultation_summaries_id_seq'::regclass);


--
-- Name: consultations id; Type: DEFAULT; Schema: public; Owner: sante
--

ALTER TABLE ONLY public.consultations ALTER COLUMN id SET DEFAULT nextval('public.consultations_id_seq'::regclass);


--
-- Name: discharge_summaries id; Type: DEFAULT; Schema: public; Owner: sante
--

ALTER TABLE ONLY public.discharge_summaries ALTER COLUMN id SET DEFAULT nextval('public.discharge_summaries_id_seq'::regclass);


--
-- Name: doctor_availabilities id; Type: DEFAULT; Schema: public; Owner: sante
--

ALTER TABLE ONLY public.doctor_availabilities ALTER COLUMN id SET DEFAULT nextval('public.doctor_availabilities_id_seq'::regclass);


--
-- Name: doctor_medicine_deliveries id; Type: DEFAULT; Schema: public; Owner: sante
--

ALTER TABLE ONLY public.doctor_medicine_deliveries ALTER COLUMN id SET DEFAULT nextval('public.doctor_medicine_deliveries_id_seq'::regclass);


--
-- Name: doctors id; Type: DEFAULT; Schema: public; Owner: sante
--

ALTER TABLE ONLY public.doctors ALTER COLUMN id SET DEFAULT nextval('public.doctors_id_seq'::regclass);


--
-- Name: email_verification_tokens id; Type: DEFAULT; Schema: public; Owner: sante
--

ALTER TABLE ONLY public.email_verification_tokens ALTER COLUMN id SET DEFAULT nextval('public.email_verification_tokens_id_seq'::regclass);


--
-- Name: follow_up_schedules id; Type: DEFAULT; Schema: public; Owner: sante
--

ALTER TABLE ONLY public.follow_up_schedules ALTER COLUMN id SET DEFAULT nextval('public.follow_up_schedules_id_seq'::regclass);


--
-- Name: hospital_beds id; Type: DEFAULT; Schema: public; Owner: sante
--

ALTER TABLE ONLY public.hospital_beds ALTER COLUMN id SET DEFAULT nextval('public.hospital_beds_id_seq'::regclass);


--
-- Name: hospital_rooms id; Type: DEFAULT; Schema: public; Owner: sante
--

ALTER TABLE ONLY public.hospital_rooms ALTER COLUMN id SET DEFAULT nextval('public.hospital_rooms_id_seq'::regclass);


--
-- Name: imaging_orders id; Type: DEFAULT; Schema: public; Owner: sante
--

ALTER TABLE ONLY public.imaging_orders ALTER COLUMN id SET DEFAULT nextval('public.imaging_orders_id_seq'::regclass);


--
-- Name: imaging_results id; Type: DEFAULT; Schema: public; Owner: sante
--

ALTER TABLE ONLY public.imaging_results ALTER COLUMN id SET DEFAULT nextval('public.imaging_results_id_seq'::regclass);


--
-- Name: immunization_records id; Type: DEFAULT; Schema: public; Owner: sante
--

ALTER TABLE ONLY public.immunization_records ALTER COLUMN id SET DEFAULT nextval('public.immunization_records_id_seq'::regclass);


--
-- Name: invoice_items id; Type: DEFAULT; Schema: public; Owner: sante
--

ALTER TABLE ONLY public.invoice_items ALTER COLUMN id SET DEFAULT nextval('public.invoice_items_id_seq'::regclass);


--
-- Name: invoices id; Type: DEFAULT; Schema: public; Owner: sante
--

ALTER TABLE ONLY public.invoices ALTER COLUMN id SET DEFAULT nextval('public.invoices_id_seq'::regclass);


--
-- Name: lab_orders id; Type: DEFAULT; Schema: public; Owner: sante
--

ALTER TABLE ONLY public.lab_orders ALTER COLUMN id SET DEFAULT nextval('public.lab_orders_id_seq'::regclass);


--
-- Name: lab_results id; Type: DEFAULT; Schema: public; Owner: sante
--

ALTER TABLE ONLY public.lab_results ALTER COLUMN id SET DEFAULT nextval('public.lab_results_id_seq'::regclass);


--
-- Name: messages id; Type: DEFAULT; Schema: public; Owner: sante
--

ALTER TABLE ONLY public.messages ALTER COLUMN id SET DEFAULT nextval('public.messages_id_seq'::regclass);


--
-- Name: notification_events id; Type: DEFAULT; Schema: public; Owner: sante
--

ALTER TABLE ONLY public.notification_events ALTER COLUMN id SET DEFAULT nextval('public.notification_events_id_seq'::regclass);


--
-- Name: nurse_assessments id; Type: DEFAULT; Schema: public; Owner: sante
--

ALTER TABLE ONLY public.nurse_assessments ALTER COLUMN id SET DEFAULT nextval('public.nurse_assessments_id_seq'::regclass);


--
-- Name: nursing_procedures id; Type: DEFAULT; Schema: public; Owner: sante
--

ALTER TABLE ONLY public.nursing_procedures ALTER COLUMN id SET DEFAULT nextval('public.nursing_procedures_id_seq'::regclass);


--
-- Name: nutrition_assessments id; Type: DEFAULT; Schema: public; Owner: sante
--

ALTER TABLE ONLY public.nutrition_assessments ALTER COLUMN id SET DEFAULT nextval('public.nutrition_assessments_id_seq'::regclass);


--
-- Name: password_reset_tokens id; Type: DEFAULT; Schema: public; Owner: sante
--

ALTER TABLE ONLY public.password_reset_tokens ALTER COLUMN id SET DEFAULT nextval('public.password_reset_tokens_id_seq'::regclass);


--
-- Name: patient_allergies id; Type: DEFAULT; Schema: public; Owner: sante
--

ALTER TABLE ONLY public.patient_allergies ALTER COLUMN id SET DEFAULT nextval('public.patient_allergies_id_seq'::regclass);


--
-- Name: patient_chronic_conditions id; Type: DEFAULT; Schema: public; Owner: sante
--

ALTER TABLE ONLY public.patient_chronic_conditions ALTER COLUMN id SET DEFAULT nextval('public.patient_chronic_conditions_id_seq'::regclass);


--
-- Name: patient_documents id; Type: DEFAULT; Schema: public; Owner: sante
--

ALTER TABLE ONLY public.patient_documents ALTER COLUMN id SET DEFAULT nextval('public.patient_documents_id_seq'::regclass);


--
-- Name: patient_medical_records id; Type: DEFAULT; Schema: public; Owner: sante
--

ALTER TABLE ONLY public.patient_medical_records ALTER COLUMN id SET DEFAULT nextval('public.patient_medical_records_id_seq'::regclass);


--
-- Name: patient_stays id; Type: DEFAULT; Schema: public; Owner: sante
--

ALTER TABLE ONLY public.patient_stays ALTER COLUMN id SET DEFAULT nextval('public.patient_stays_id_seq'::regclass);


--
-- Name: patient_visit_workflow_steps id; Type: DEFAULT; Schema: public; Owner: sante
--

ALTER TABLE ONLY public.patient_visit_workflow_steps ALTER COLUMN id SET DEFAULT nextval('public.patient_visit_workflow_steps_id_seq'::regclass);


--
-- Name: patient_visit_workflows id; Type: DEFAULT; Schema: public; Owner: sante
--

ALTER TABLE ONLY public.patient_visit_workflows ALTER COLUMN id SET DEFAULT nextval('public.patient_visit_workflows_id_seq'::regclass);


--
-- Name: patient_vital_signs id; Type: DEFAULT; Schema: public; Owner: sante
--

ALTER TABLE ONLY public.patient_vital_signs ALTER COLUMN id SET DEFAULT nextval('public.patient_vital_signs_id_seq'::regclass);


--
-- Name: patients id; Type: DEFAULT; Schema: public; Owner: sante
--

ALTER TABLE ONLY public.patients ALTER COLUMN id SET DEFAULT nextval('public.patients_id_seq'::regclass);


--
-- Name: payment_records id; Type: DEFAULT; Schema: public; Owner: sante
--

ALTER TABLE ONLY public.payment_records ALTER COLUMN id SET DEFAULT nextval('public.payment_records_id_seq'::regclass);


--
-- Name: payments id; Type: DEFAULT; Schema: public; Owner: sante
--

ALTER TABLE ONLY public.payments ALTER COLUMN id SET DEFAULT nextval('public.payments_id_seq'::regclass);


--
-- Name: pharmacy_inventory id; Type: DEFAULT; Schema: public; Owner: sante
--

ALTER TABLE ONLY public.pharmacy_inventory ALTER COLUMN id SET DEFAULT nextval('public.pharmacy_inventory_id_seq'::regclass);


--
-- Name: pharmacy_orders id; Type: DEFAULT; Schema: public; Owner: sante
--

ALTER TABLE ONLY public.pharmacy_orders ALTER COLUMN id SET DEFAULT nextval('public.pharmacy_orders_id_seq'::regclass);


--
-- Name: prescription_items id; Type: DEFAULT; Schema: public; Owner: sante
--

ALTER TABLE ONLY public.prescription_items ALTER COLUMN id SET DEFAULT nextval('public.prescription_items_id_seq'::regclass);


--
-- Name: prescriptions id; Type: DEFAULT; Schema: public; Owner: sante
--

ALTER TABLE ONLY public.prescriptions ALTER COLUMN id SET DEFAULT nextval('public.prescriptions_id_seq'::regclass);


--
-- Name: reminder_events id; Type: DEFAULT; Schema: public; Owner: sante
--

ALTER TABLE ONLY public.reminder_events ALTER COLUMN id SET DEFAULT nextval('public.reminder_events_id_seq'::regclass);


--
-- Name: rendezvous id; Type: DEFAULT; Schema: public; Owner: sante
--

ALTER TABLE ONLY public.rendezvous ALTER COLUMN id SET DEFAULT nextval('public.rendezvous_id_seq'::regclass);


--
-- Name: sync_conflicts id; Type: DEFAULT; Schema: public; Owner: sante
--

ALTER TABLE ONLY public.sync_conflicts ALTER COLUMN id SET DEFAULT nextval('public.sync_conflicts_id_seq'::regclass);


--
-- Name: sync_outbox_events id; Type: DEFAULT; Schema: public; Owner: sante
--

ALTER TABLE ONLY public.sync_outbox_events ALTER COLUMN id SET DEFAULT nextval('public.sync_outbox_events_id_seq'::regclass);


--
-- Name: users id; Type: DEFAULT; Schema: public; Owner: sante
--

ALTER TABLE ONLY public.users ALTER COLUMN id SET DEFAULT nextval('public.users_id_seq'::regclass);


--
-- Name: vaccine_schedule_items id; Type: DEFAULT; Schema: public; Owner: sante
--

ALTER TABLE ONLY public.vaccine_schedule_items ALTER COLUMN id SET DEFAULT nextval('public.vaccine_schedule_items_id_seq'::regclass);


--
-- Name: admissions admissions_pkey; Type: CONSTRAINT; Schema: public; Owner: sante
--

ALTER TABLE ONLY public.admissions
    ADD CONSTRAINT admissions_pkey PRIMARY KEY (id);


--
-- Name: appointment_reminders appointment_reminders_pkey; Type: CONSTRAINT; Schema: public; Owner: sante
--

ALTER TABLE ONLY public.appointment_reminders
    ADD CONSTRAINT appointment_reminders_pkey PRIMARY KEY (id);


--
-- Name: attachment_access_logs attachment_access_logs_pkey; Type: CONSTRAINT; Schema: public; Owner: sante
--

ALTER TABLE ONLY public.attachment_access_logs
    ADD CONSTRAINT attachment_access_logs_pkey PRIMARY KEY (id);


--
-- Name: clinic_charge_payments clinic_charge_payments_pkey; Type: CONSTRAINT; Schema: public; Owner: sante
--

ALTER TABLE ONLY public.clinic_charge_payments
    ADD CONSTRAINT clinic_charge_payments_pkey PRIMARY KEY (id);


--
-- Name: clinic_charges clinic_charges_pkey; Type: CONSTRAINT; Schema: public; Owner: sante
--

ALTER TABLE ONLY public.clinic_charges
    ADD CONSTRAINT clinic_charges_pkey PRIMARY KEY (id);


--
-- Name: clinic_lab_tests clinic_lab_tests_pkey; Type: CONSTRAINT; Schema: public; Owner: sante
--

ALTER TABLE ONLY public.clinic_lab_tests
    ADD CONSTRAINT clinic_lab_tests_pkey PRIMARY KEY (id);


--
-- Name: clinic_node_heartbeats clinic_node_heartbeats_pkey; Type: CONSTRAINT; Schema: public; Owner: sante
--

ALTER TABLE ONLY public.clinic_node_heartbeats
    ADD CONSTRAINT clinic_node_heartbeats_pkey PRIMARY KEY (id);


--
-- Name: clinic_node_licenses clinic_node_licenses_pkey; Type: CONSTRAINT; Schema: public; Owner: sante
--

ALTER TABLE ONLY public.clinic_node_licenses
    ADD CONSTRAINT clinic_node_licenses_pkey PRIMARY KEY (id);


--
-- Name: clinic_refunds clinic_refunds_pkey; Type: CONSTRAINT; Schema: public; Owner: sante
--

ALTER TABLE ONLY public.clinic_refunds
    ADD CONSTRAINT clinic_refunds_pkey PRIMARY KEY (id);


--
-- Name: clinic_service_requests clinic_service_requests_pkey; Type: CONSTRAINT; Schema: public; Owner: sante
--

ALTER TABLE ONLY public.clinic_service_requests
    ADD CONSTRAINT clinic_service_requests_pkey PRIMARY KEY (id);


--
-- Name: clinic_staff clinic_staff_pkey; Type: CONSTRAINT; Schema: public; Owner: sante
--

ALTER TABLE ONLY public.clinic_staff
    ADD CONSTRAINT clinic_staff_pkey PRIMARY KEY (id);


--
-- Name: clinical_audit_logs clinical_audit_logs_pkey; Type: CONSTRAINT; Schema: public; Owner: sante
--

ALTER TABLE ONLY public.clinical_audit_logs
    ADD CONSTRAINT clinical_audit_logs_pkey PRIMARY KEY (id);


--
-- Name: clinical_notes clinical_notes_pkey; Type: CONSTRAINT; Schema: public; Owner: sante
--

ALTER TABLE ONLY public.clinical_notes
    ADD CONSTRAINT clinical_notes_pkey PRIMARY KEY (id);


--
-- Name: clinical_visits clinical_visits_pkey; Type: CONSTRAINT; Schema: public; Owner: sante
--

ALTER TABLE ONLY public.clinical_visits
    ADD CONSTRAINT clinical_visits_pkey PRIMARY KEY (id);


--
-- Name: clinics clinics_pkey; Type: CONSTRAINT; Schema: public; Owner: sante
--

ALTER TABLE ONLY public.clinics
    ADD CONSTRAINT clinics_pkey PRIMARY KEY (id);


--
-- Name: consultation_summaries consultation_summaries_pkey; Type: CONSTRAINT; Schema: public; Owner: sante
--

ALTER TABLE ONLY public.consultation_summaries
    ADD CONSTRAINT consultation_summaries_pkey PRIMARY KEY (id);


--
-- Name: consultations consultations_pkey; Type: CONSTRAINT; Schema: public; Owner: sante
--

ALTER TABLE ONLY public.consultations
    ADD CONSTRAINT consultations_pkey PRIMARY KEY (id);


--
-- Name: discharge_summaries discharge_summaries_pkey; Type: CONSTRAINT; Schema: public; Owner: sante
--

ALTER TABLE ONLY public.discharge_summaries
    ADD CONSTRAINT discharge_summaries_pkey PRIMARY KEY (id);


--
-- Name: doctor_availabilities doctor_availabilities_pkey; Type: CONSTRAINT; Schema: public; Owner: sante
--

ALTER TABLE ONLY public.doctor_availabilities
    ADD CONSTRAINT doctor_availabilities_pkey PRIMARY KEY (id);


--
-- Name: doctor_medicine_deliveries doctor_medicine_deliveries_pkey; Type: CONSTRAINT; Schema: public; Owner: sante
--

ALTER TABLE ONLY public.doctor_medicine_deliveries
    ADD CONSTRAINT doctor_medicine_deliveries_pkey PRIMARY KEY (id);


--
-- Name: doctors doctors_pkey; Type: CONSTRAINT; Schema: public; Owner: sante
--

ALTER TABLE ONLY public.doctors
    ADD CONSTRAINT doctors_pkey PRIMARY KEY (id);


--
-- Name: email_verification_tokens email_verification_tokens_pkey; Type: CONSTRAINT; Schema: public; Owner: sante
--

ALTER TABLE ONLY public.email_verification_tokens
    ADD CONSTRAINT email_verification_tokens_pkey PRIMARY KEY (id);


--
-- Name: follow_up_schedules follow_up_schedules_pkey; Type: CONSTRAINT; Schema: public; Owner: sante
--

ALTER TABLE ONLY public.follow_up_schedules
    ADD CONSTRAINT follow_up_schedules_pkey PRIMARY KEY (id);


--
-- Name: hospital_beds hospital_beds_pkey; Type: CONSTRAINT; Schema: public; Owner: sante
--

ALTER TABLE ONLY public.hospital_beds
    ADD CONSTRAINT hospital_beds_pkey PRIMARY KEY (id);


--
-- Name: hospital_rooms hospital_rooms_pkey; Type: CONSTRAINT; Schema: public; Owner: sante
--

ALTER TABLE ONLY public.hospital_rooms
    ADD CONSTRAINT hospital_rooms_pkey PRIMARY KEY (id);


--
-- Name: imaging_orders imaging_orders_pkey; Type: CONSTRAINT; Schema: public; Owner: sante
--

ALTER TABLE ONLY public.imaging_orders
    ADD CONSTRAINT imaging_orders_pkey PRIMARY KEY (id);


--
-- Name: imaging_results imaging_results_pkey; Type: CONSTRAINT; Schema: public; Owner: sante
--

ALTER TABLE ONLY public.imaging_results
    ADD CONSTRAINT imaging_results_pkey PRIMARY KEY (id);


--
-- Name: immunization_records immunization_records_pkey; Type: CONSTRAINT; Schema: public; Owner: sante
--

ALTER TABLE ONLY public.immunization_records
    ADD CONSTRAINT immunization_records_pkey PRIMARY KEY (id);


--
-- Name: invoice_items invoice_items_pkey; Type: CONSTRAINT; Schema: public; Owner: sante
--

ALTER TABLE ONLY public.invoice_items
    ADD CONSTRAINT invoice_items_pkey PRIMARY KEY (id);


--
-- Name: invoices invoices_pkey; Type: CONSTRAINT; Schema: public; Owner: sante
--

ALTER TABLE ONLY public.invoices
    ADD CONSTRAINT invoices_pkey PRIMARY KEY (id);


--
-- Name: lab_orders lab_orders_pkey; Type: CONSTRAINT; Schema: public; Owner: sante
--

ALTER TABLE ONLY public.lab_orders
    ADD CONSTRAINT lab_orders_pkey PRIMARY KEY (id);


--
-- Name: lab_results lab_results_pkey; Type: CONSTRAINT; Schema: public; Owner: sante
--

ALTER TABLE ONLY public.lab_results
    ADD CONSTRAINT lab_results_pkey PRIMARY KEY (id);


--
-- Name: messages messages_pkey; Type: CONSTRAINT; Schema: public; Owner: sante
--

ALTER TABLE ONLY public.messages
    ADD CONSTRAINT messages_pkey PRIMARY KEY (id);


--
-- Name: notification_events notification_events_pkey; Type: CONSTRAINT; Schema: public; Owner: sante
--

ALTER TABLE ONLY public.notification_events
    ADD CONSTRAINT notification_events_pkey PRIMARY KEY (id);


--
-- Name: nurse_assessments nurse_assessments_pkey; Type: CONSTRAINT; Schema: public; Owner: sante
--

ALTER TABLE ONLY public.nurse_assessments
    ADD CONSTRAINT nurse_assessments_pkey PRIMARY KEY (id);


--
-- Name: nursing_procedures nursing_procedures_pkey; Type: CONSTRAINT; Schema: public; Owner: sante
--

ALTER TABLE ONLY public.nursing_procedures
    ADD CONSTRAINT nursing_procedures_pkey PRIMARY KEY (id);


--
-- Name: nutrition_assessments nutrition_assessments_pkey; Type: CONSTRAINT; Schema: public; Owner: sante
--

ALTER TABLE ONLY public.nutrition_assessments
    ADD CONSTRAINT nutrition_assessments_pkey PRIMARY KEY (id);


--
-- Name: password_reset_tokens password_reset_tokens_pkey; Type: CONSTRAINT; Schema: public; Owner: sante
--

ALTER TABLE ONLY public.password_reset_tokens
    ADD CONSTRAINT password_reset_tokens_pkey PRIMARY KEY (id);


--
-- Name: patient_allergies patient_allergies_pkey; Type: CONSTRAINT; Schema: public; Owner: sante
--

ALTER TABLE ONLY public.patient_allergies
    ADD CONSTRAINT patient_allergies_pkey PRIMARY KEY (id);


--
-- Name: patient_chronic_conditions patient_chronic_conditions_pkey; Type: CONSTRAINT; Schema: public; Owner: sante
--

ALTER TABLE ONLY public.patient_chronic_conditions
    ADD CONSTRAINT patient_chronic_conditions_pkey PRIMARY KEY (id);


--
-- Name: patient_documents patient_documents_pkey; Type: CONSTRAINT; Schema: public; Owner: sante
--

ALTER TABLE ONLY public.patient_documents
    ADD CONSTRAINT patient_documents_pkey PRIMARY KEY (id);


--
-- Name: patient_medical_records patient_medical_records_pkey; Type: CONSTRAINT; Schema: public; Owner: sante
--

ALTER TABLE ONLY public.patient_medical_records
    ADD CONSTRAINT patient_medical_records_pkey PRIMARY KEY (id);


--
-- Name: patient_stays patient_stays_pkey; Type: CONSTRAINT; Schema: public; Owner: sante
--

ALTER TABLE ONLY public.patient_stays
    ADD CONSTRAINT patient_stays_pkey PRIMARY KEY (id);


--
-- Name: patient_visit_workflow_steps patient_visit_workflow_steps_pkey; Type: CONSTRAINT; Schema: public; Owner: sante
--

ALTER TABLE ONLY public.patient_visit_workflow_steps
    ADD CONSTRAINT patient_visit_workflow_steps_pkey PRIMARY KEY (id);


--
-- Name: patient_visit_workflows patient_visit_workflows_pkey; Type: CONSTRAINT; Schema: public; Owner: sante
--

ALTER TABLE ONLY public.patient_visit_workflows
    ADD CONSTRAINT patient_visit_workflows_pkey PRIMARY KEY (id);


--
-- Name: patient_vital_signs patient_vital_signs_pkey; Type: CONSTRAINT; Schema: public; Owner: sante
--

ALTER TABLE ONLY public.patient_vital_signs
    ADD CONSTRAINT patient_vital_signs_pkey PRIMARY KEY (id);


--
-- Name: patients patients_pkey; Type: CONSTRAINT; Schema: public; Owner: sante
--

ALTER TABLE ONLY public.patients
    ADD CONSTRAINT patients_pkey PRIMARY KEY (id);


--
-- Name: payment_records payment_records_pkey; Type: CONSTRAINT; Schema: public; Owner: sante
--

ALTER TABLE ONLY public.payment_records
    ADD CONSTRAINT payment_records_pkey PRIMARY KEY (id);


--
-- Name: payments payments_pkey; Type: CONSTRAINT; Schema: public; Owner: sante
--

ALTER TABLE ONLY public.payments
    ADD CONSTRAINT payments_pkey PRIMARY KEY (id);


--
-- Name: pharmacy_inventory pharmacy_inventory_pkey; Type: CONSTRAINT; Schema: public; Owner: sante
--

ALTER TABLE ONLY public.pharmacy_inventory
    ADD CONSTRAINT pharmacy_inventory_pkey PRIMARY KEY (id);


--
-- Name: pharmacy_orders pharmacy_orders_pkey; Type: CONSTRAINT; Schema: public; Owner: sante
--

ALTER TABLE ONLY public.pharmacy_orders
    ADD CONSTRAINT pharmacy_orders_pkey PRIMARY KEY (id);


--
-- Name: prescription_items prescription_items_pkey; Type: CONSTRAINT; Schema: public; Owner: sante
--

ALTER TABLE ONLY public.prescription_items
    ADD CONSTRAINT prescription_items_pkey PRIMARY KEY (id);


--
-- Name: prescriptions prescriptions_pkey; Type: CONSTRAINT; Schema: public; Owner: sante
--

ALTER TABLE ONLY public.prescriptions
    ADD CONSTRAINT prescriptions_pkey PRIMARY KEY (id);


--
-- Name: reminder_events reminder_events_pkey; Type: CONSTRAINT; Schema: public; Owner: sante
--

ALTER TABLE ONLY public.reminder_events
    ADD CONSTRAINT reminder_events_pkey PRIMARY KEY (id);


--
-- Name: rendezvous rendezvous_pkey; Type: CONSTRAINT; Schema: public; Owner: sante
--

ALTER TABLE ONLY public.rendezvous
    ADD CONSTRAINT rendezvous_pkey PRIMARY KEY (id);


--
-- Name: sync_conflicts sync_conflicts_pkey; Type: CONSTRAINT; Schema: public; Owner: sante
--

ALTER TABLE ONLY public.sync_conflicts
    ADD CONSTRAINT sync_conflicts_pkey PRIMARY KEY (id);


--
-- Name: sync_outbox_events sync_outbox_events_pkey; Type: CONSTRAINT; Schema: public; Owner: sante
--

ALTER TABLE ONLY public.sync_outbox_events
    ADD CONSTRAINT sync_outbox_events_pkey PRIMARY KEY (id);


--
-- Name: clinic_lab_tests uq_clinic_lab_tests_clinic_code; Type: CONSTRAINT; Schema: public; Owner: sante
--

ALTER TABLE ONLY public.clinic_lab_tests
    ADD CONSTRAINT uq_clinic_lab_tests_clinic_code UNIQUE (clinic_id, code);


--
-- Name: patients uq_patients_clinic_user; Type: CONSTRAINT; Schema: public; Owner: sante
--

ALTER TABLE ONLY public.patients
    ADD CONSTRAINT uq_patients_clinic_user UNIQUE (clinic_id, user_id);


--
-- Name: sync_outbox_events uq_sync_outbox_event_id; Type: CONSTRAINT; Schema: public; Owner: sante
--

ALTER TABLE ONLY public.sync_outbox_events
    ADD CONSTRAINT uq_sync_outbox_event_id UNIQUE (event_id);


--
-- Name: users users_pkey; Type: CONSTRAINT; Schema: public; Owner: sante
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_pkey PRIMARY KEY (id);


--
-- Name: vaccine_schedule_items vaccine_schedule_items_pkey; Type: CONSTRAINT; Schema: public; Owner: sante
--

ALTER TABLE ONLY public.vaccine_schedule_items
    ADD CONSTRAINT vaccine_schedule_items_pkey PRIMARY KEY (id);


--
-- Name: ix_admissions_admission_number; Type: INDEX; Schema: public; Owner: sante
--

CREATE UNIQUE INDEX ix_admissions_admission_number ON public.admissions USING btree (admission_number);


--
-- Name: ix_admissions_admission_type; Type: INDEX; Schema: public; Owner: sante
--

CREATE INDEX ix_admissions_admission_type ON public.admissions USING btree (admission_type);


--
-- Name: ix_admissions_clinic_id; Type: INDEX; Schema: public; Owner: sante
--

CREATE INDEX ix_admissions_clinic_id ON public.admissions USING btree (clinic_id);


--
-- Name: ix_admissions_consultation_id; Type: INDEX; Schema: public; Owner: sante
--

CREATE INDEX ix_admissions_consultation_id ON public.admissions USING btree (consultation_id);


--
-- Name: ix_admissions_department; Type: INDEX; Schema: public; Owner: sante
--

CREATE INDEX ix_admissions_department ON public.admissions USING btree (department);


--
-- Name: ix_admissions_id; Type: INDEX; Schema: public; Owner: sante
--

CREATE INDEX ix_admissions_id ON public.admissions USING btree (id);


--
-- Name: ix_admissions_patient_id; Type: INDEX; Schema: public; Owner: sante
--

CREATE INDEX ix_admissions_patient_id ON public.admissions USING btree (patient_id);


--
-- Name: ix_admissions_status; Type: INDEX; Schema: public; Owner: sante
--

CREATE INDEX ix_admissions_status ON public.admissions USING btree (status);


--
-- Name: ix_appointment_reminders_appointment_id; Type: INDEX; Schema: public; Owner: sante
--

CREATE INDEX ix_appointment_reminders_appointment_id ON public.appointment_reminders USING btree (appointment_id);


--
-- Name: ix_appointment_reminders_id; Type: INDEX; Schema: public; Owner: sante
--

CREATE INDEX ix_appointment_reminders_id ON public.appointment_reminders USING btree (id);


--
-- Name: ix_appointment_reminders_patient_id; Type: INDEX; Schema: public; Owner: sante
--

CREATE INDEX ix_appointment_reminders_patient_id ON public.appointment_reminders USING btree (patient_id);


--
-- Name: ix_appointment_reminders_reminder_type; Type: INDEX; Schema: public; Owner: sante
--

CREATE INDEX ix_appointment_reminders_reminder_type ON public.appointment_reminders USING btree (reminder_type);


--
-- Name: ix_appointment_reminders_scheduled_at; Type: INDEX; Schema: public; Owner: sante
--

CREATE INDEX ix_appointment_reminders_scheduled_at ON public.appointment_reminders USING btree (scheduled_at);


--
-- Name: ix_appointment_reminders_status; Type: INDEX; Schema: public; Owner: sante
--

CREATE INDEX ix_appointment_reminders_status ON public.appointment_reminders USING btree (status);


--
-- Name: ix_attachment_access_logs_appointment_id; Type: INDEX; Schema: public; Owner: sante
--

CREATE INDEX ix_attachment_access_logs_appointment_id ON public.attachment_access_logs USING btree (appointment_id);


--
-- Name: ix_attachment_access_logs_created_at; Type: INDEX; Schema: public; Owner: sante
--

CREATE INDEX ix_attachment_access_logs_created_at ON public.attachment_access_logs USING btree (created_at);


--
-- Name: ix_attachment_access_logs_id; Type: INDEX; Schema: public; Owner: sante
--

CREATE INDEX ix_attachment_access_logs_id ON public.attachment_access_logs USING btree (id);


--
-- Name: ix_attachment_access_logs_message_id; Type: INDEX; Schema: public; Owner: sante
--

CREATE INDEX ix_attachment_access_logs_message_id ON public.attachment_access_logs USING btree (message_id);


--
-- Name: ix_attachment_access_logs_user_id; Type: INDEX; Schema: public; Owner: sante
--

CREATE INDEX ix_attachment_access_logs_user_id ON public.attachment_access_logs USING btree (user_id);


--
-- Name: ix_clinic_charge_payments_charge_id; Type: INDEX; Schema: public; Owner: sante
--

CREATE INDEX ix_clinic_charge_payments_charge_id ON public.clinic_charge_payments USING btree (charge_id);


--
-- Name: ix_clinic_charge_payments_id; Type: INDEX; Schema: public; Owner: sante
--

CREATE INDEX ix_clinic_charge_payments_id ON public.clinic_charge_payments USING btree (id);


--
-- Name: ix_clinic_charges_charge_type; Type: INDEX; Schema: public; Owner: sante
--

CREATE INDEX ix_clinic_charges_charge_type ON public.clinic_charges USING btree (charge_type);


--
-- Name: ix_clinic_charges_clinic_id; Type: INDEX; Schema: public; Owner: sante
--

CREATE INDEX ix_clinic_charges_clinic_id ON public.clinic_charges USING btree (clinic_id);


--
-- Name: ix_clinic_charges_created_at; Type: INDEX; Schema: public; Owner: sante
--

CREATE INDEX ix_clinic_charges_created_at ON public.clinic_charges USING btree (created_at);


--
-- Name: ix_clinic_charges_id; Type: INDEX; Schema: public; Owner: sante
--

CREATE INDEX ix_clinic_charges_id ON public.clinic_charges USING btree (id);


--
-- Name: ix_clinic_charges_invoice_id; Type: INDEX; Schema: public; Owner: sante
--

CREATE INDEX ix_clinic_charges_invoice_id ON public.clinic_charges USING btree (invoice_id);


--
-- Name: ix_clinic_charges_patient_id; Type: INDEX; Schema: public; Owner: sante
--

CREATE INDEX ix_clinic_charges_patient_id ON public.clinic_charges USING btree (patient_id);


--
-- Name: ix_clinic_charges_payment_status; Type: INDEX; Schema: public; Owner: sante
--

CREATE INDEX ix_clinic_charges_payment_status ON public.clinic_charges USING btree (payment_status);


--
-- Name: ix_clinic_charges_source_id; Type: INDEX; Schema: public; Owner: sante
--

CREATE INDEX ix_clinic_charges_source_id ON public.clinic_charges USING btree (source_id);


--
-- Name: ix_clinic_charges_visit_id; Type: INDEX; Schema: public; Owner: sante
--

CREATE INDEX ix_clinic_charges_visit_id ON public.clinic_charges USING btree (visit_id);


--
-- Name: ix_clinic_lab_tests_category; Type: INDEX; Schema: public; Owner: sante
--

CREATE INDEX ix_clinic_lab_tests_category ON public.clinic_lab_tests USING btree (category);


--
-- Name: ix_clinic_lab_tests_clinic_id; Type: INDEX; Schema: public; Owner: sante
--

CREATE INDEX ix_clinic_lab_tests_clinic_id ON public.clinic_lab_tests USING btree (clinic_id);


--
-- Name: ix_clinic_lab_tests_id; Type: INDEX; Schema: public; Owner: sante
--

CREATE INDEX ix_clinic_lab_tests_id ON public.clinic_lab_tests USING btree (id);


--
-- Name: ix_clinic_node_heartbeats_clinic_id; Type: INDEX; Schema: public; Owner: sante
--

CREATE INDEX ix_clinic_node_heartbeats_clinic_id ON public.clinic_node_heartbeats USING btree (clinic_id);


--
-- Name: ix_clinic_node_heartbeats_id; Type: INDEX; Schema: public; Owner: sante
--

CREATE INDEX ix_clinic_node_heartbeats_id ON public.clinic_node_heartbeats USING btree (id);


--
-- Name: ix_clinic_node_heartbeats_node_id; Type: INDEX; Schema: public; Owner: sante
--

CREATE INDEX ix_clinic_node_heartbeats_node_id ON public.clinic_node_heartbeats USING btree (node_id);


--
-- Name: ix_clinic_node_licenses_clinic_id; Type: INDEX; Schema: public; Owner: sante
--

CREATE INDEX ix_clinic_node_licenses_clinic_id ON public.clinic_node_licenses USING btree (clinic_id);


--
-- Name: ix_clinic_node_licenses_id; Type: INDEX; Schema: public; Owner: sante
--

CREATE INDEX ix_clinic_node_licenses_id ON public.clinic_node_licenses USING btree (id);


--
-- Name: ix_clinic_refunds_clinic_id; Type: INDEX; Schema: public; Owner: sante
--

CREATE INDEX ix_clinic_refunds_clinic_id ON public.clinic_refunds USING btree (clinic_id);


--
-- Name: ix_clinic_refunds_id; Type: INDEX; Schema: public; Owner: sante
--

CREATE INDEX ix_clinic_refunds_id ON public.clinic_refunds USING btree (id);


--
-- Name: ix_clinic_refunds_invoice_id; Type: INDEX; Schema: public; Owner: sante
--

CREATE INDEX ix_clinic_refunds_invoice_id ON public.clinic_refunds USING btree (invoice_id);


--
-- Name: ix_clinic_refunds_patient_id; Type: INDEX; Schema: public; Owner: sante
--

CREATE INDEX ix_clinic_refunds_patient_id ON public.clinic_refunds USING btree (patient_id);


--
-- Name: ix_clinic_refunds_reason; Type: INDEX; Schema: public; Owner: sante
--

CREATE INDEX ix_clinic_refunds_reason ON public.clinic_refunds USING btree (reason);


--
-- Name: ix_clinic_refunds_refund_number; Type: INDEX; Schema: public; Owner: sante
--

CREATE UNIQUE INDEX ix_clinic_refunds_refund_number ON public.clinic_refunds USING btree (refund_number);


--
-- Name: ix_clinic_refunds_status; Type: INDEX; Schema: public; Owner: sante
--

CREATE INDEX ix_clinic_refunds_status ON public.clinic_refunds USING btree (status);


--
-- Name: ix_clinic_service_requests_admission_id; Type: INDEX; Schema: public; Owner: sante
--

CREATE INDEX ix_clinic_service_requests_admission_id ON public.clinic_service_requests USING btree (admission_id);


--
-- Name: ix_clinic_service_requests_clinic_id; Type: INDEX; Schema: public; Owner: sante
--

CREATE INDEX ix_clinic_service_requests_clinic_id ON public.clinic_service_requests USING btree (clinic_id);


--
-- Name: ix_clinic_service_requests_id; Type: INDEX; Schema: public; Owner: sante
--

CREATE INDEX ix_clinic_service_requests_id ON public.clinic_service_requests USING btree (id);


--
-- Name: ix_clinic_service_requests_patient_id; Type: INDEX; Schema: public; Owner: sante
--

CREATE INDEX ix_clinic_service_requests_patient_id ON public.clinic_service_requests USING btree (patient_id);


--
-- Name: ix_clinic_service_requests_request_number; Type: INDEX; Schema: public; Owner: sante
--

CREATE UNIQUE INDEX ix_clinic_service_requests_request_number ON public.clinic_service_requests USING btree (request_number);


--
-- Name: ix_clinic_service_requests_service_category; Type: INDEX; Schema: public; Owner: sante
--

CREATE INDEX ix_clinic_service_requests_service_category ON public.clinic_service_requests USING btree (service_category);


--
-- Name: ix_clinic_service_requests_status; Type: INDEX; Schema: public; Owner: sante
--

CREATE INDEX ix_clinic_service_requests_status ON public.clinic_service_requests USING btree (status);


--
-- Name: ix_clinic_staff_clinic_id; Type: INDEX; Schema: public; Owner: sante
--

CREATE INDEX ix_clinic_staff_clinic_id ON public.clinic_staff USING btree (clinic_id);


--
-- Name: ix_clinic_staff_id; Type: INDEX; Schema: public; Owner: sante
--

CREATE INDEX ix_clinic_staff_id ON public.clinic_staff USING btree (id);


--
-- Name: ix_clinic_staff_user_id; Type: INDEX; Schema: public; Owner: sante
--

CREATE INDEX ix_clinic_staff_user_id ON public.clinic_staff USING btree (user_id);


--
-- Name: ix_clinical_audit_logs_actor_id; Type: INDEX; Schema: public; Owner: sante
--

CREATE INDEX ix_clinical_audit_logs_actor_id ON public.clinical_audit_logs USING btree (actor_id);


--
-- Name: ix_clinical_audit_logs_clinic_id; Type: INDEX; Schema: public; Owner: sante
--

CREATE INDEX ix_clinical_audit_logs_clinic_id ON public.clinical_audit_logs USING btree (clinic_id);


--
-- Name: ix_clinical_audit_logs_id; Type: INDEX; Schema: public; Owner: sante
--

CREATE INDEX ix_clinical_audit_logs_id ON public.clinical_audit_logs USING btree (id);


--
-- Name: ix_clinical_audit_logs_patient_id; Type: INDEX; Schema: public; Owner: sante
--

CREATE INDEX ix_clinical_audit_logs_patient_id ON public.clinical_audit_logs USING btree (patient_id);


--
-- Name: ix_clinical_audit_logs_timestamp; Type: INDEX; Schema: public; Owner: sante
--

CREATE INDEX ix_clinical_audit_logs_timestamp ON public.clinical_audit_logs USING btree ("timestamp");


--
-- Name: ix_clinical_notes_appointment_id; Type: INDEX; Schema: public; Owner: sante
--

CREATE INDEX ix_clinical_notes_appointment_id ON public.clinical_notes USING btree (appointment_id);


--
-- Name: ix_clinical_notes_created_at; Type: INDEX; Schema: public; Owner: sante
--

CREATE INDEX ix_clinical_notes_created_at ON public.clinical_notes USING btree (created_at);


--
-- Name: ix_clinical_notes_doctor_id; Type: INDEX; Schema: public; Owner: sante
--

CREATE INDEX ix_clinical_notes_doctor_id ON public.clinical_notes USING btree (doctor_id);


--
-- Name: ix_clinical_notes_id; Type: INDEX; Schema: public; Owner: sante
--

CREATE INDEX ix_clinical_notes_id ON public.clinical_notes USING btree (id);


--
-- Name: ix_clinical_notes_patient_id; Type: INDEX; Schema: public; Owner: sante
--

CREATE INDEX ix_clinical_notes_patient_id ON public.clinical_notes USING btree (patient_id);


--
-- Name: ix_clinical_visits_admission_id; Type: INDEX; Schema: public; Owner: sante
--

CREATE INDEX ix_clinical_visits_admission_id ON public.clinical_visits USING btree (admission_id);


--
-- Name: ix_clinical_visits_appointment_id; Type: INDEX; Schema: public; Owner: sante
--

CREATE INDEX ix_clinical_visits_appointment_id ON public.clinical_visits USING btree (appointment_id);


--
-- Name: ix_clinical_visits_clinic_id; Type: INDEX; Schema: public; Owner: sante
--

CREATE INDEX ix_clinical_visits_clinic_id ON public.clinical_visits USING btree (clinic_id);


--
-- Name: ix_clinical_visits_consultation_id; Type: INDEX; Schema: public; Owner: sante
--

CREATE INDEX ix_clinical_visits_consultation_id ON public.clinical_visits USING btree (consultation_id);


--
-- Name: ix_clinical_visits_id; Type: INDEX; Schema: public; Owner: sante
--

CREATE INDEX ix_clinical_visits_id ON public.clinical_visits USING btree (id);


--
-- Name: ix_clinical_visits_patient_id; Type: INDEX; Schema: public; Owner: sante
--

CREATE INDEX ix_clinical_visits_patient_id ON public.clinical_visits USING btree (patient_id);


--
-- Name: ix_clinical_visits_status; Type: INDEX; Schema: public; Owner: sante
--

CREATE INDEX ix_clinical_visits_status ON public.clinical_visits USING btree (status);


--
-- Name: ix_clinics_city; Type: INDEX; Schema: public; Owner: sante
--

CREATE INDEX ix_clinics_city ON public.clinics USING btree (city);


--
-- Name: ix_clinics_id; Type: INDEX; Schema: public; Owner: sante
--

CREATE INDEX ix_clinics_id ON public.clinics USING btree (id);


--
-- Name: ix_clinics_is_active; Type: INDEX; Schema: public; Owner: sante
--

CREATE INDEX ix_clinics_is_active ON public.clinics USING btree (is_active);


--
-- Name: ix_clinics_name; Type: INDEX; Schema: public; Owner: sante
--

CREATE INDEX ix_clinics_name ON public.clinics USING btree (name);


--
-- Name: ix_consultation_summaries_appointment_id; Type: INDEX; Schema: public; Owner: sante
--

CREATE INDEX ix_consultation_summaries_appointment_id ON public.consultation_summaries USING btree (appointment_id);


--
-- Name: ix_consultation_summaries_created_at; Type: INDEX; Schema: public; Owner: sante
--

CREATE INDEX ix_consultation_summaries_created_at ON public.consultation_summaries USING btree (created_at);


--
-- Name: ix_consultation_summaries_doctor_id; Type: INDEX; Schema: public; Owner: sante
--

CREATE INDEX ix_consultation_summaries_doctor_id ON public.consultation_summaries USING btree (doctor_id);


--
-- Name: ix_consultation_summaries_id; Type: INDEX; Schema: public; Owner: sante
--

CREATE INDEX ix_consultation_summaries_id ON public.consultation_summaries USING btree (id);


--
-- Name: ix_consultation_summaries_patient_id; Type: INDEX; Schema: public; Owner: sante
--

CREATE INDEX ix_consultation_summaries_patient_id ON public.consultation_summaries USING btree (patient_id);


--
-- Name: ix_consultations_appointment_id; Type: INDEX; Schema: public; Owner: sante
--

CREATE UNIQUE INDEX ix_consultations_appointment_id ON public.consultations USING btree (appointment_id);


--
-- Name: ix_consultations_clinic_id; Type: INDEX; Schema: public; Owner: sante
--

CREATE INDEX ix_consultations_clinic_id ON public.consultations USING btree (clinic_id);


--
-- Name: ix_consultations_doctor_id; Type: INDEX; Schema: public; Owner: sante
--

CREATE INDEX ix_consultations_doctor_id ON public.consultations USING btree (doctor_id);


--
-- Name: ix_consultations_id; Type: INDEX; Schema: public; Owner: sante
--

CREATE INDEX ix_consultations_id ON public.consultations USING btree (id);


--
-- Name: ix_consultations_patient_id; Type: INDEX; Schema: public; Owner: sante
--

CREATE INDEX ix_consultations_patient_id ON public.consultations USING btree (patient_id);


--
-- Name: ix_consultations_status; Type: INDEX; Schema: public; Owner: sante
--

CREATE INDEX ix_consultations_status ON public.consultations USING btree (status);


--
-- Name: ix_discharge_summaries_admission_id; Type: INDEX; Schema: public; Owner: sante
--

CREATE INDEX ix_discharge_summaries_admission_id ON public.discharge_summaries USING btree (admission_id);


--
-- Name: ix_discharge_summaries_clinic_id; Type: INDEX; Schema: public; Owner: sante
--

CREATE INDEX ix_discharge_summaries_clinic_id ON public.discharge_summaries USING btree (clinic_id);


--
-- Name: ix_discharge_summaries_consultation_id; Type: INDEX; Schema: public; Owner: sante
--

CREATE INDEX ix_discharge_summaries_consultation_id ON public.discharge_summaries USING btree (consultation_id);


--
-- Name: ix_discharge_summaries_id; Type: INDEX; Schema: public; Owner: sante
--

CREATE INDEX ix_discharge_summaries_id ON public.discharge_summaries USING btree (id);


--
-- Name: ix_discharge_summaries_invoice_id; Type: INDEX; Schema: public; Owner: sante
--

CREATE INDEX ix_discharge_summaries_invoice_id ON public.discharge_summaries USING btree (invoice_id);


--
-- Name: ix_discharge_summaries_patient_id; Type: INDEX; Schema: public; Owner: sante
--

CREATE INDEX ix_discharge_summaries_patient_id ON public.discharge_summaries USING btree (patient_id);


--
-- Name: ix_discharge_summaries_status; Type: INDEX; Schema: public; Owner: sante
--

CREATE INDEX ix_discharge_summaries_status ON public.discharge_summaries USING btree (status);


--
-- Name: ix_discharge_summaries_visit_id; Type: INDEX; Schema: public; Owner: sante
--

CREATE INDEX ix_discharge_summaries_visit_id ON public.discharge_summaries USING btree (visit_id);


--
-- Name: ix_doctor_availabilities_id; Type: INDEX; Schema: public; Owner: sante
--

CREATE INDEX ix_doctor_availabilities_id ON public.doctor_availabilities USING btree (id);


--
-- Name: ix_doctor_medicine_deliveries_clinic_id; Type: INDEX; Schema: public; Owner: sante
--

CREATE INDEX ix_doctor_medicine_deliveries_clinic_id ON public.doctor_medicine_deliveries USING btree (clinic_id);


--
-- Name: ix_doctor_medicine_deliveries_delivered_at; Type: INDEX; Schema: public; Owner: sante
--

CREATE INDEX ix_doctor_medicine_deliveries_delivered_at ON public.doctor_medicine_deliveries USING btree (delivered_at);


--
-- Name: ix_doctor_medicine_deliveries_id; Type: INDEX; Schema: public; Owner: sante
--

CREATE INDEX ix_doctor_medicine_deliveries_id ON public.doctor_medicine_deliveries USING btree (id);


--
-- Name: ix_doctor_medicine_deliveries_patient_id; Type: INDEX; Schema: public; Owner: sante
--

CREATE INDEX ix_doctor_medicine_deliveries_patient_id ON public.doctor_medicine_deliveries USING btree (patient_id);


--
-- Name: ix_doctor_medicine_deliveries_recorded_by_user_id; Type: INDEX; Schema: public; Owner: sante
--

CREATE INDEX ix_doctor_medicine_deliveries_recorded_by_user_id ON public.doctor_medicine_deliveries USING btree (recorded_by_user_id);


--
-- Name: ix_doctors_city; Type: INDEX; Schema: public; Owner: sante
--

CREATE INDEX ix_doctors_city ON public.doctors USING btree (city);


--
-- Name: ix_doctors_clinic_id; Type: INDEX; Schema: public; Owner: sante
--

CREATE INDEX ix_doctors_clinic_id ON public.doctors USING btree (clinic_id);


--
-- Name: ix_doctors_first_name; Type: INDEX; Schema: public; Owner: sante
--

CREATE INDEX ix_doctors_first_name ON public.doctors USING btree (first_name);


--
-- Name: ix_doctors_id; Type: INDEX; Schema: public; Owner: sante
--

CREATE INDEX ix_doctors_id ON public.doctors USING btree (id);


--
-- Name: ix_doctors_last_name; Type: INDEX; Schema: public; Owner: sante
--

CREATE INDEX ix_doctors_last_name ON public.doctors USING btree (last_name);


--
-- Name: ix_doctors_specialty; Type: INDEX; Schema: public; Owner: sante
--

CREATE INDEX ix_doctors_specialty ON public.doctors USING btree (specialty);


--
-- Name: ix_doctors_user_id; Type: INDEX; Schema: public; Owner: sante
--

CREATE INDEX ix_doctors_user_id ON public.doctors USING btree (user_id);


--
-- Name: ix_email_verification_tokens_id; Type: INDEX; Schema: public; Owner: sante
--

CREATE INDEX ix_email_verification_tokens_id ON public.email_verification_tokens USING btree (id);


--
-- Name: ix_email_verification_tokens_token_hash; Type: INDEX; Schema: public; Owner: sante
--

CREATE UNIQUE INDEX ix_email_verification_tokens_token_hash ON public.email_verification_tokens USING btree (token_hash);


--
-- Name: ix_email_verification_tokens_user_id; Type: INDEX; Schema: public; Owner: sante
--

CREATE INDEX ix_email_verification_tokens_user_id ON public.email_verification_tokens USING btree (user_id);


--
-- Name: ix_follow_up_schedules_clinic_id; Type: INDEX; Schema: public; Owner: sante
--

CREATE INDEX ix_follow_up_schedules_clinic_id ON public.follow_up_schedules USING btree (clinic_id);


--
-- Name: ix_follow_up_schedules_consultation_id; Type: INDEX; Schema: public; Owner: sante
--

CREATE INDEX ix_follow_up_schedules_consultation_id ON public.follow_up_schedules USING btree (consultation_id);


--
-- Name: ix_follow_up_schedules_doctor_id; Type: INDEX; Schema: public; Owner: sante
--

CREATE INDEX ix_follow_up_schedules_doctor_id ON public.follow_up_schedules USING btree (doctor_id);


--
-- Name: ix_follow_up_schedules_id; Type: INDEX; Schema: public; Owner: sante
--

CREATE INDEX ix_follow_up_schedules_id ON public.follow_up_schedules USING btree (id);


--
-- Name: ix_follow_up_schedules_patient_id; Type: INDEX; Schema: public; Owner: sante
--

CREATE INDEX ix_follow_up_schedules_patient_id ON public.follow_up_schedules USING btree (patient_id);


--
-- Name: ix_follow_up_schedules_scheduled_date; Type: INDEX; Schema: public; Owner: sante
--

CREATE INDEX ix_follow_up_schedules_scheduled_date ON public.follow_up_schedules USING btree (scheduled_date);


--
-- Name: ix_follow_up_schedules_status; Type: INDEX; Schema: public; Owner: sante
--

CREATE INDEX ix_follow_up_schedules_status ON public.follow_up_schedules USING btree (status);


--
-- Name: ix_hospital_beds_id; Type: INDEX; Schema: public; Owner: sante
--

CREATE INDEX ix_hospital_beds_id ON public.hospital_beds USING btree (id);


--
-- Name: ix_hospital_beds_room_id; Type: INDEX; Schema: public; Owner: sante
--

CREATE INDEX ix_hospital_beds_room_id ON public.hospital_beds USING btree (room_id);


--
-- Name: ix_hospital_beds_status; Type: INDEX; Schema: public; Owner: sante
--

CREATE INDEX ix_hospital_beds_status ON public.hospital_beds USING btree (status);


--
-- Name: ix_hospital_rooms_clinic_id; Type: INDEX; Schema: public; Owner: sante
--

CREATE INDEX ix_hospital_rooms_clinic_id ON public.hospital_rooms USING btree (clinic_id);


--
-- Name: ix_hospital_rooms_id; Type: INDEX; Schema: public; Owner: sante
--

CREATE INDEX ix_hospital_rooms_id ON public.hospital_rooms USING btree (id);


--
-- Name: ix_hospital_rooms_status; Type: INDEX; Schema: public; Owner: sante
--

CREATE INDEX ix_hospital_rooms_status ON public.hospital_rooms USING btree (status);


--
-- Name: ix_hospital_rooms_ward_name; Type: INDEX; Schema: public; Owner: sante
--

CREATE INDEX ix_hospital_rooms_ward_name ON public.hospital_rooms USING btree (ward_name);


--
-- Name: ix_imaging_orders_clinic_id; Type: INDEX; Schema: public; Owner: sante
--

CREATE INDEX ix_imaging_orders_clinic_id ON public.imaging_orders USING btree (clinic_id);


--
-- Name: ix_imaging_orders_consultation_id; Type: INDEX; Schema: public; Owner: sante
--

CREATE INDEX ix_imaging_orders_consultation_id ON public.imaging_orders USING btree (consultation_id);


--
-- Name: ix_imaging_orders_id; Type: INDEX; Schema: public; Owner: sante
--

CREATE INDEX ix_imaging_orders_id ON public.imaging_orders USING btree (id);


--
-- Name: ix_imaging_orders_modality; Type: INDEX; Schema: public; Owner: sante
--

CREATE INDEX ix_imaging_orders_modality ON public.imaging_orders USING btree (modality);


--
-- Name: ix_imaging_orders_patient_id; Type: INDEX; Schema: public; Owner: sante
--

CREATE INDEX ix_imaging_orders_patient_id ON public.imaging_orders USING btree (patient_id);


--
-- Name: ix_imaging_orders_status; Type: INDEX; Schema: public; Owner: sante
--

CREATE INDEX ix_imaging_orders_status ON public.imaging_orders USING btree (status);


--
-- Name: ix_imaging_results_id; Type: INDEX; Schema: public; Owner: sante
--

CREATE INDEX ix_imaging_results_id ON public.imaging_results USING btree (id);


--
-- Name: ix_imaging_results_order_id; Type: INDEX; Schema: public; Owner: sante
--

CREATE INDEX ix_imaging_results_order_id ON public.imaging_results USING btree (order_id);


--
-- Name: ix_imaging_results_status; Type: INDEX; Schema: public; Owner: sante
--

CREATE INDEX ix_imaging_results_status ON public.imaging_results USING btree (status);


--
-- Name: ix_immunization_records_clinic_id; Type: INDEX; Schema: public; Owner: sante
--

CREATE INDEX ix_immunization_records_clinic_id ON public.immunization_records USING btree (clinic_id);


--
-- Name: ix_immunization_records_id; Type: INDEX; Schema: public; Owner: sante
--

CREATE INDEX ix_immunization_records_id ON public.immunization_records USING btree (id);


--
-- Name: ix_immunization_records_patient_id; Type: INDEX; Schema: public; Owner: sante
--

CREATE INDEX ix_immunization_records_patient_id ON public.immunization_records USING btree (patient_id);


--
-- Name: ix_immunization_records_vaccine_code; Type: INDEX; Schema: public; Owner: sante
--

CREATE INDEX ix_immunization_records_vaccine_code ON public.immunization_records USING btree (vaccine_code);


--
-- Name: ix_invoice_items_charge_type; Type: INDEX; Schema: public; Owner: sante
--

CREATE INDEX ix_invoice_items_charge_type ON public.invoice_items USING btree (charge_type);


--
-- Name: ix_invoice_items_clinic_charge_id; Type: INDEX; Schema: public; Owner: sante
--

CREATE INDEX ix_invoice_items_clinic_charge_id ON public.invoice_items USING btree (clinic_charge_id);


--
-- Name: ix_invoice_items_id; Type: INDEX; Schema: public; Owner: sante
--

CREATE INDEX ix_invoice_items_id ON public.invoice_items USING btree (id);


--
-- Name: ix_invoice_items_invoice_id; Type: INDEX; Schema: public; Owner: sante
--

CREATE INDEX ix_invoice_items_invoice_id ON public.invoice_items USING btree (invoice_id);


--
-- Name: ix_invoices_clinic_id; Type: INDEX; Schema: public; Owner: sante
--

CREATE INDEX ix_invoices_clinic_id ON public.invoices USING btree (clinic_id);


--
-- Name: ix_invoices_department; Type: INDEX; Schema: public; Owner: sante
--

CREATE INDEX ix_invoices_department ON public.invoices USING btree (department);


--
-- Name: ix_invoices_id; Type: INDEX; Schema: public; Owner: sante
--

CREATE INDEX ix_invoices_id ON public.invoices USING btree (id);


--
-- Name: ix_invoices_invoice_number; Type: INDEX; Schema: public; Owner: sante
--

CREATE UNIQUE INDEX ix_invoices_invoice_number ON public.invoices USING btree (invoice_number);


--
-- Name: ix_invoices_patient_id; Type: INDEX; Schema: public; Owner: sante
--

CREATE INDEX ix_invoices_patient_id ON public.invoices USING btree (patient_id);


--
-- Name: ix_invoices_status; Type: INDEX; Schema: public; Owner: sante
--

CREATE INDEX ix_invoices_status ON public.invoices USING btree (status);


--
-- Name: ix_invoices_visit_id; Type: INDEX; Schema: public; Owner: sante
--

CREATE INDEX ix_invoices_visit_id ON public.invoices USING btree (visit_id);


--
-- Name: ix_lab_orders_clinic_id; Type: INDEX; Schema: public; Owner: sante
--

CREATE INDEX ix_lab_orders_clinic_id ON public.lab_orders USING btree (clinic_id);


--
-- Name: ix_lab_orders_consultation_id; Type: INDEX; Schema: public; Owner: sante
--

CREATE INDEX ix_lab_orders_consultation_id ON public.lab_orders USING btree (consultation_id);


--
-- Name: ix_lab_orders_doctor_id; Type: INDEX; Schema: public; Owner: sante
--

CREATE INDEX ix_lab_orders_doctor_id ON public.lab_orders USING btree (doctor_id);


--
-- Name: ix_lab_orders_id; Type: INDEX; Schema: public; Owner: sante
--

CREATE INDEX ix_lab_orders_id ON public.lab_orders USING btree (id);


--
-- Name: ix_lab_orders_ordered_by_user_id; Type: INDEX; Schema: public; Owner: sante
--

CREATE INDEX ix_lab_orders_ordered_by_user_id ON public.lab_orders USING btree (ordered_by_user_id);


--
-- Name: ix_lab_orders_patient_id; Type: INDEX; Schema: public; Owner: sante
--

CREATE INDEX ix_lab_orders_patient_id ON public.lab_orders USING btree (patient_id);


--
-- Name: ix_lab_orders_status; Type: INDEX; Schema: public; Owner: sante
--

CREATE INDEX ix_lab_orders_status ON public.lab_orders USING btree (status);


--
-- Name: ix_lab_orders_test_code; Type: INDEX; Schema: public; Owner: sante
--

CREATE INDEX ix_lab_orders_test_code ON public.lab_orders USING btree (test_code);


--
-- Name: ix_lab_results_id; Type: INDEX; Schema: public; Owner: sante
--

CREATE INDEX ix_lab_results_id ON public.lab_results USING btree (id);


--
-- Name: ix_lab_results_lab_order_id; Type: INDEX; Schema: public; Owner: sante
--

CREATE UNIQUE INDEX ix_lab_results_lab_order_id ON public.lab_results USING btree (lab_order_id);


--
-- Name: ix_lab_results_recorded_by_user_id; Type: INDEX; Schema: public; Owner: sante
--

CREATE INDEX ix_lab_results_recorded_by_user_id ON public.lab_results USING btree (recorded_by_user_id);


--
-- Name: ix_lab_results_status; Type: INDEX; Schema: public; Owner: sante
--

CREATE INDEX ix_lab_results_status ON public.lab_results USING btree (status);


--
-- Name: ix_messages_appointment_id; Type: INDEX; Schema: public; Owner: sante
--

CREATE INDEX ix_messages_appointment_id ON public.messages USING btree (appointment_id);


--
-- Name: ix_messages_attachment_storage_key; Type: INDEX; Schema: public; Owner: sante
--

CREATE INDEX ix_messages_attachment_storage_key ON public.messages USING btree (attachment_storage_key);


--
-- Name: ix_messages_created_at; Type: INDEX; Schema: public; Owner: sante
--

CREATE INDEX ix_messages_created_at ON public.messages USING btree (created_at);


--
-- Name: ix_messages_id; Type: INDEX; Schema: public; Owner: sante
--

CREATE INDEX ix_messages_id ON public.messages USING btree (id);


--
-- Name: ix_messages_sender_user_id; Type: INDEX; Schema: public; Owner: sante
--

CREATE INDEX ix_messages_sender_user_id ON public.messages USING btree (sender_user_id);


--
-- Name: ix_notification_events_channel; Type: INDEX; Schema: public; Owner: sante
--

CREATE INDEX ix_notification_events_channel ON public.notification_events USING btree (channel);


--
-- Name: ix_notification_events_id; Type: INDEX; Schema: public; Owner: sante
--

CREATE INDEX ix_notification_events_id ON public.notification_events USING btree (id);


--
-- Name: ix_notification_events_user_id; Type: INDEX; Schema: public; Owner: sante
--

CREATE INDEX ix_notification_events_user_id ON public.notification_events USING btree (user_id);


--
-- Name: ix_nurse_assessments_admission_id; Type: INDEX; Schema: public; Owner: sante
--

CREATE INDEX ix_nurse_assessments_admission_id ON public.nurse_assessments USING btree (admission_id);


--
-- Name: ix_nurse_assessments_appointment_id; Type: INDEX; Schema: public; Owner: sante
--

CREATE INDEX ix_nurse_assessments_appointment_id ON public.nurse_assessments USING btree (appointment_id);


--
-- Name: ix_nurse_assessments_clinic_id; Type: INDEX; Schema: public; Owner: sante
--

CREATE INDEX ix_nurse_assessments_clinic_id ON public.nurse_assessments USING btree (clinic_id);


--
-- Name: ix_nurse_assessments_consultation_id; Type: INDEX; Schema: public; Owner: sante
--

CREATE INDEX ix_nurse_assessments_consultation_id ON public.nurse_assessments USING btree (consultation_id);


--
-- Name: ix_nurse_assessments_id; Type: INDEX; Schema: public; Owner: sante
--

CREATE INDEX ix_nurse_assessments_id ON public.nurse_assessments USING btree (id);


--
-- Name: ix_nurse_assessments_patient_id; Type: INDEX; Schema: public; Owner: sante
--

CREATE INDEX ix_nurse_assessments_patient_id ON public.nurse_assessments USING btree (patient_id);


--
-- Name: ix_nursing_procedures_clinic_id; Type: INDEX; Schema: public; Owner: sante
--

CREATE INDEX ix_nursing_procedures_clinic_id ON public.nursing_procedures USING btree (clinic_id);


--
-- Name: ix_nursing_procedures_id; Type: INDEX; Schema: public; Owner: sante
--

CREATE INDEX ix_nursing_procedures_id ON public.nursing_procedures USING btree (id);


--
-- Name: ix_nursing_procedures_patient_id; Type: INDEX; Schema: public; Owner: sante
--

CREATE INDEX ix_nursing_procedures_patient_id ON public.nursing_procedures USING btree (patient_id);


--
-- Name: ix_nursing_procedures_procedure_date; Type: INDEX; Schema: public; Owner: sante
--

CREATE INDEX ix_nursing_procedures_procedure_date ON public.nursing_procedures USING btree (procedure_date);


--
-- Name: ix_nursing_procedures_procedure_type; Type: INDEX; Schema: public; Owner: sante
--

CREATE INDEX ix_nursing_procedures_procedure_type ON public.nursing_procedures USING btree (procedure_type);


--
-- Name: ix_nutrition_assessments_clinic_id; Type: INDEX; Schema: public; Owner: sante
--

CREATE INDEX ix_nutrition_assessments_clinic_id ON public.nutrition_assessments USING btree (clinic_id);


--
-- Name: ix_nutrition_assessments_consultation_id; Type: INDEX; Schema: public; Owner: sante
--

CREATE INDEX ix_nutrition_assessments_consultation_id ON public.nutrition_assessments USING btree (consultation_id);


--
-- Name: ix_nutrition_assessments_id; Type: INDEX; Schema: public; Owner: sante
--

CREATE INDEX ix_nutrition_assessments_id ON public.nutrition_assessments USING btree (id);


--
-- Name: ix_nutrition_assessments_patient_id; Type: INDEX; Schema: public; Owner: sante
--

CREATE INDEX ix_nutrition_assessments_patient_id ON public.nutrition_assessments USING btree (patient_id);


--
-- Name: ix_password_reset_tokens_id; Type: INDEX; Schema: public; Owner: sante
--

CREATE INDEX ix_password_reset_tokens_id ON public.password_reset_tokens USING btree (id);


--
-- Name: ix_password_reset_tokens_token_hash; Type: INDEX; Schema: public; Owner: sante
--

CREATE UNIQUE INDEX ix_password_reset_tokens_token_hash ON public.password_reset_tokens USING btree (token_hash);


--
-- Name: ix_password_reset_tokens_user_id; Type: INDEX; Schema: public; Owner: sante
--

CREATE INDEX ix_password_reset_tokens_user_id ON public.password_reset_tokens USING btree (user_id);


--
-- Name: ix_patient_allergies_id; Type: INDEX; Schema: public; Owner: sante
--

CREATE INDEX ix_patient_allergies_id ON public.patient_allergies USING btree (id);


--
-- Name: ix_patient_allergies_patient_id; Type: INDEX; Schema: public; Owner: sante
--

CREATE INDEX ix_patient_allergies_patient_id ON public.patient_allergies USING btree (patient_id);


--
-- Name: ix_patient_chronic_conditions_id; Type: INDEX; Schema: public; Owner: sante
--

CREATE INDEX ix_patient_chronic_conditions_id ON public.patient_chronic_conditions USING btree (id);


--
-- Name: ix_patient_chronic_conditions_patient_id; Type: INDEX; Schema: public; Owner: sante
--

CREATE INDEX ix_patient_chronic_conditions_patient_id ON public.patient_chronic_conditions USING btree (patient_id);


--
-- Name: ix_patient_documents_created_at; Type: INDEX; Schema: public; Owner: sante
--

CREATE INDEX ix_patient_documents_created_at ON public.patient_documents USING btree (created_at);


--
-- Name: ix_patient_documents_id; Type: INDEX; Schema: public; Owner: sante
--

CREATE INDEX ix_patient_documents_id ON public.patient_documents USING btree (id);


--
-- Name: ix_patient_documents_patient_id; Type: INDEX; Schema: public; Owner: sante
--

CREATE INDEX ix_patient_documents_patient_id ON public.patient_documents USING btree (patient_id);


--
-- Name: ix_patient_documents_uploaded_by; Type: INDEX; Schema: public; Owner: sante
--

CREATE INDEX ix_patient_documents_uploaded_by ON public.patient_documents USING btree (uploaded_by);


--
-- Name: ix_patient_medical_records_id; Type: INDEX; Schema: public; Owner: sante
--

CREATE INDEX ix_patient_medical_records_id ON public.patient_medical_records USING btree (id);


--
-- Name: ix_patient_medical_records_patient_id; Type: INDEX; Schema: public; Owner: sante
--

CREATE UNIQUE INDEX ix_patient_medical_records_patient_id ON public.patient_medical_records USING btree (patient_id);


--
-- Name: ix_patient_stays_admission_id; Type: INDEX; Schema: public; Owner: sante
--

CREATE INDEX ix_patient_stays_admission_id ON public.patient_stays USING btree (admission_id);


--
-- Name: ix_patient_stays_bed_id; Type: INDEX; Schema: public; Owner: sante
--

CREATE INDEX ix_patient_stays_bed_id ON public.patient_stays USING btree (bed_id);


--
-- Name: ix_patient_stays_id; Type: INDEX; Schema: public; Owner: sante
--

CREATE INDEX ix_patient_stays_id ON public.patient_stays USING btree (id);


--
-- Name: ix_patient_stays_is_current; Type: INDEX; Schema: public; Owner: sante
--

CREATE INDEX ix_patient_stays_is_current ON public.patient_stays USING btree (is_current);


--
-- Name: ix_patient_visit_workflow_steps_department; Type: INDEX; Schema: public; Owner: sante
--

CREATE INDEX ix_patient_visit_workflow_steps_department ON public.patient_visit_workflow_steps USING btree (department);


--
-- Name: ix_patient_visit_workflow_steps_id; Type: INDEX; Schema: public; Owner: sante
--

CREATE INDEX ix_patient_visit_workflow_steps_id ON public.patient_visit_workflow_steps USING btree (id);


--
-- Name: ix_patient_visit_workflow_steps_status; Type: INDEX; Schema: public; Owner: sante
--

CREATE INDEX ix_patient_visit_workflow_steps_status ON public.patient_visit_workflow_steps USING btree (status);


--
-- Name: ix_patient_visit_workflow_steps_workflow_id; Type: INDEX; Schema: public; Owner: sante
--

CREATE INDEX ix_patient_visit_workflow_steps_workflow_id ON public.patient_visit_workflow_steps USING btree (workflow_id);


--
-- Name: ix_patient_visit_workflows_clinic_id; Type: INDEX; Schema: public; Owner: sante
--

CREATE INDEX ix_patient_visit_workflows_clinic_id ON public.patient_visit_workflows USING btree (clinic_id);


--
-- Name: ix_patient_visit_workflows_clinical_visit_id; Type: INDEX; Schema: public; Owner: sante
--

CREATE INDEX ix_patient_visit_workflows_clinical_visit_id ON public.patient_visit_workflows USING btree (clinical_visit_id);


--
-- Name: ix_patient_visit_workflows_current_department; Type: INDEX; Schema: public; Owner: sante
--

CREATE INDEX ix_patient_visit_workflows_current_department ON public.patient_visit_workflows USING btree (current_department);


--
-- Name: ix_patient_visit_workflows_id; Type: INDEX; Schema: public; Owner: sante
--

CREATE INDEX ix_patient_visit_workflows_id ON public.patient_visit_workflows USING btree (id);


--
-- Name: ix_patient_visit_workflows_patient_id; Type: INDEX; Schema: public; Owner: sante
--

CREATE INDEX ix_patient_visit_workflows_patient_id ON public.patient_visit_workflows USING btree (patient_id);


--
-- Name: ix_patient_visit_workflows_status; Type: INDEX; Schema: public; Owner: sante
--

CREATE INDEX ix_patient_visit_workflows_status ON public.patient_visit_workflows USING btree (status);


--
-- Name: ix_patient_visit_workflows_workflow_type; Type: INDEX; Schema: public; Owner: sante
--

CREATE INDEX ix_patient_visit_workflows_workflow_type ON public.patient_visit_workflows USING btree (workflow_type);


--
-- Name: ix_patient_vital_signs_consultation_id; Type: INDEX; Schema: public; Owner: sante
--

CREATE INDEX ix_patient_vital_signs_consultation_id ON public.patient_vital_signs USING btree (consultation_id);


--
-- Name: ix_patient_vital_signs_id; Type: INDEX; Schema: public; Owner: sante
--

CREATE INDEX ix_patient_vital_signs_id ON public.patient_vital_signs USING btree (id);


--
-- Name: ix_patient_vital_signs_patient_id; Type: INDEX; Schema: public; Owner: sante
--

CREATE INDEX ix_patient_vital_signs_patient_id ON public.patient_vital_signs USING btree (patient_id);


--
-- Name: ix_patients_clinic_id; Type: INDEX; Schema: public; Owner: sante
--

CREATE INDEX ix_patients_clinic_id ON public.patients USING btree (clinic_id);


--
-- Name: ix_patients_first_name; Type: INDEX; Schema: public; Owner: sante
--

CREATE INDEX ix_patients_first_name ON public.patients USING btree (first_name);


--
-- Name: ix_patients_id; Type: INDEX; Schema: public; Owner: sante
--

CREATE INDEX ix_patients_id ON public.patients USING btree (id);


--
-- Name: ix_patients_is_archived; Type: INDEX; Schema: public; Owner: sante
--

CREATE INDEX ix_patients_is_archived ON public.patients USING btree (is_archived);


--
-- Name: ix_patients_last_name; Type: INDEX; Schema: public; Owner: sante
--

CREATE INDEX ix_patients_last_name ON public.patients USING btree (last_name);


--
-- Name: ix_patients_patient_number; Type: INDEX; Schema: public; Owner: sante
--

CREATE INDEX ix_patients_patient_number ON public.patients USING btree (patient_number);


--
-- Name: ix_patients_qr_token; Type: INDEX; Schema: public; Owner: sante
--

CREATE UNIQUE INDEX ix_patients_qr_token ON public.patients USING btree (qr_token);


--
-- Name: ix_patients_user_id; Type: INDEX; Schema: public; Owner: sante
--

CREATE INDEX ix_patients_user_id ON public.patients USING btree (user_id);


--
-- Name: ix_payment_records_id; Type: INDEX; Schema: public; Owner: sante
--

CREATE INDEX ix_payment_records_id ON public.payment_records USING btree (id);


--
-- Name: ix_payment_records_invoice_id; Type: INDEX; Schema: public; Owner: sante
--

CREATE INDEX ix_payment_records_invoice_id ON public.payment_records USING btree (invoice_id);


--
-- Name: ix_payments_appointment_id; Type: INDEX; Schema: public; Owner: sante
--

CREATE INDEX ix_payments_appointment_id ON public.payments USING btree (appointment_id);


--
-- Name: ix_payments_id; Type: INDEX; Schema: public; Owner: sante
--

CREATE INDEX ix_payments_id ON public.payments USING btree (id);


--
-- Name: ix_payments_last_stripe_event_id; Type: INDEX; Schema: public; Owner: sante
--

CREATE INDEX ix_payments_last_stripe_event_id ON public.payments USING btree (last_stripe_event_id);


--
-- Name: ix_payments_payment_id; Type: INDEX; Schema: public; Owner: sante
--

CREATE UNIQUE INDEX ix_payments_payment_id ON public.payments USING btree (payment_id);


--
-- Name: ix_payments_refund_status; Type: INDEX; Schema: public; Owner: sante
--

CREATE INDEX ix_payments_refund_status ON public.payments USING btree (refund_status);


--
-- Name: ix_payments_settlement_channel; Type: INDEX; Schema: public; Owner: sante
--

CREATE INDEX ix_payments_settlement_channel ON public.payments USING btree (settlement_channel);


--
-- Name: ix_payments_status; Type: INDEX; Schema: public; Owner: sante
--

CREATE INDEX ix_payments_status ON public.payments USING btree (status);


--
-- Name: ix_payments_stripe_session_id; Type: INDEX; Schema: public; Owner: sante
--

CREATE INDEX ix_payments_stripe_session_id ON public.payments USING btree (stripe_session_id);


--
-- Name: ix_pharmacy_inventory_clinic_id; Type: INDEX; Schema: public; Owner: sante
--

CREATE INDEX ix_pharmacy_inventory_clinic_id ON public.pharmacy_inventory USING btree (clinic_id);


--
-- Name: ix_pharmacy_inventory_id; Type: INDEX; Schema: public; Owner: sante
--

CREATE INDEX ix_pharmacy_inventory_id ON public.pharmacy_inventory USING btree (id);


--
-- Name: ix_pharmacy_inventory_medication_name; Type: INDEX; Schema: public; Owner: sante
--

CREATE INDEX ix_pharmacy_inventory_medication_name ON public.pharmacy_inventory USING btree (medication_name);


--
-- Name: ix_pharmacy_inventory_sku; Type: INDEX; Schema: public; Owner: sante
--

CREATE INDEX ix_pharmacy_inventory_sku ON public.pharmacy_inventory USING btree (sku);


--
-- Name: ix_pharmacy_orders_clinic_id; Type: INDEX; Schema: public; Owner: sante
--

CREATE INDEX ix_pharmacy_orders_clinic_id ON public.pharmacy_orders USING btree (clinic_id);


--
-- Name: ix_pharmacy_orders_id; Type: INDEX; Schema: public; Owner: sante
--

CREATE INDEX ix_pharmacy_orders_id ON public.pharmacy_orders USING btree (id);


--
-- Name: ix_pharmacy_orders_patient_id; Type: INDEX; Schema: public; Owner: sante
--

CREATE INDEX ix_pharmacy_orders_patient_id ON public.pharmacy_orders USING btree (patient_id);


--
-- Name: ix_pharmacy_orders_prescription_id; Type: INDEX; Schema: public; Owner: sante
--

CREATE INDEX ix_pharmacy_orders_prescription_id ON public.pharmacy_orders USING btree (prescription_id);


--
-- Name: ix_pharmacy_orders_status; Type: INDEX; Schema: public; Owner: sante
--

CREATE INDEX ix_pharmacy_orders_status ON public.pharmacy_orders USING btree (status);


--
-- Name: ix_prescription_items_id; Type: INDEX; Schema: public; Owner: sante
--

CREATE INDEX ix_prescription_items_id ON public.prescription_items USING btree (id);


--
-- Name: ix_prescription_items_prescription_id; Type: INDEX; Schema: public; Owner: sante
--

CREATE INDEX ix_prescription_items_prescription_id ON public.prescription_items USING btree (prescription_id);


--
-- Name: ix_prescriptions_clinic_id; Type: INDEX; Schema: public; Owner: sante
--

CREATE INDEX ix_prescriptions_clinic_id ON public.prescriptions USING btree (clinic_id);


--
-- Name: ix_prescriptions_consultation_id; Type: INDEX; Schema: public; Owner: sante
--

CREATE INDEX ix_prescriptions_consultation_id ON public.prescriptions USING btree (consultation_id);


--
-- Name: ix_prescriptions_id; Type: INDEX; Schema: public; Owner: sante
--

CREATE INDEX ix_prescriptions_id ON public.prescriptions USING btree (id);


--
-- Name: ix_prescriptions_patient_id; Type: INDEX; Schema: public; Owner: sante
--

CREATE INDEX ix_prescriptions_patient_id ON public.prescriptions USING btree (patient_id);


--
-- Name: ix_prescriptions_prescriber_doctor_id; Type: INDEX; Schema: public; Owner: sante
--

CREATE INDEX ix_prescriptions_prescriber_doctor_id ON public.prescriptions USING btree (prescriber_doctor_id);


--
-- Name: ix_prescriptions_status; Type: INDEX; Schema: public; Owner: sante
--

CREATE INDEX ix_prescriptions_status ON public.prescriptions USING btree (status);


--
-- Name: ix_reminder_events_event_type; Type: INDEX; Schema: public; Owner: sante
--

CREATE INDEX ix_reminder_events_event_type ON public.reminder_events USING btree (event_type);


--
-- Name: ix_reminder_events_id; Type: INDEX; Schema: public; Owner: sante
--

CREATE INDEX ix_reminder_events_id ON public.reminder_events USING btree (id);


--
-- Name: ix_reminder_events_reminder_id; Type: INDEX; Schema: public; Owner: sante
--

CREATE INDEX ix_reminder_events_reminder_id ON public.reminder_events USING btree (reminder_id);


--
-- Name: ix_rendezvous_clinic_id; Type: INDEX; Schema: public; Owner: sante
--

CREATE INDEX ix_rendezvous_clinic_id ON public.rendezvous USING btree (clinic_id);


--
-- Name: ix_rendezvous_clinical_status; Type: INDEX; Schema: public; Owner: sante
--

CREATE INDEX ix_rendezvous_clinical_status ON public.rendezvous USING btree (clinical_status);


--
-- Name: ix_rendezvous_consultation_type; Type: INDEX; Schema: public; Owner: sante
--

CREATE INDEX ix_rendezvous_consultation_type ON public.rendezvous USING btree (consultation_type);


--
-- Name: ix_rendezvous_created_at; Type: INDEX; Schema: public; Owner: sante
--

CREATE INDEX ix_rendezvous_created_at ON public.rendezvous USING btree (created_at);


--
-- Name: ix_rendezvous_date; Type: INDEX; Schema: public; Owner: sante
--

CREATE INDEX ix_rendezvous_date ON public.rendezvous USING btree (date);


--
-- Name: ix_rendezvous_doctor_id; Type: INDEX; Schema: public; Owner: sante
--

CREATE INDEX ix_rendezvous_doctor_id ON public.rendezvous USING btree (doctor_id);


--
-- Name: ix_rendezvous_id; Type: INDEX; Schema: public; Owner: sante
--

CREATE INDEX ix_rendezvous_id ON public.rendezvous USING btree (id);


--
-- Name: ix_rendezvous_patient_id; Type: INDEX; Schema: public; Owner: sante
--

CREATE INDEX ix_rendezvous_patient_id ON public.rendezvous USING btree (patient_id);


--
-- Name: ix_rendezvous_payment_intent_id; Type: INDEX; Schema: public; Owner: sante
--

CREATE INDEX ix_rendezvous_payment_intent_id ON public.rendezvous USING btree (payment_intent_id);


--
-- Name: ix_rendezvous_payment_status; Type: INDEX; Schema: public; Owner: sante
--

CREATE INDEX ix_rendezvous_payment_status ON public.rendezvous USING btree (payment_status);


--
-- Name: ix_rendezvous_status; Type: INDEX; Schema: public; Owner: sante
--

CREATE INDEX ix_rendezvous_status ON public.rendezvous USING btree (status);


--
-- Name: ix_sync_conflicts_clinic_id; Type: INDEX; Schema: public; Owner: sante
--

CREATE INDEX ix_sync_conflicts_clinic_id ON public.sync_conflicts USING btree (clinic_id);


--
-- Name: ix_sync_conflicts_id; Type: INDEX; Schema: public; Owner: sante
--

CREATE INDEX ix_sync_conflicts_id ON public.sync_conflicts USING btree (id);


--
-- Name: ix_sync_outbox_events_clinic_id; Type: INDEX; Schema: public; Owner: sante
--

CREATE INDEX ix_sync_outbox_events_clinic_id ON public.sync_outbox_events USING btree (clinic_id);


--
-- Name: ix_sync_outbox_events_entity_type; Type: INDEX; Schema: public; Owner: sante
--

CREATE INDEX ix_sync_outbox_events_entity_type ON public.sync_outbox_events USING btree (entity_type);


--
-- Name: ix_sync_outbox_events_entity_uid; Type: INDEX; Schema: public; Owner: sante
--

CREATE INDEX ix_sync_outbox_events_entity_uid ON public.sync_outbox_events USING btree (entity_uid);


--
-- Name: ix_sync_outbox_events_event_id; Type: INDEX; Schema: public; Owner: sante
--

CREATE INDEX ix_sync_outbox_events_event_id ON public.sync_outbox_events USING btree (event_id);


--
-- Name: ix_sync_outbox_events_id; Type: INDEX; Schema: public; Owner: sante
--

CREATE INDEX ix_sync_outbox_events_id ON public.sync_outbox_events USING btree (id);


--
-- Name: ix_sync_outbox_events_node_id; Type: INDEX; Schema: public; Owner: sante
--

CREATE INDEX ix_sync_outbox_events_node_id ON public.sync_outbox_events USING btree (node_id);


--
-- Name: ix_users_clinic_id; Type: INDEX; Schema: public; Owner: sante
--

CREATE INDEX ix_users_clinic_id ON public.users USING btree (clinic_id);


--
-- Name: ix_users_email; Type: INDEX; Schema: public; Owner: sante
--

CREATE UNIQUE INDEX ix_users_email ON public.users USING btree (email);


--
-- Name: ix_users_id; Type: INDEX; Schema: public; Owner: sante
--

CREATE INDEX ix_users_id ON public.users USING btree (id);


--
-- Name: ix_vaccine_schedule_items_id; Type: INDEX; Schema: public; Owner: sante
--

CREATE INDEX ix_vaccine_schedule_items_id ON public.vaccine_schedule_items USING btree (id);


--
-- Name: ix_vaccine_schedule_items_vaccine_code; Type: INDEX; Schema: public; Owner: sante
--

CREATE INDEX ix_vaccine_schedule_items_vaccine_code ON public.vaccine_schedule_items USING btree (vaccine_code);


--
-- Name: admissions admissions_admitted_by_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: sante
--

ALTER TABLE ONLY public.admissions
    ADD CONSTRAINT admissions_admitted_by_user_id_fkey FOREIGN KEY (admitted_by_user_id) REFERENCES public.users(id);


--
-- Name: admissions admissions_attending_clinician_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: sante
--

ALTER TABLE ONLY public.admissions
    ADD CONSTRAINT admissions_attending_clinician_user_id_fkey FOREIGN KEY (attending_clinician_user_id) REFERENCES public.users(id);


--
-- Name: admissions admissions_clinic_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: sante
--

ALTER TABLE ONLY public.admissions
    ADD CONSTRAINT admissions_clinic_id_fkey FOREIGN KEY (clinic_id) REFERENCES public.clinics(id);


--
-- Name: admissions admissions_consultation_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: sante
--

ALTER TABLE ONLY public.admissions
    ADD CONSTRAINT admissions_consultation_id_fkey FOREIGN KEY (consultation_id) REFERENCES public.consultations(id);


--
-- Name: admissions admissions_patient_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: sante
--

ALTER TABLE ONLY public.admissions
    ADD CONSTRAINT admissions_patient_id_fkey FOREIGN KEY (patient_id) REFERENCES public.patients(id);


--
-- Name: appointment_reminders appointment_reminders_appointment_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: sante
--

ALTER TABLE ONLY public.appointment_reminders
    ADD CONSTRAINT appointment_reminders_appointment_id_fkey FOREIGN KEY (appointment_id) REFERENCES public.rendezvous(id);


--
-- Name: appointment_reminders appointment_reminders_patient_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: sante
--

ALTER TABLE ONLY public.appointment_reminders
    ADD CONSTRAINT appointment_reminders_patient_id_fkey FOREIGN KEY (patient_id) REFERENCES public.patients(id);


--
-- Name: attachment_access_logs attachment_access_logs_appointment_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: sante
--

ALTER TABLE ONLY public.attachment_access_logs
    ADD CONSTRAINT attachment_access_logs_appointment_id_fkey FOREIGN KEY (appointment_id) REFERENCES public.rendezvous(id);


--
-- Name: attachment_access_logs attachment_access_logs_message_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: sante
--

ALTER TABLE ONLY public.attachment_access_logs
    ADD CONSTRAINT attachment_access_logs_message_id_fkey FOREIGN KEY (message_id) REFERENCES public.messages(id);


--
-- Name: attachment_access_logs attachment_access_logs_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: sante
--

ALTER TABLE ONLY public.attachment_access_logs
    ADD CONSTRAINT attachment_access_logs_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id);


--
-- Name: clinic_charge_payments clinic_charge_payments_charge_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: sante
--

ALTER TABLE ONLY public.clinic_charge_payments
    ADD CONSTRAINT clinic_charge_payments_charge_id_fkey FOREIGN KEY (charge_id) REFERENCES public.clinic_charges(id);


--
-- Name: clinic_charge_payments clinic_charge_payments_recorded_by_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: sante
--

ALTER TABLE ONLY public.clinic_charge_payments
    ADD CONSTRAINT clinic_charge_payments_recorded_by_user_id_fkey FOREIGN KEY (recorded_by_user_id) REFERENCES public.users(id);


--
-- Name: clinic_charges clinic_charges_clinic_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: sante
--

ALTER TABLE ONLY public.clinic_charges
    ADD CONSTRAINT clinic_charges_clinic_id_fkey FOREIGN KEY (clinic_id) REFERENCES public.clinics(id);


--
-- Name: clinic_charges clinic_charges_invoice_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: sante
--

ALTER TABLE ONLY public.clinic_charges
    ADD CONSTRAINT clinic_charges_invoice_id_fkey FOREIGN KEY (invoice_id) REFERENCES public.invoices(id);


--
-- Name: clinic_charges clinic_charges_patient_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: sante
--

ALTER TABLE ONLY public.clinic_charges
    ADD CONSTRAINT clinic_charges_patient_id_fkey FOREIGN KEY (patient_id) REFERENCES public.patients(id);


--
-- Name: clinic_charges clinic_charges_recorded_by_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: sante
--

ALTER TABLE ONLY public.clinic_charges
    ADD CONSTRAINT clinic_charges_recorded_by_user_id_fkey FOREIGN KEY (recorded_by_user_id) REFERENCES public.users(id);


--
-- Name: clinic_charges clinic_charges_visit_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: sante
--

ALTER TABLE ONLY public.clinic_charges
    ADD CONSTRAINT clinic_charges_visit_id_fkey FOREIGN KEY (visit_id) REFERENCES public.clinical_visits(id);


--
-- Name: clinic_lab_tests clinic_lab_tests_clinic_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: sante
--

ALTER TABLE ONLY public.clinic_lab_tests
    ADD CONSTRAINT clinic_lab_tests_clinic_id_fkey FOREIGN KEY (clinic_id) REFERENCES public.clinics(id);


--
-- Name: clinic_refunds clinic_refunds_approved_by_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: sante
--

ALTER TABLE ONLY public.clinic_refunds
    ADD CONSTRAINT clinic_refunds_approved_by_user_id_fkey FOREIGN KEY (approved_by_user_id) REFERENCES public.users(id);


--
-- Name: clinic_refunds clinic_refunds_clinic_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: sante
--

ALTER TABLE ONLY public.clinic_refunds
    ADD CONSTRAINT clinic_refunds_clinic_id_fkey FOREIGN KEY (clinic_id) REFERENCES public.clinics(id);


--
-- Name: clinic_refunds clinic_refunds_created_by_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: sante
--

ALTER TABLE ONLY public.clinic_refunds
    ADD CONSTRAINT clinic_refunds_created_by_user_id_fkey FOREIGN KEY (created_by_user_id) REFERENCES public.users(id);


--
-- Name: clinic_refunds clinic_refunds_invoice_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: sante
--

ALTER TABLE ONLY public.clinic_refunds
    ADD CONSTRAINT clinic_refunds_invoice_id_fkey FOREIGN KEY (invoice_id) REFERENCES public.invoices(id);


--
-- Name: clinic_refunds clinic_refunds_paid_by_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: sante
--

ALTER TABLE ONLY public.clinic_refunds
    ADD CONSTRAINT clinic_refunds_paid_by_user_id_fkey FOREIGN KEY (paid_by_user_id) REFERENCES public.users(id);


--
-- Name: clinic_refunds clinic_refunds_patient_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: sante
--

ALTER TABLE ONLY public.clinic_refunds
    ADD CONSTRAINT clinic_refunds_patient_id_fkey FOREIGN KEY (patient_id) REFERENCES public.patients(id);


--
-- Name: clinic_service_requests clinic_service_requests_admission_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: sante
--

ALTER TABLE ONLY public.clinic_service_requests
    ADD CONSTRAINT clinic_service_requests_admission_id_fkey FOREIGN KEY (admission_id) REFERENCES public.admissions(id);


--
-- Name: clinic_service_requests clinic_service_requests_clinic_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: sante
--

ALTER TABLE ONLY public.clinic_service_requests
    ADD CONSTRAINT clinic_service_requests_clinic_id_fkey FOREIGN KEY (clinic_id) REFERENCES public.clinics(id);


--
-- Name: clinic_service_requests clinic_service_requests_created_by_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: sante
--

ALTER TABLE ONLY public.clinic_service_requests
    ADD CONSTRAINT clinic_service_requests_created_by_user_id_fkey FOREIGN KEY (created_by_user_id) REFERENCES public.users(id);


--
-- Name: clinic_service_requests clinic_service_requests_patient_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: sante
--

ALTER TABLE ONLY public.clinic_service_requests
    ADD CONSTRAINT clinic_service_requests_patient_id_fkey FOREIGN KEY (patient_id) REFERENCES public.patients(id);


--
-- Name: clinic_service_requests clinic_service_requests_updated_by_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: sante
--

ALTER TABLE ONLY public.clinic_service_requests
    ADD CONSTRAINT clinic_service_requests_updated_by_user_id_fkey FOREIGN KEY (updated_by_user_id) REFERENCES public.users(id);


--
-- Name: clinic_staff clinic_staff_clinic_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: sante
--

ALTER TABLE ONLY public.clinic_staff
    ADD CONSTRAINT clinic_staff_clinic_id_fkey FOREIGN KEY (clinic_id) REFERENCES public.clinics(id);


--
-- Name: clinic_staff clinic_staff_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: sante
--

ALTER TABLE ONLY public.clinic_staff
    ADD CONSTRAINT clinic_staff_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id);


--
-- Name: clinical_audit_logs clinical_audit_logs_actor_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: sante
--

ALTER TABLE ONLY public.clinical_audit_logs
    ADD CONSTRAINT clinical_audit_logs_actor_id_fkey FOREIGN KEY (actor_id) REFERENCES public.users(id);


--
-- Name: clinical_audit_logs clinical_audit_logs_clinic_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: sante
--

ALTER TABLE ONLY public.clinical_audit_logs
    ADD CONSTRAINT clinical_audit_logs_clinic_id_fkey FOREIGN KEY (clinic_id) REFERENCES public.clinics(id);


--
-- Name: clinical_audit_logs clinical_audit_logs_patient_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: sante
--

ALTER TABLE ONLY public.clinical_audit_logs
    ADD CONSTRAINT clinical_audit_logs_patient_id_fkey FOREIGN KEY (patient_id) REFERENCES public.patients(id);


--
-- Name: clinical_notes clinical_notes_appointment_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: sante
--

ALTER TABLE ONLY public.clinical_notes
    ADD CONSTRAINT clinical_notes_appointment_id_fkey FOREIGN KEY (appointment_id) REFERENCES public.rendezvous(id);


--
-- Name: clinical_notes clinical_notes_doctor_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: sante
--

ALTER TABLE ONLY public.clinical_notes
    ADD CONSTRAINT clinical_notes_doctor_id_fkey FOREIGN KEY (doctor_id) REFERENCES public.doctors(id);


--
-- Name: clinical_notes clinical_notes_patient_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: sante
--

ALTER TABLE ONLY public.clinical_notes
    ADD CONSTRAINT clinical_notes_patient_id_fkey FOREIGN KEY (patient_id) REFERENCES public.patients(id);


--
-- Name: clinical_visits clinical_visits_admission_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: sante
--

ALTER TABLE ONLY public.clinical_visits
    ADD CONSTRAINT clinical_visits_admission_id_fkey FOREIGN KEY (admission_id) REFERENCES public.admissions(id);


--
-- Name: clinical_visits clinical_visits_appointment_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: sante
--

ALTER TABLE ONLY public.clinical_visits
    ADD CONSTRAINT clinical_visits_appointment_id_fkey FOREIGN KEY (appointment_id) REFERENCES public.rendezvous(id);


--
-- Name: clinical_visits clinical_visits_clinic_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: sante
--

ALTER TABLE ONLY public.clinical_visits
    ADD CONSTRAINT clinical_visits_clinic_id_fkey FOREIGN KEY (clinic_id) REFERENCES public.clinics(id);


--
-- Name: clinical_visits clinical_visits_consultation_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: sante
--

ALTER TABLE ONLY public.clinical_visits
    ADD CONSTRAINT clinical_visits_consultation_id_fkey FOREIGN KEY (consultation_id) REFERENCES public.consultations(id);


--
-- Name: clinical_visits clinical_visits_patient_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: sante
--

ALTER TABLE ONLY public.clinical_visits
    ADD CONSTRAINT clinical_visits_patient_id_fkey FOREIGN KEY (patient_id) REFERENCES public.patients(id);


--
-- Name: consultation_summaries consultation_summaries_appointment_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: sante
--

ALTER TABLE ONLY public.consultation_summaries
    ADD CONSTRAINT consultation_summaries_appointment_id_fkey FOREIGN KEY (appointment_id) REFERENCES public.rendezvous(id);


--
-- Name: consultation_summaries consultation_summaries_doctor_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: sante
--

ALTER TABLE ONLY public.consultation_summaries
    ADD CONSTRAINT consultation_summaries_doctor_id_fkey FOREIGN KEY (doctor_id) REFERENCES public.doctors(id);


--
-- Name: consultation_summaries consultation_summaries_patient_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: sante
--

ALTER TABLE ONLY public.consultation_summaries
    ADD CONSTRAINT consultation_summaries_patient_id_fkey FOREIGN KEY (patient_id) REFERENCES public.patients(id);


--
-- Name: consultations consultations_appointment_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: sante
--

ALTER TABLE ONLY public.consultations
    ADD CONSTRAINT consultations_appointment_id_fkey FOREIGN KEY (appointment_id) REFERENCES public.rendezvous(id);


--
-- Name: consultations consultations_clinic_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: sante
--

ALTER TABLE ONLY public.consultations
    ADD CONSTRAINT consultations_clinic_id_fkey FOREIGN KEY (clinic_id) REFERENCES public.clinics(id);


--
-- Name: consultations consultations_doctor_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: sante
--

ALTER TABLE ONLY public.consultations
    ADD CONSTRAINT consultations_doctor_id_fkey FOREIGN KEY (doctor_id) REFERENCES public.doctors(id);


--
-- Name: consultations consultations_patient_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: sante
--

ALTER TABLE ONLY public.consultations
    ADD CONSTRAINT consultations_patient_id_fkey FOREIGN KEY (patient_id) REFERENCES public.patients(id);


--
-- Name: discharge_summaries discharge_summaries_admission_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: sante
--

ALTER TABLE ONLY public.discharge_summaries
    ADD CONSTRAINT discharge_summaries_admission_id_fkey FOREIGN KEY (admission_id) REFERENCES public.admissions(id);


--
-- Name: discharge_summaries discharge_summaries_clinic_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: sante
--

ALTER TABLE ONLY public.discharge_summaries
    ADD CONSTRAINT discharge_summaries_clinic_id_fkey FOREIGN KEY (clinic_id) REFERENCES public.clinics(id);


--
-- Name: discharge_summaries discharge_summaries_consultation_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: sante
--

ALTER TABLE ONLY public.discharge_summaries
    ADD CONSTRAINT discharge_summaries_consultation_id_fkey FOREIGN KEY (consultation_id) REFERENCES public.consultations(id);


--
-- Name: discharge_summaries discharge_summaries_discharged_by_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: sante
--

ALTER TABLE ONLY public.discharge_summaries
    ADD CONSTRAINT discharge_summaries_discharged_by_user_id_fkey FOREIGN KEY (discharged_by_user_id) REFERENCES public.users(id);


--
-- Name: discharge_summaries discharge_summaries_invoice_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: sante
--

ALTER TABLE ONLY public.discharge_summaries
    ADD CONSTRAINT discharge_summaries_invoice_id_fkey FOREIGN KEY (invoice_id) REFERENCES public.invoices(id);


--
-- Name: discharge_summaries discharge_summaries_patient_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: sante
--

ALTER TABLE ONLY public.discharge_summaries
    ADD CONSTRAINT discharge_summaries_patient_id_fkey FOREIGN KEY (patient_id) REFERENCES public.patients(id);


--
-- Name: discharge_summaries discharge_summaries_visit_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: sante
--

ALTER TABLE ONLY public.discharge_summaries
    ADD CONSTRAINT discharge_summaries_visit_id_fkey FOREIGN KEY (visit_id) REFERENCES public.clinical_visits(id);


--
-- Name: doctor_availabilities doctor_availabilities_doctor_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: sante
--

ALTER TABLE ONLY public.doctor_availabilities
    ADD CONSTRAINT doctor_availabilities_doctor_id_fkey FOREIGN KEY (doctor_id) REFERENCES public.doctors(id);


--
-- Name: doctor_medicine_deliveries doctor_medicine_deliveries_clinic_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: sante
--

ALTER TABLE ONLY public.doctor_medicine_deliveries
    ADD CONSTRAINT doctor_medicine_deliveries_clinic_id_fkey FOREIGN KEY (clinic_id) REFERENCES public.clinics(id);


--
-- Name: doctor_medicine_deliveries doctor_medicine_deliveries_patient_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: sante
--

ALTER TABLE ONLY public.doctor_medicine_deliveries
    ADD CONSTRAINT doctor_medicine_deliveries_patient_id_fkey FOREIGN KEY (patient_id) REFERENCES public.patients(id);


--
-- Name: doctor_medicine_deliveries doctor_medicine_deliveries_recorded_by_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: sante
--

ALTER TABLE ONLY public.doctor_medicine_deliveries
    ADD CONSTRAINT doctor_medicine_deliveries_recorded_by_user_id_fkey FOREIGN KEY (recorded_by_user_id) REFERENCES public.users(id);


--
-- Name: doctors doctors_clinic_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: sante
--

ALTER TABLE ONLY public.doctors
    ADD CONSTRAINT doctors_clinic_id_fkey FOREIGN KEY (clinic_id) REFERENCES public.clinics(id);


--
-- Name: doctors doctors_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: sante
--

ALTER TABLE ONLY public.doctors
    ADD CONSTRAINT doctors_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id);


--
-- Name: email_verification_tokens email_verification_tokens_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: sante
--

ALTER TABLE ONLY public.email_verification_tokens
    ADD CONSTRAINT email_verification_tokens_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id);


--
-- Name: follow_up_schedules follow_up_schedules_clinic_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: sante
--

ALTER TABLE ONLY public.follow_up_schedules
    ADD CONSTRAINT follow_up_schedules_clinic_id_fkey FOREIGN KEY (clinic_id) REFERENCES public.clinics(id);


--
-- Name: follow_up_schedules follow_up_schedules_consultation_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: sante
--

ALTER TABLE ONLY public.follow_up_schedules
    ADD CONSTRAINT follow_up_schedules_consultation_id_fkey FOREIGN KEY (consultation_id) REFERENCES public.consultations(id);


--
-- Name: follow_up_schedules follow_up_schedules_created_by_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: sante
--

ALTER TABLE ONLY public.follow_up_schedules
    ADD CONSTRAINT follow_up_schedules_created_by_user_id_fkey FOREIGN KEY (created_by_user_id) REFERENCES public.users(id);


--
-- Name: follow_up_schedules follow_up_schedules_doctor_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: sante
--

ALTER TABLE ONLY public.follow_up_schedules
    ADD CONSTRAINT follow_up_schedules_doctor_id_fkey FOREIGN KEY (doctor_id) REFERENCES public.doctors(id);


--
-- Name: follow_up_schedules follow_up_schedules_follow_up_appointment_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: sante
--

ALTER TABLE ONLY public.follow_up_schedules
    ADD CONSTRAINT follow_up_schedules_follow_up_appointment_id_fkey FOREIGN KEY (follow_up_appointment_id) REFERENCES public.rendezvous(id);


--
-- Name: follow_up_schedules follow_up_schedules_patient_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: sante
--

ALTER TABLE ONLY public.follow_up_schedules
    ADD CONSTRAINT follow_up_schedules_patient_id_fkey FOREIGN KEY (patient_id) REFERENCES public.patients(id);


--
-- Name: hospital_beds hospital_beds_room_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: sante
--

ALTER TABLE ONLY public.hospital_beds
    ADD CONSTRAINT hospital_beds_room_id_fkey FOREIGN KEY (room_id) REFERENCES public.hospital_rooms(id);


--
-- Name: hospital_rooms hospital_rooms_clinic_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: sante
--

ALTER TABLE ONLY public.hospital_rooms
    ADD CONSTRAINT hospital_rooms_clinic_id_fkey FOREIGN KEY (clinic_id) REFERENCES public.clinics(id);


--
-- Name: imaging_orders imaging_orders_clinic_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: sante
--

ALTER TABLE ONLY public.imaging_orders
    ADD CONSTRAINT imaging_orders_clinic_id_fkey FOREIGN KEY (clinic_id) REFERENCES public.clinics(id);


--
-- Name: imaging_orders imaging_orders_consultation_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: sante
--

ALTER TABLE ONLY public.imaging_orders
    ADD CONSTRAINT imaging_orders_consultation_id_fkey FOREIGN KEY (consultation_id) REFERENCES public.consultations(id);


--
-- Name: imaging_orders imaging_orders_ordered_by_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: sante
--

ALTER TABLE ONLY public.imaging_orders
    ADD CONSTRAINT imaging_orders_ordered_by_user_id_fkey FOREIGN KEY (ordered_by_user_id) REFERENCES public.users(id);


--
-- Name: imaging_orders imaging_orders_patient_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: sante
--

ALTER TABLE ONLY public.imaging_orders
    ADD CONSTRAINT imaging_orders_patient_id_fkey FOREIGN KEY (patient_id) REFERENCES public.patients(id);


--
-- Name: imaging_results imaging_results_order_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: sante
--

ALTER TABLE ONLY public.imaging_results
    ADD CONSTRAINT imaging_results_order_id_fkey FOREIGN KEY (order_id) REFERENCES public.imaging_orders(id);


--
-- Name: imaging_results imaging_results_reported_by_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: sante
--

ALTER TABLE ONLY public.imaging_results
    ADD CONSTRAINT imaging_results_reported_by_user_id_fkey FOREIGN KEY (reported_by_user_id) REFERENCES public.users(id);


--
-- Name: imaging_results imaging_results_validated_by_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: sante
--

ALTER TABLE ONLY public.imaging_results
    ADD CONSTRAINT imaging_results_validated_by_user_id_fkey FOREIGN KEY (validated_by_user_id) REFERENCES public.users(id);


--
-- Name: immunization_records immunization_records_administered_by_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: sante
--

ALTER TABLE ONLY public.immunization_records
    ADD CONSTRAINT immunization_records_administered_by_user_id_fkey FOREIGN KEY (administered_by_user_id) REFERENCES public.users(id);


--
-- Name: immunization_records immunization_records_clinic_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: sante
--

ALTER TABLE ONLY public.immunization_records
    ADD CONSTRAINT immunization_records_clinic_id_fkey FOREIGN KEY (clinic_id) REFERENCES public.clinics(id);


--
-- Name: immunization_records immunization_records_patient_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: sante
--

ALTER TABLE ONLY public.immunization_records
    ADD CONSTRAINT immunization_records_patient_id_fkey FOREIGN KEY (patient_id) REFERENCES public.patients(id);


--
-- Name: invoice_items invoice_items_clinic_charge_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: sante
--

ALTER TABLE ONLY public.invoice_items
    ADD CONSTRAINT invoice_items_clinic_charge_id_fkey FOREIGN KEY (clinic_charge_id) REFERENCES public.clinic_charges(id);


--
-- Name: invoice_items invoice_items_invoice_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: sante
--

ALTER TABLE ONLY public.invoice_items
    ADD CONSTRAINT invoice_items_invoice_id_fkey FOREIGN KEY (invoice_id) REFERENCES public.invoices(id);


--
-- Name: invoices invoices_clinic_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: sante
--

ALTER TABLE ONLY public.invoices
    ADD CONSTRAINT invoices_clinic_id_fkey FOREIGN KEY (clinic_id) REFERENCES public.clinics(id);


--
-- Name: invoices invoices_created_by_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: sante
--

ALTER TABLE ONLY public.invoices
    ADD CONSTRAINT invoices_created_by_user_id_fkey FOREIGN KEY (created_by_user_id) REFERENCES public.users(id);


--
-- Name: invoices invoices_patient_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: sante
--

ALTER TABLE ONLY public.invoices
    ADD CONSTRAINT invoices_patient_id_fkey FOREIGN KEY (patient_id) REFERENCES public.patients(id);


--
-- Name: invoices invoices_visit_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: sante
--

ALTER TABLE ONLY public.invoices
    ADD CONSTRAINT invoices_visit_id_fkey FOREIGN KEY (visit_id) REFERENCES public.clinical_visits(id);


--
-- Name: lab_orders lab_orders_clinic_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: sante
--

ALTER TABLE ONLY public.lab_orders
    ADD CONSTRAINT lab_orders_clinic_id_fkey FOREIGN KEY (clinic_id) REFERENCES public.clinics(id);


--
-- Name: lab_orders lab_orders_consultation_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: sante
--

ALTER TABLE ONLY public.lab_orders
    ADD CONSTRAINT lab_orders_consultation_id_fkey FOREIGN KEY (consultation_id) REFERENCES public.consultations(id);


--
-- Name: lab_orders lab_orders_doctor_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: sante
--

ALTER TABLE ONLY public.lab_orders
    ADD CONSTRAINT lab_orders_doctor_id_fkey FOREIGN KEY (doctor_id) REFERENCES public.doctors(id);


--
-- Name: lab_orders lab_orders_ordered_by_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: sante
--

ALTER TABLE ONLY public.lab_orders
    ADD CONSTRAINT lab_orders_ordered_by_user_id_fkey FOREIGN KEY (ordered_by_user_id) REFERENCES public.users(id);


--
-- Name: lab_orders lab_orders_patient_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: sante
--

ALTER TABLE ONLY public.lab_orders
    ADD CONSTRAINT lab_orders_patient_id_fkey FOREIGN KEY (patient_id) REFERENCES public.patients(id);


--
-- Name: lab_results lab_results_lab_order_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: sante
--

ALTER TABLE ONLY public.lab_results
    ADD CONSTRAINT lab_results_lab_order_id_fkey FOREIGN KEY (lab_order_id) REFERENCES public.lab_orders(id);


--
-- Name: lab_results lab_results_recorded_by_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: sante
--

ALTER TABLE ONLY public.lab_results
    ADD CONSTRAINT lab_results_recorded_by_user_id_fkey FOREIGN KEY (recorded_by_user_id) REFERENCES public.users(id);


--
-- Name: lab_results lab_results_validated_by_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: sante
--

ALTER TABLE ONLY public.lab_results
    ADD CONSTRAINT lab_results_validated_by_user_id_fkey FOREIGN KEY (validated_by_user_id) REFERENCES public.users(id);


--
-- Name: messages messages_appointment_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: sante
--

ALTER TABLE ONLY public.messages
    ADD CONSTRAINT messages_appointment_id_fkey FOREIGN KEY (appointment_id) REFERENCES public.rendezvous(id);


--
-- Name: messages messages_sender_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: sante
--

ALTER TABLE ONLY public.messages
    ADD CONSTRAINT messages_sender_user_id_fkey FOREIGN KEY (sender_user_id) REFERENCES public.users(id);


--
-- Name: notification_events notification_events_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: sante
--

ALTER TABLE ONLY public.notification_events
    ADD CONSTRAINT notification_events_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id);


--
-- Name: nurse_assessments nurse_assessments_admission_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: sante
--

ALTER TABLE ONLY public.nurse_assessments
    ADD CONSTRAINT nurse_assessments_admission_id_fkey FOREIGN KEY (admission_id) REFERENCES public.admissions(id);


--
-- Name: nurse_assessments nurse_assessments_appointment_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: sante
--

ALTER TABLE ONLY public.nurse_assessments
    ADD CONSTRAINT nurse_assessments_appointment_id_fkey FOREIGN KEY (appointment_id) REFERENCES public.rendezvous(id);


--
-- Name: nurse_assessments nurse_assessments_clinic_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: sante
--

ALTER TABLE ONLY public.nurse_assessments
    ADD CONSTRAINT nurse_assessments_clinic_id_fkey FOREIGN KEY (clinic_id) REFERENCES public.clinics(id);


--
-- Name: nurse_assessments nurse_assessments_consultation_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: sante
--

ALTER TABLE ONLY public.nurse_assessments
    ADD CONSTRAINT nurse_assessments_consultation_id_fkey FOREIGN KEY (consultation_id) REFERENCES public.consultations(id);


--
-- Name: nurse_assessments nurse_assessments_nurse_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: sante
--

ALTER TABLE ONLY public.nurse_assessments
    ADD CONSTRAINT nurse_assessments_nurse_user_id_fkey FOREIGN KEY (nurse_user_id) REFERENCES public.users(id);


--
-- Name: nurse_assessments nurse_assessments_patient_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: sante
--

ALTER TABLE ONLY public.nurse_assessments
    ADD CONSTRAINT nurse_assessments_patient_id_fkey FOREIGN KEY (patient_id) REFERENCES public.patients(id);


--
-- Name: nursing_procedures nursing_procedures_clinic_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: sante
--

ALTER TABLE ONLY public.nursing_procedures
    ADD CONSTRAINT nursing_procedures_clinic_id_fkey FOREIGN KEY (clinic_id) REFERENCES public.clinics(id);


--
-- Name: nursing_procedures nursing_procedures_nurse_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: sante
--

ALTER TABLE ONLY public.nursing_procedures
    ADD CONSTRAINT nursing_procedures_nurse_user_id_fkey FOREIGN KEY (nurse_user_id) REFERENCES public.users(id);


--
-- Name: nursing_procedures nursing_procedures_patient_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: sante
--

ALTER TABLE ONLY public.nursing_procedures
    ADD CONSTRAINT nursing_procedures_patient_id_fkey FOREIGN KEY (patient_id) REFERENCES public.patients(id);


--
-- Name: nutrition_assessments nutrition_assessments_clinic_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: sante
--

ALTER TABLE ONLY public.nutrition_assessments
    ADD CONSTRAINT nutrition_assessments_clinic_id_fkey FOREIGN KEY (clinic_id) REFERENCES public.clinics(id);


--
-- Name: nutrition_assessments nutrition_assessments_consultation_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: sante
--

ALTER TABLE ONLY public.nutrition_assessments
    ADD CONSTRAINT nutrition_assessments_consultation_id_fkey FOREIGN KEY (consultation_id) REFERENCES public.consultations(id);


--
-- Name: nutrition_assessments nutrition_assessments_patient_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: sante
--

ALTER TABLE ONLY public.nutrition_assessments
    ADD CONSTRAINT nutrition_assessments_patient_id_fkey FOREIGN KEY (patient_id) REFERENCES public.patients(id);


--
-- Name: nutrition_assessments nutrition_assessments_recorded_by_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: sante
--

ALTER TABLE ONLY public.nutrition_assessments
    ADD CONSTRAINT nutrition_assessments_recorded_by_user_id_fkey FOREIGN KEY (recorded_by_user_id) REFERENCES public.users(id);


--
-- Name: password_reset_tokens password_reset_tokens_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: sante
--

ALTER TABLE ONLY public.password_reset_tokens
    ADD CONSTRAINT password_reset_tokens_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id);


--
-- Name: patient_allergies patient_allergies_patient_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: sante
--

ALTER TABLE ONLY public.patient_allergies
    ADD CONSTRAINT patient_allergies_patient_id_fkey FOREIGN KEY (patient_id) REFERENCES public.patients(id);


--
-- Name: patient_allergies patient_allergies_recorded_by_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: sante
--

ALTER TABLE ONLY public.patient_allergies
    ADD CONSTRAINT patient_allergies_recorded_by_user_id_fkey FOREIGN KEY (recorded_by_user_id) REFERENCES public.users(id);


--
-- Name: patient_chronic_conditions patient_chronic_conditions_patient_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: sante
--

ALTER TABLE ONLY public.patient_chronic_conditions
    ADD CONSTRAINT patient_chronic_conditions_patient_id_fkey FOREIGN KEY (patient_id) REFERENCES public.patients(id);


--
-- Name: patient_chronic_conditions patient_chronic_conditions_recorded_by_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: sante
--

ALTER TABLE ONLY public.patient_chronic_conditions
    ADD CONSTRAINT patient_chronic_conditions_recorded_by_user_id_fkey FOREIGN KEY (recorded_by_user_id) REFERENCES public.users(id);


--
-- Name: patient_documents patient_documents_patient_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: sante
--

ALTER TABLE ONLY public.patient_documents
    ADD CONSTRAINT patient_documents_patient_id_fkey FOREIGN KEY (patient_id) REFERENCES public.patients(id);


--
-- Name: patient_documents patient_documents_uploaded_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: sante
--

ALTER TABLE ONLY public.patient_documents
    ADD CONSTRAINT patient_documents_uploaded_by_fkey FOREIGN KEY (uploaded_by) REFERENCES public.users(id);


--
-- Name: patient_medical_records patient_medical_records_patient_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: sante
--

ALTER TABLE ONLY public.patient_medical_records
    ADD CONSTRAINT patient_medical_records_patient_id_fkey FOREIGN KEY (patient_id) REFERENCES public.patients(id);


--
-- Name: patient_stays patient_stays_admission_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: sante
--

ALTER TABLE ONLY public.patient_stays
    ADD CONSTRAINT patient_stays_admission_id_fkey FOREIGN KEY (admission_id) REFERENCES public.admissions(id);


--
-- Name: patient_stays patient_stays_assigned_by_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: sante
--

ALTER TABLE ONLY public.patient_stays
    ADD CONSTRAINT patient_stays_assigned_by_user_id_fkey FOREIGN KEY (assigned_by_user_id) REFERENCES public.users(id);


--
-- Name: patient_stays patient_stays_bed_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: sante
--

ALTER TABLE ONLY public.patient_stays
    ADD CONSTRAINT patient_stays_bed_id_fkey FOREIGN KEY (bed_id) REFERENCES public.hospital_beds(id);


--
-- Name: patient_visit_workflow_steps patient_visit_workflow_steps_completed_by_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: sante
--

ALTER TABLE ONLY public.patient_visit_workflow_steps
    ADD CONSTRAINT patient_visit_workflow_steps_completed_by_user_id_fkey FOREIGN KEY (completed_by_user_id) REFERENCES public.users(id);


--
-- Name: patient_visit_workflow_steps patient_visit_workflow_steps_workflow_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: sante
--

ALTER TABLE ONLY public.patient_visit_workflow_steps
    ADD CONSTRAINT patient_visit_workflow_steps_workflow_id_fkey FOREIGN KEY (workflow_id) REFERENCES public.patient_visit_workflows(id);


--
-- Name: patient_visit_workflows patient_visit_workflows_clinic_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: sante
--

ALTER TABLE ONLY public.patient_visit_workflows
    ADD CONSTRAINT patient_visit_workflows_clinic_id_fkey FOREIGN KEY (clinic_id) REFERENCES public.clinics(id);


--
-- Name: patient_visit_workflows patient_visit_workflows_clinical_visit_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: sante
--

ALTER TABLE ONLY public.patient_visit_workflows
    ADD CONSTRAINT patient_visit_workflows_clinical_visit_id_fkey FOREIGN KEY (clinical_visit_id) REFERENCES public.clinical_visits(id);


--
-- Name: patient_visit_workflows patient_visit_workflows_created_by_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: sante
--

ALTER TABLE ONLY public.patient_visit_workflows
    ADD CONSTRAINT patient_visit_workflows_created_by_user_id_fkey FOREIGN KEY (created_by_user_id) REFERENCES public.users(id);


--
-- Name: patient_visit_workflows patient_visit_workflows_patient_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: sante
--

ALTER TABLE ONLY public.patient_visit_workflows
    ADD CONSTRAINT patient_visit_workflows_patient_id_fkey FOREIGN KEY (patient_id) REFERENCES public.patients(id);


--
-- Name: patient_vital_signs patient_vital_signs_consultation_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: sante
--

ALTER TABLE ONLY public.patient_vital_signs
    ADD CONSTRAINT patient_vital_signs_consultation_id_fkey FOREIGN KEY (consultation_id) REFERENCES public.consultations(id);


--
-- Name: patient_vital_signs patient_vital_signs_patient_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: sante
--

ALTER TABLE ONLY public.patient_vital_signs
    ADD CONSTRAINT patient_vital_signs_patient_id_fkey FOREIGN KEY (patient_id) REFERENCES public.patients(id);


--
-- Name: patient_vital_signs patient_vital_signs_recorded_by_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: sante
--

ALTER TABLE ONLY public.patient_vital_signs
    ADD CONSTRAINT patient_vital_signs_recorded_by_user_id_fkey FOREIGN KEY (recorded_by_user_id) REFERENCES public.users(id);


--
-- Name: patients patients_clinic_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: sante
--

ALTER TABLE ONLY public.patients
    ADD CONSTRAINT patients_clinic_id_fkey FOREIGN KEY (clinic_id) REFERENCES public.clinics(id);


--
-- Name: patients patients_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: sante
--

ALTER TABLE ONLY public.patients
    ADD CONSTRAINT patients_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id);


--
-- Name: payment_records payment_records_invoice_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: sante
--

ALTER TABLE ONLY public.payment_records
    ADD CONSTRAINT payment_records_invoice_id_fkey FOREIGN KEY (invoice_id) REFERENCES public.invoices(id);


--
-- Name: payment_records payment_records_recorded_by_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: sante
--

ALTER TABLE ONLY public.payment_records
    ADD CONSTRAINT payment_records_recorded_by_user_id_fkey FOREIGN KEY (recorded_by_user_id) REFERENCES public.users(id);


--
-- Name: payments payments_appointment_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: sante
--

ALTER TABLE ONLY public.payments
    ADD CONSTRAINT payments_appointment_id_fkey FOREIGN KEY (appointment_id) REFERENCES public.rendezvous(id);


--
-- Name: pharmacy_inventory pharmacy_inventory_clinic_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: sante
--

ALTER TABLE ONLY public.pharmacy_inventory
    ADD CONSTRAINT pharmacy_inventory_clinic_id_fkey FOREIGN KEY (clinic_id) REFERENCES public.clinics(id);


--
-- Name: pharmacy_orders pharmacy_orders_clinic_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: sante
--

ALTER TABLE ONLY public.pharmacy_orders
    ADD CONSTRAINT pharmacy_orders_clinic_id_fkey FOREIGN KEY (clinic_id) REFERENCES public.clinics(id);


--
-- Name: pharmacy_orders pharmacy_orders_patient_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: sante
--

ALTER TABLE ONLY public.pharmacy_orders
    ADD CONSTRAINT pharmacy_orders_patient_id_fkey FOREIGN KEY (patient_id) REFERENCES public.patients(id);


--
-- Name: pharmacy_orders pharmacy_orders_prepared_by_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: sante
--

ALTER TABLE ONLY public.pharmacy_orders
    ADD CONSTRAINT pharmacy_orders_prepared_by_user_id_fkey FOREIGN KEY (prepared_by_user_id) REFERENCES public.users(id);


--
-- Name: pharmacy_orders pharmacy_orders_prescription_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: sante
--

ALTER TABLE ONLY public.pharmacy_orders
    ADD CONSTRAINT pharmacy_orders_prescription_id_fkey FOREIGN KEY (prescription_id) REFERENCES public.prescriptions(id);


--
-- Name: prescription_items prescription_items_prescription_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: sante
--

ALTER TABLE ONLY public.prescription_items
    ADD CONSTRAINT prescription_items_prescription_id_fkey FOREIGN KEY (prescription_id) REFERENCES public.prescriptions(id);


--
-- Name: prescriptions prescriptions_clinic_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: sante
--

ALTER TABLE ONLY public.prescriptions
    ADD CONSTRAINT prescriptions_clinic_id_fkey FOREIGN KEY (clinic_id) REFERENCES public.clinics(id);


--
-- Name: prescriptions prescriptions_consultation_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: sante
--

ALTER TABLE ONLY public.prescriptions
    ADD CONSTRAINT prescriptions_consultation_id_fkey FOREIGN KEY (consultation_id) REFERENCES public.consultations(id);


--
-- Name: prescriptions prescriptions_patient_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: sante
--

ALTER TABLE ONLY public.prescriptions
    ADD CONSTRAINT prescriptions_patient_id_fkey FOREIGN KEY (patient_id) REFERENCES public.patients(id);


--
-- Name: prescriptions prescriptions_prescriber_doctor_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: sante
--

ALTER TABLE ONLY public.prescriptions
    ADD CONSTRAINT prescriptions_prescriber_doctor_id_fkey FOREIGN KEY (prescriber_doctor_id) REFERENCES public.doctors(id);


--
-- Name: reminder_events reminder_events_reminder_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: sante
--

ALTER TABLE ONLY public.reminder_events
    ADD CONSTRAINT reminder_events_reminder_id_fkey FOREIGN KEY (reminder_id) REFERENCES public.appointment_reminders(id);


--
-- Name: rendezvous rendezvous_clinic_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: sante
--

ALTER TABLE ONLY public.rendezvous
    ADD CONSTRAINT rendezvous_clinic_id_fkey FOREIGN KEY (clinic_id) REFERENCES public.clinics(id);


--
-- Name: rendezvous rendezvous_doctor_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: sante
--

ALTER TABLE ONLY public.rendezvous
    ADD CONSTRAINT rendezvous_doctor_id_fkey FOREIGN KEY (doctor_id) REFERENCES public.doctors(id);


--
-- Name: rendezvous rendezvous_patient_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: sante
--

ALTER TABLE ONLY public.rendezvous
    ADD CONSTRAINT rendezvous_patient_id_fkey FOREIGN KEY (patient_id) REFERENCES public.patients(id);


--
-- PostgreSQL database dump complete
--

\unrestrict jHle7GiIWHCGbkqBgozFtGVp0Zv649fov6glBcjapoSXwShvSNSGB8MUFxglcMw

