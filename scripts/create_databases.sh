#!/bin/bash
# PostgreSQL 초기화 시 추가 데이터베이스 생성
# docker-entrypoint-initdb.d/에서 init.sql 보다 먼저 실행 (00_ 접두사)
set -e

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
  SELECT 'CREATE DATABASE langfuse'
  WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'langfuse')\gexec
EOSQL
