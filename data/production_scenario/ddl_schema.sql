--
-- PostgreSQL database dump
--
-- Dumped from database version 15.4
-- Dumped by pg_dump version 15.4
--
-- Sistema: plataforma de telemedicina "SaudeConecta"
-- Ambiente: production (extraído via `pg_dump --schema-only --no-owner saudeconecta_prod`)
-- Gerado em: 2026-08-11 03:12:07 UTC
--

SET statement_timeout = 0;
SET lock_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

CREATE TYPE user_role_enum AS ENUM ('PATIENT', 'DOCTOR', 'SUPPORT', 'ADMIN');
CREATE TYPE appointment_status_enum AS ENUM ('SCHEDULED', 'IN_PROGRESS', 'COMPLETED', 'CANCELLED', 'NO_SHOW');
CREATE TYPE consent_scope_enum AS ENUM ('TERMS_OF_USE', 'MARKETING', 'DATA_SHARING_PARTNERS', 'TELEMETRY');

--
-- Tabela: users
-- Cadastro unificado de pacientes, médicos e equipe interna.
--
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    role user_role_enum NOT NULL DEFAULT 'PATIENT',
    full_name TEXT NOT NULL,
    cpf VARCHAR(11) NOT NULL UNIQUE,
    email CITEXT NOT NULL UNIQUE,
    phone VARCHAR(20),
    password_hash TEXT NOT NULL,
    password_reset_token TEXT,
    birth_date DATE,
    gender VARCHAR(30),
    mother_full_name TEXT,
    marketing_opt_in BOOLEAN NOT NULL DEFAULT false,
    is_active BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    deleted_at TIMESTAMPTZ
);

COMMENT ON COLUMN users.cpf IS 'CPF armazenado em texto plano, sem mascaramento nem tokenização.';
COMMENT ON COLUMN users.mother_full_name IS 'Coletado para validação de identidade no primeiro acesso; sem base legal documentada no termo de tratamento.';

CREATE UNIQUE INDEX idx_users_cpf ON users (cpf);
CREATE INDEX idx_users_role ON users (role);

--
-- Tabela: doctors
-- Dados profissionais complementares para usuários com role = DOCTOR.
--
CREATE TABLE doctors (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    crm_number VARCHAR(20) NOT NULL,
    crm_state CHAR(2) NOT NULL,
    specialty TEXT NOT NULL,
    signature_image_url TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (crm_number, crm_state)
);

