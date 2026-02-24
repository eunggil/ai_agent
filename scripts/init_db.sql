-- AI Agent Database Initialization Script
-- PostgreSQL with pgvector extension

-- pgvector 확장 설치
CREATE EXTENSION IF NOT EXISTS vector;

-- 사용자 테이블
CREATE TABLE IF NOT EXISTS users (
    user_id VARCHAR(255) PRIMARY KEY,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    profile JSONB,
    long_term_vector vector(128),
    short_term_vector vector(128)
);

-- 콘텐츠 테이블
CREATE TABLE IF NOT EXISTS contents (
    content_id VARCHAR(255) PRIMARY KEY,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    content_type VARCHAR(50),
    metadata JSONB,
    embedding vector(128)
);

-- 상품 테이블
CREATE TABLE IF NOT EXISTS products (
    product_id VARCHAR(255) PRIMARY KEY,
    brand_id VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    product_data JSONB,
    embedding vector(128)
);

-- 캠페인 테이블
CREATE TABLE IF NOT EXISTS campaigns (
    campaign_id VARCHAR(255) PRIMARY KEY,
    brand_id VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    campaign_data JSONB,
    targeting_rules JSONB,
    embedding vector(128)
);

-- 인덱스 생성 (벡터 검색 최적화)
CREATE INDEX IF NOT EXISTS users_long_term_vector_idx
    ON users USING ivfflat (long_term_vector vector_cosine_ops) WITH (lists = 100);

CREATE INDEX IF NOT EXISTS users_short_term_vector_idx
    ON users USING ivfflat (short_term_vector vector_cosine_ops) WITH (lists = 100);

CREATE INDEX IF NOT EXISTS contents_embedding_idx
    ON contents USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

CREATE INDEX IF NOT EXISTS products_embedding_idx
    ON products USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

CREATE INDEX IF NOT EXISTS campaigns_embedding_idx
    ON campaigns USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

-- 일반 인덱스
CREATE INDEX IF NOT EXISTS idx_users_created_at ON users(created_at);
CREATE INDEX IF NOT EXISTS idx_contents_type ON contents(content_type);
CREATE INDEX IF NOT EXISTS idx_products_brand ON products(brand_id);
CREATE INDEX IF NOT EXISTS idx_campaigns_brand ON campaigns(brand_id);

-- 샘플 데이터 삽입 (Mock 데이터와 동일)
INSERT INTO users (user_id, profile, long_term_vector) VALUES
    ('user_001', '{"name": "테스트 유저 1", "interests": ["패션", "뷰티"]}', ARRAY[0.1, 0.2, 0.3]::real[]::vector)
ON CONFLICT (user_id) DO NOTHING;

-- 확인 메시지
DO $$
BEGIN
    RAISE NOTICE 'Database initialized successfully with pgvector extension!';
END $$;
