
-- SESI Acolhe - Banco de dados SQLite

PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS usuarios (
    id_usuario INTEGER PRIMARY KEY AUTOINCREMENT,
    nome TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE,
    senha_hash TEXT NOT NULL,
    tipo TEXT NOT NULL
        CHECK (tipo IN ('profissional', 'administrador'))
);

CREATE TABLE IF NOT EXISTS relatos (
    id_relato INTEGER PRIMARY KEY AUTOINCREMENT,
    codigo_acompanhamento TEXT NOT NULL UNIQUE,
    id_usuario INTEGER,
    titulo TEXT NOT NULL,
    descricao TEXT NOT NULL,
    categoria TEXT NOT NULL,
    anonimo INTEGER NOT NULL DEFAULT 1
        CHECK (anonimo IN (0, 1)),
    data_criacao TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    status TEXT NOT NULL DEFAULT 'Recebido'
        CHECK (status IN (
            'Recebido',
            'Em análise',
            'Encaminhado',
            'Em acompanhamento',
            'Finalizado'
        )),
    FOREIGN KEY (id_usuario)
        REFERENCES usuarios(id_usuario)
        ON DELETE SET NULL,
    CHECK (
        (anonimo = 1 AND id_usuario IS NULL)
        OR (anonimo = 0 AND id_usuario IS NOT NULL)
    )
);

CREATE TABLE IF NOT EXISTS atendimentos (
    id_atendimento INTEGER PRIMARY KEY AUTOINCREMENT,
    id_relato INTEGER NOT NULL,
    id_responsavel INTEGER NOT NULL,
    observacao TEXT NOT NULL,
    data_atendimento TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    status TEXT,
    FOREIGN KEY (id_relato)
        REFERENCES relatos(id_relato)
        ON DELETE CASCADE,
    FOREIGN KEY (id_responsavel)
        REFERENCES usuarios(id_usuario)
);

CREATE TABLE IF NOT EXISTS solicitacoes_atendimento (
    id_solicitacao INTEGER PRIMARY KEY AUTOINCREMENT,
    id_usuario INTEGER,
    id_relato INTEGER,
    descricao TEXT NOT NULL,
    data_solicitacao TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    status TEXT NOT NULL DEFAULT 'Pendente'
        CHECK (status IN (
            'Pendente', 'Agendada', 'Atendida', 'Cancelada'
        )),
    FOREIGN KEY (id_usuario)
        REFERENCES usuarios(id_usuario)
        ON DELETE SET NULL,
    FOREIGN KEY (id_relato)
        REFERENCES relatos(id_relato)
        ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_relatos_status
    ON relatos(status);

CREATE INDEX IF NOT EXISTS idx_relatos_categoria
    ON relatos(categoria);

CREATE INDEX IF NOT EXISTS idx_atendimentos_relato
    ON atendimentos(id_relato);
