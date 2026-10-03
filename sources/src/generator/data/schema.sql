-- Source tables for the CDC pipeline. Idempotent: safe to run on every `generator dims` / stream start.
-- Every table has a primary key so Debezium can key its change events.
CREATE SCHEMA IF NOT EXISTS fruit_juice;

CREATE TABLE IF NOT EXISTS fruit_juice.dim_categoria (
    cod_categoria VARCHAR(50) PRIMARY KEY,
    desc_categoria VARCHAR(200)
);
CREATE TABLE IF NOT EXISTS fruit_juice.dim_marca (
    cod_marca VARCHAR(50) PRIMARY KEY,
    desc_marca VARCHAR(200),
    cod_categoria VARCHAR(50)
);
CREATE TABLE IF NOT EXISTS fruit_juice.dim_produto (
    cod_produto VARCHAR(50) PRIMARY KEY,
    desc_produto VARCHAR(200),
    atr_tamanho VARCHAR(200),
    atr_sabor VARCHAR(200),
    cod_marca VARCHAR(50)
);
CREATE TABLE IF NOT EXISTS fruit_juice.dim_cliente (
    cod_cliente VARCHAR(50) PRIMARY KEY,
    desc_cliente VARCHAR(200),
    cod_cidade VARCHAR(50),
    desc_cidade VARCHAR(200),
    cod_estado VARCHAR(50),
    desc_estado VARCHAR(200),
    cod_regiao VARCHAR(50),
    desc_regiao VARCHAR(200),
    cod_segmento VARCHAR(50),
    desc_segmento VARCHAR(200)
);
CREATE TABLE IF NOT EXISTS fruit_juice.dim_fabrica (
    cod_fabrica VARCHAR(50) PRIMARY KEY,
    desc_fabrica VARCHAR(200)
);
CREATE TABLE IF NOT EXISTS fruit_juice.dim_organizacional (
    cod_filho VARCHAR(50) PRIMARY KEY,
    desc_filho VARCHAR(200),
    cod_pai VARCHAR(50),
    esquerda INTEGER,
    direita INTEGER,
    nivel INTEGER
);

CREATE TABLE IF NOT EXISTS fruit_juice.stream_sales (
    event_id UUID PRIMARY KEY,
    seq BIGINT NOT NULL,
    event_time TIMESTAMPTZ NOT NULL,
    cod_dia VARCHAR(8) NOT NULL,
    cod_cliente VARCHAR(50) NOT NULL,
    cod_produto VARCHAR(50) NOT NULL,
    cod_fabrica VARCHAR(50) NOT NULL,
    cod_organizacional VARCHAR(50) NOT NULL,
    faturamento DOUBLE PRECISION NOT NULL,
    imposto DOUBLE PRECISION NOT NULL,
    custo_variavel DOUBLE PRECISION NOT NULL,
    unidades DOUBLE PRECISION NOT NULL,
    quantidade_vendida DOUBLE PRECISION NOT NULL
);
