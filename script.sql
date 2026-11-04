
PRAGMA foreign_keys = ON;

-- =========================================
-- 1. USUÁRIOS DO SISTEMA
-- =========================================

CREATE TABLE IF NOT EXISTS usuarios (
    id_usuario INTEGER PRIMARY KEY AUTOINCREMENT,
    nome TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE,
    senha_hash TEXT NOT NULL,
    tipo TEXT NOT NULL
        CHECK (tipo IN ('aluno', 'profissional', 'administrador')),
    ativo INTEGER NOT NULL DEFAULT 1
        CHECK (ativo IN (0, 1)),
    data_criacao TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- =========================================
-- 2. RELATOS
-- =========================================

CREATE TABLE IF NOT EXISTS relatos (
    id_relato INTEGER PRIMARY KEY AUTOINCREMENT,

    codigo_acompanhamento TEXT NOT NULL UNIQUE,

    id_usuario INTEGER,

    titulo TEXT NOT NULL,
    descricao TEXT NOT NULL,
    categoria TEXT NOT NULL,

    anonimo INTEGER NOT NULL DEFAULT 1
        CHECK (anonimo IN (0, 1)),

    nome_identificado TEXT,
    email_identificado TEXT,

    status TEXT NOT NULL DEFAULT 'Recebido'
        CHECK (
            status IN (
                'Recebido',
                'Em análise',
                'Encaminhado',
                'Em acompanhamento',
                'Finalizado'
            )
        ),

    data_criacao TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (id_usuario)
        REFERENCES usuarios(id_usuario)
        ON DELETE SET NULL,

    CHECK (
        (anonimo = 1
            AND nome_identificado IS NULL
            AND email_identificado IS NULL)
        OR
        (anonimo = 0
            AND nome_identificado IS NOT NULL
            AND nome_identificado <> '')
    )
);

-- =========================================
-- 3. SOLICITAÇÕES DE ATENDIMENTO
-- =========================================

CREATE TABLE IF NOT EXISTS solicitacoes_atendimento (
    id_solicitacao INTEGER PRIMARY KEY AUTOINCREMENT,

    id_usuario INTEGER,
    id_relato INTEGER,

    nome TEXT,
    email TEXT,

    descricao TEXT NOT NULL,

    status TEXT NOT NULL DEFAULT 'Pendente'
        CHECK (
            status IN (
                'Pendente',
                'Agendada',
                'Atendida',
                'Cancelada'
            )
        ),

    data_solicitacao TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (id_usuario)
        REFERENCES usuarios(id_usuario)
        ON DELETE SET NULL,

    FOREIGN KEY (id_relato)
        REFERENCES relatos(id_relato)
        ON DELETE SET NULL
);

-- =========================================
-- 4. ATENDIMENTOS
-- =========================================

CREATE TABLE IF NOT EXISTS atendimentos (
    id_atendimento INTEGER PRIMARY KEY AUTOINCREMENT,

    id_relato INTEGER,
    id_solicitacao INTEGER,

    id_responsavel INTEGER NOT NULL,

    observacao TEXT,

    data_atendimento TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,

    status TEXT NOT NULL DEFAULT 'Agendado'
        CHECK (
            status IN (
                'Agendado',
                'Realizado',
                'Cancelado'
            )
        ),

    FOREIGN KEY (id_relato)
        REFERENCES relatos(id_relato)
        ON DELETE SET NULL,

    FOREIGN KEY (id_solicitacao)
        REFERENCES solicitacoes_atendimento(id_solicitacao)
        ON DELETE SET NULL,

    FOREIGN KEY (id_responsavel)
        REFERENCES usuarios(id_usuario)
);

-- =========================================
-- 5. ÍNDICES PARA CONSULTAS
-- =========================================

CREATE INDEX IF NOT EXISTS idx_relatos_status
ON relatos(status);

CREATE INDEX IF NOT EXISTS idx_relatos_categoria
ON relatos(categoria);

CREATE INDEX IF NOT EXISTS idx_relatos_data
ON relatos(data_criacao);

CREATE INDEX IF NOT EXISTS idx_solicitacoes_status
ON solicitacoes_atendimento(status);

CREATE INDEX IF NOT EXISTS idx_atendimentos_responsavel
ON atendimentos(id_responsavel);