--
-- Tabela: patient_health_profiles
-- Dados sensíveis de saúde (LGPD Art. 5º, II c/c Art. 11).
--
CREATE TABLE patient_health_profiles (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL UNIQUE REFERENCES users(id) ON DELETE CASCADE,
    blood_type VARCHAR(3),
    chronic_conditions TEXT,
    current_medications TEXT,
    allergies TEXT,
    mental_health_notes TEXT,
    height_cm SMALLINT,
    weight_kg NUMERIC(5,2),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

COMMENT ON TABLE patient_health_profiles IS 'Dado pessoal sensível nos termos do Art. 5º, II da LGPD. Requer consentimento específico e destacado (Art. 11, I) ou outra base legal aplicável.';
COMMENT ON COLUMN patient_health_profiles.mental_health_notes IS 'Texto livre preenchido pelo próprio paciente no onboarding; não há campo de consentimento específico vinculado a este dado sensível.';

--
-- Tabela: appointments
-- Consultas agendadas entre paciente e médico.
--
CREATE TABLE appointments (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    patient_id UUID NOT NULL REFERENCES users(id),
    doctor_id UUID NOT NULL REFERENCES doctors(id),
    status appointment_status_enum NOT NULL DEFAULT 'SCHEDULED',
    scheduled_at TIMESTAMPTZ NOT NULL,
    started_at TIMESTAMPTZ,
    ended_at TIMESTAMPTZ,
    video_room_url TEXT,
    price_cents INTEGER NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_appointments_patient_id ON appointments (patient_id);
CREATE INDEX idx_appointments_doctor_id ON appointments (doctor_id);
CREATE INDEX idx_appointments_scheduled_at ON appointments (scheduled_at);

--
-- Tabela: consultation_records
-- Prontuário eletrônico resumido gerado ao final da consulta.
--
CREATE TABLE consultation_records (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    appointment_id UUID NOT NULL UNIQUE REFERENCES appointments(id) ON DELETE CASCADE,
    symptoms TEXT,
    diagnosis_notes TEXT,
    prescribed_medications TEXT,
    icd10_codes TEXT[],
    recording_url TEXT,
    transcription_text TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

COMMENT ON COLUMN consultation_records.recording_url IS 'Link para gravação de áudio/vídeo da consulta armazenada em bucket privado; não há política de expurgo automatizada configurada.';
COMMENT ON COLUMN consultation_records.transcription_text IS 'Transcrição automática gerada por serviço de terceiro (Whisper API) — dado de saúde enviado a subprocessador externo.';

--
-- Tabela: consent_records
-- Registro de consentimentos coletados dos titulares, por finalidade.
--
CREATE TABLE consent_records (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    scope consent_scope_enum NOT NULL,
    granted BOOLEAN NOT NULL,
    ip_address INET,
    user_agent TEXT,
    collected_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    revoked_at TIMESTAMPTZ
);

CREATE INDEX idx_consent_records_user_id ON consent_records (user_id);

COMMENT ON TABLE consent_records IS 'Cobre TERMS_OF_USE, MARKETING, DATA_SHARING_PARTNERS e TELEMETRY. Não existe escopo de consentimento específico para dados de saúde (patient_health_profiles / consultation_records).';

--
-- Tabela: payments
-- Transações de pagamento das consultas.
--
CREATE TABLE payments (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    appointment_id UUID NOT NULL REFERENCES appointments(id),
    user_id UUID NOT NULL REFERENCES users(id),
    amount_cents INTEGER NOT NULL,
    payment_method VARCHAR(20) NOT NULL,
    card_last_four CHAR(4),
    card_brand VARCHAR(20),
    gateway_transaction_id TEXT,
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

COMMENT ON TABLE payments IS 'Somente os últimos 4 dígitos do cartão são persistidos; dados completos ficam no gateway (compatível com escopo PCI-DSS fora do banco da aplicação).';

--
-- Tabela: third_party_data_shares
-- Log de compartilhamento de dados pessoais com parceiros/subprocessadores.
--
CREATE TABLE third_party_data_shares (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id),
    partner_name TEXT NOT NULL,
    data_categories TEXT[] NOT NULL,
    purpose TEXT NOT NULL,
    shared_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

COMMENT ON TABLE third_party_data_shares IS 'Inclui registros com partner_name = ''AdInsight Analytics'' e data_categories contendo {email, cpf, chronic_conditions} para finalidade ''ad_targeting'', sem consentimento específico correspondente em consent_records.';

--
-- Tabela: audit_logs
-- Trilha de auditoria de acesso a dados sensíveis (leitura/escrita).
--
CREATE TABLE audit_logs (
    id BIGSERIAL PRIMARY KEY,
    actor_user_id UUID REFERENCES users(id),
    action VARCHAR(50) NOT NULL,
    entity_table VARCHAR(100) NOT NULL,
    entity_id UUID,
    ip_address INET,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_audit_logs_entity ON audit_logs (entity_table, entity_id);
CREATE INDEX idx_audit_logs_created_at ON audit_logs (created_at);

--
-- Tabela: data_subject_requests
-- Solicitações de titulares (acesso, correção, portabilidade, eliminação) — Art. 18 LGPD.
--
CREATE TABLE data_subject_requests (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id),
    request_type VARCHAR(30) NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'received',
    requested_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    resolved_at TIMESTAMPTZ,
    resolution_notes TEXT
);

--
-- Trigger genérica de updated_at
--
CREATE OR REPLACE FUNCTION set_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_users_updated_at BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TRIGGER trg_health_profiles_updated_at BEFORE UPDATE ON patient_health_profiles
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();


