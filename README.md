# 💜 SESI Acolhe

**OUVIR → ACOLHER → ENCAMINHAR**

## 📌 Sobre o projeto

O **SESI Acolhe** é uma proposta de plataforma digital desenvolvida para aproximar os estudantes da equipe responsável pelo acolhimento escolar, oferecendo um espaço seguro e organizado para o registro de relatos e solicitações de atendimento.

O projeto busca facilitar a comunicação entre os alunos e os profissionais da instituição, contribuindo para a identificação de situações que necessitam de atenção e para o encaminhamento adequado de cada caso.

## 🎯 Objetivo

Promover um ambiente escolar mais acolhedor, incentivando a escuta, o cuidado e o acompanhamento dos estudantes por meio de uma plataforma acessível e organizada.

## ⚙️ Funcionalidades previstas

- Registro de relatos relacionados ao ambiente escolar.
- Possibilidade de envio de relatos anônimos.
- Geração de código para acompanhamento dos relatos.
- Organização dos relatos por categoria e status.
- Registro dos atendimentos realizados pelos profissionais responsáveis.
- Solicitação de atendimento.
- Acompanhamento do andamento dos casos.

## 🛠️ Tecnologias utilizadas

- **SQLite:** modelagem e gerenciamento do banco de dados.
- **SQL:** criação das tabelas, relacionamentos e índices.
- **Diagrama Entidade-Relacionamento (DER):** representação visual da estrutura do banco de dados.
- **Git e GitHub:** versionamento e documentação do projeto.

## 🗂️ Estrutura do repositório

```text
SESI-Acolhe/
├── README.md
├── Levantamento_de_Requisitos.pdf
├── DER.png
└── script.sql
```

**Descrição dos arquivos:**

- `README.md`: documentação e apresentação do projeto.
- `Levantamento_de_Requisitos.pdf`: documento com a definição do problema, os requisitos funcionais e não funcionais e a organização da equipe.
- `DER.png`: imagem do Diagrama Entidade-Relacionamento do banco de dados.
- `script.sql`: código SQL responsável pela criação da estrutura do banco de dados.

## 🗄️ Modelagem do banco de dados

O banco de dados foi planejado para organizar as informações necessárias ao funcionamento da plataforma, utilizando as seguintes entidades:

- **Usuários:** armazena os dados dos profissionais e administradores.
- **Relatos:** registra as situações comunicadas pelos estudantes.
- **Atendimentos:** registra os acompanhamentos realizados pelos responsáveis.
- **Solicitações de atendimento:** organiza os pedidos de atendimento feitos à equipe responsável.

O relacionamento entre essas entidades permite estruturar as informações e manter a organização dos registros.

## 🔐 Privacidade e segurança

Por lidar com informações relacionadas ao bem-estar dos estudantes, o SESI Acolhe considera a privacidade e a segurança requisitos essenciais. A proposta prevê o cuidado com os dados pessoais, o controle de acesso às informações e a possibilidade de envio de relatos anônimos.

A implementação dessas medidas deverá seguir as orientações da instituição e as normas aplicáveis de proteção de dados.

## 👥 Equipe

Projeto desenvolvido por uma equipe de **7 integrantes**, com divisão de responsabilidades para as etapas de planejamento, levantamento de requisitos e modelagem do banco de dados.

**Integrantes:** adicionar os nomes dos sete integrantes.

## 🚀 Etapa atual do projeto

Nesta etapa, foram desenvolvidos os documentos de levantamento de requisitos, a modelagem do banco de dados por meio do DER e o script SQL para criação das tabelas.

O repositório reúne esses materiais para facilitar a documentação, a consulta e o versionamento do projeto.

## 💜 Nossa proposta

Acreditamos que uma escola melhor começa com a escuta e o acolhimento. O SESI Acolhe propõe aproximar estudantes e profissionais, valorizando cada relato e contribuindo para um ambiente escolar mais seguro e humano.

**SESI
