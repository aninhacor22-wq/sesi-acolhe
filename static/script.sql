-- =====================================================
-- PROJETO: SESI ACOLHE
-- BANCO DE DADOS: SQLite
-- =====================================================

PRAGMA foreign_keys = ON;

-- =====================================================
-- 1. TABELA DE USUARIOS
-- =====================================================

CREATE TABLE IF NOT EXISTS usuarios (
    id_usuario INTEGER PRIMARY KEY AUTOINCREMENT,
    nome TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE,
    senha_hash TEXT NOT NULL,
    tipo TEXT NOT NULL
        CHECK (tipo IN ('profissional', 'administrador'))
);

-- =====================================================
-- 2. TABELA DE RELATOS
-- =====================================================

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
        OR
        (anonimo = 0 AND id_usuario IS NOT NULL)
    )
);

-- =====================================================
-- 3. TABELA DE ATENDIMENTOS
-- =====================================================

CREATE TABLE IF NOT EXISTS atendimentos (
    id_atendimento INTEGER PRIMARY KEY AUTOINCREMENT,
    id_relato INTEGER NOT NULL,
    id_responsavel INTEGER NOT NULL,
    observacao TEXT NOT NULL,
    data_atendimento TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    status TEXT
        CHECK (
            status IS NULL OR status IN (
                'Recebido',
                'Em análise',
                'Encaminhado',
                'Em acompanhamento',
                'Finalizado'
            )
        ),
    FOREIGN KEY (id_relato)
        REFERENCES relatos(id_relato)
        ON DELETE CASCADE,
    FOREIGN KEY (id_responsavel)
        REFERENCES usuarios(id_usuario)
);

-- =====================================================
-- 4. TABELA DE SOLICITACOES DE ATENDIMENTO
-- =====================================================

CREATE TABLE IF NOT EXISTS solicitacoes_atendimento (
    id_solicitacao INTEGER PRIMARY KEY AUTOINCREMENT,
    id_usuario INTEGER,
    id_relato INTEGER,
    descricao TEXT NOT NULL,
    data_solicitacao TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    status TEXT NOT NULL DEFAULT 'Pendente'
        CHECK (status IN (
            'Pendente',
            'Agendada',
            'Atendida',
            'Cancelada'
        )),
    FOREIGN KEY (id_usuario)
        REFERENCES usuarios(id_usuario)
        ON DELETE SET NULL,
    FOREIGN KEY (id_relato)
        REFERENCES relatos(id_relato)
        ON DELETE SET NULL
);

-- =====================================================
-- 5. INDICES PARA OTIMIZAR CONSULTAS
-- =====================================================

CREATE INDEX IF NOT EXISTS idx_relatos_status
    ON relatos(status);

CREATE INDEX IF NOT EXISTS idx_relatos_categoria
    ON relatos(categoria);

CREATE INDEX IF NOT EXISTS idx_atendimentos_relato
    ON atendimentos(id_relato);

-- =====================================================
-- 6. INSERCAO DE DADOS FICTICIOS (INSERT)
-- =====================================================

-- Profissional ficticio para demonstracao.
-- A senha abaixo e apenas um valor demonstrativo,
-- NAO e um hash real para autenticacao.

INSERT INTO usuarios (
    nome,
    email,
    senha_hash,
    tipo
)
VALUES (
    'Profissional Demonstrativo',
    'profissional.exemplo@exemplo.com',
    'HASH_DEMONSTRATIVO_NAO_UTILIZAR_PARA_LOGIN',
    'profissional'
)
ON CONFLICT(email) DO NOTHING;

-- Relato ficticio para testar o banco.
-- O relato e anonimo e nao possui usuario associado.

INSERT INTO relatos (
    codigo_acompanhamento,
    id_usuario,
    titulo,
    descricao,
    categoria,
    anonimo,
    status
)
VALUES (
    'EXEMPLO-001',
    NULL,
    'Relato demonstrativo',
    'Registro ficticio utilizado para testar o funcionamento do banco de dados.',
    'Conflito',
    1,
    'Recebido'
)
ON CONFLICT(codigo_acompanhamento) DO NOTHING;

-- Atendimento demonstrativo associado ao relato.
-- Evita duplicacao ao executar novamente o script.

INSERT INTO atendimentos (
    id_relato,
    id_responsavel,
    observacao,
    status
)
SELECT
    r.id_relato,
    u.id_usuario,
    'Registro demonstrativo para testar o acompanhamento.',
    'Em análise'
FROM relatos AS r
JOIN usuarios AS u
    ON u.email = 'profissional.exemplo@exemplo.com'
WHERE r.codigo_acompanhamento = 'EXEMPLO-001'
  AND NOT EXISTS (
      SELECT 1
      FROM atendimentos AS a
      WHERE a.id_relato = r.id_relato
        AND a.id_responsavel = u.id_usuario
        AND a.observacao =
            'Registro demonstrativo para testar o acompanhamento.'
  );

-- Solicitacao ficticia de atendimento.

INSERT INTO solicitacoes_atendimento (
    id_usuario,
    id_relato,
    descricao,
    status
)
SELECT
    NULL,
    r.id_relato,
    'Solicitacao demonstrativa para testar o banco de dados.',
    'Pendente'
FROM relatos AS r
WHERE r.codigo_acompanhamento = 'EXEMPLO-001'
  AND NOT EXISTS (
      SELECT 1
      FROM solicitacoes_atendimento AS s
      WHERE s.id_relato = r.id_relato
        AND s.descricao =
            'Solicitacao demonstrativa para testar o banco de dados.'
  );

-- =====================================================
-- FIM DO SCRIPT
-- =====================================================
