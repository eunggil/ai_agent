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
    long_term_vector vector(768),   -- text-embedding-004 기본 차원
    short_term_vector vector(768)
);

-- 콘텐츠 테이블
CREATE TABLE IF NOT EXISTS contents (
    content_id VARCHAR(255) PRIMARY KEY,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    content_type VARCHAR(50),
    metadata JSONB,
    embedding vector(768)
);

-- 상품 테이블
CREATE TABLE IF NOT EXISTS products (
    product_id VARCHAR(255) PRIMARY KEY,
    brand_id VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    product_data JSONB,
    embedding vector(768)
);

-- 캠페인 테이블
CREATE TABLE IF NOT EXISTS campaigns (
    campaign_id VARCHAR(255) PRIMARY KEY,
    brand_id VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    campaign_data JSONB,
    targeting_rules JSONB,
    embedding vector(768)
);

-- 벡터 인덱스 (HNSW - 소규모 데이터셋에 적합, IVFFlat은 대량 데이터 필요)
CREATE INDEX IF NOT EXISTS users_long_term_vector_idx
    ON users USING hnsw (long_term_vector vector_cosine_ops);

CREATE INDEX IF NOT EXISTS users_short_term_vector_idx
    ON users USING hnsw (short_term_vector vector_cosine_ops);

CREATE INDEX IF NOT EXISTS contents_embedding_idx
    ON contents USING hnsw (embedding vector_cosine_ops);

CREATE INDEX IF NOT EXISTS products_embedding_idx
    ON products USING hnsw (embedding vector_cosine_ops);

CREATE INDEX IF NOT EXISTS campaigns_embedding_idx
    ON campaigns USING hnsw (embedding vector_cosine_ops);

-- 일반 인덱스
CREATE INDEX IF NOT EXISTS idx_users_created_at ON users(created_at);
CREATE INDEX IF NOT EXISTS idx_contents_type ON contents(content_type);
CREATE INDEX IF NOT EXISTS idx_products_brand ON products(brand_id);
CREATE INDEX IF NOT EXISTS idx_campaigns_brand ON campaigns(brand_id);

-- 사용자 데이터 삽입
INSERT INTO users (user_id, profile) VALUES
    ('user_001', '{"name": "김지수", "age": 25, "interests": ["fashion", "beauty", "lifestyle"], "mindset": "trendy", "recent_activities": ["립스틱 상품 조회", "캐주얼 아웃핏 검색", "뷰티 유튜버 팔로우"], "vector_summary": "패션/뷰티 관심 높음, 20대 여성, 자연스러운 스타일 선호"}'),
    ('user_002', '{"name": "이민준", "age": 32, "interests": ["sports", "tech", "food"], "mindset": "active", "recent_activities": ["러닝화 상품 조회", "단백질 보충제 검색", "헬스 유튜버 팔로우"], "vector_summary": "스포츠/건강 관심 높음, 30대 남성, 기능성 제품 선호"}'),
    ('user_003', '{"name": "박서연", "age": 28, "interests": ["travel", "food", "photography"], "mindset": "relaxed", "recent_activities": ["여행 숙소 검색", "맛집 리뷰 조회", "카메라 악세서리 조회"], "vector_summary": "여행/음식/취미 관심 높음, 20대 후반, 경험 중심 소비 성향"}')
ON CONFLICT (user_id) DO UPDATE SET profile = EXCLUDED.profile;

-- 광고 캠페인 데이터 삽입 (image_url: picsum.photos 플레이스홀더)
INSERT INTO campaigns (campaign_id, brand_id, campaign_data, targeting_rules) VALUES
    ('camp_001', 'LUNA',      '{"ad_id": "ad_001", "product": "LUNA 매트 립스틱", "brand": "LUNA", "category": "beauty", "description": "촉촉한 매트 립스틱, 자연스러운 누드 베이지 컬러. 하루 종일 지속되는 발색.", "bid": 2.5, "image_url": "https://picsum.photos/seed/luna-lipstick/400/400"}',  '{"tags": ["beauty", "cosmetic", "lip", "fashion"]}'),
    ('camp_002', 'ZARA',      '{"ad_id": "ad_002", "product": "ZARA 오버핏 티셔츠", "brand": "ZARA", "category": "fashion", "description": "편안한 오버핏 코튼 티셔츠. 베이직한 컬러와 부드러운 소재.", "bid": 1.8, "image_url": "https://picsum.photos/seed/zara-shirt/400/400"}',              '{"tags": ["fashion", "casual", "top", "lifestyle"]}'),
    ('camp_003', 'INNISFREE', '{"ad_id": "ad_003", "product": "INNISFREE 녹차 수분 세럼", "brand": "INNISFREE", "category": "skincare", "description": "제주 녹차 성분 수분 세럼. 민감성 피부에도 순한 수분 보충.", "bid": 3.0, "image_url": "https://picsum.photos/seed/innisfree-serum/400/400"}', '{"tags": ["beauty", "skincare", "moisturizing", "lifestyle"]}'),
    ('camp_004', 'Nike',      '{"ad_id": "ad_004", "product": "나이키 에어맥스 270", "brand": "Nike", "category": "sports", "description": "에어쿠션 기술로 하루 종일 편안한 러닝화. 스타일과 기능 모두.", "bid": 4.0, "image_url": "https://picsum.photos/seed/nike-airmax/400/400"}',         '{"tags": ["sports", "shoes", "running", "active"]}'),
    ('camp_005', 'Loacker',   '{"ad_id": "ad_005", "product": "로아커 웨하스 초콜릿", "brand": "Loacker", "category": "food", "description": "이탈리아 전통 웨하스에 진한 초콜릿 코팅. 달콤한 오후의 행복.", "bid": 1.2, "image_url": "https://picsum.photos/seed/loacker-choco/400/400"}',       '{"tags": ["food", "snack", "sweet", "lifestyle", "travel"]}'),
    ('camp_006', 'Sony',      '{"ad_id": "ad_006", "product": "소니 WH-1000XM5 헤드폰", "brand": "Sony", "category": "tech", "description": "업계 최고 수준의 노이즈 캔슬링. 30시간 배터리 지속.", "bid": 5.0, "image_url": "https://picsum.photos/seed/sony-headphone/400/400"}',               '{"tags": ["tech", "music", "travel", "lifestyle"]}')
ON CONFLICT (campaign_id) DO UPDATE SET campaign_data = EXCLUDED.campaign_data;

-- 확인 메시지
DO $$
BEGIN
    RAISE NOTICE 'Database initialized successfully with pgvector extension!';
END $$;
