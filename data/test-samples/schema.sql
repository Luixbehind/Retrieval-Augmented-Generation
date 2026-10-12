-- Schema de exemplo: sistema de cadastro de clientes de um e-commerce
-- Extraído via `pg_dump --schema-only` (formato DDL puro)

CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    full_name TEXT NOT NULL,
    cpf TEXT NOT NULL UNIQUE,
    email TEXT NOT NULL UNIQUE,
    phone TEXT,
    password_plain TEXT NOT NULL,
    birth_date DATE,
    address TEXT,
    marketing_opt_in BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT now()
);

CREATE TABLE orders (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id),
    total_amount NUMERIC(10,2) NOT NULL,
    payment_card_number TEXT,
    shipping_address TEXT NOT NULL,
    status TEXT DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT now()
);

CREATE TABLE support_tickets (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id),
    subject TEXT NOT NULL,
    message TEXT NOT NULL,
    health_condition_notes TEXT,
    created_at TIMESTAMP DEFAULT now()
);

CREATE TABLE analytics_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id),
    event_name TEXT NOT NULL,
    ip_address TEXT,
    device_fingerprint TEXT,
    created_at TIMESTAMP DEFAULT now()
);

-- Observações do time de dados:
-- 1. password_plain armazena a senha sem hashing.
-- 2. payment_card_number é armazenado sem tokenização/criptografia.
-- 3. health_condition_notes é preenchido livremente pelo atendente, sem base legal específica.
-- 4. Não há coluna de exclusão lógica (deleted_at) nem processo de retenção/expurgo de dados.
-- 5. marketing_opt_in vem com default true (usuário já nasce "opt-in" sem ação explícita).
