"""
목업 테스트 데이터
USE_MOCK_VECTOR_DB=true 일 때 실제 DB 대신 사용
"""
from typing import List

# ──────────────────────────────────────────
# 목업 사용자 데이터
# ──────────────────────────────────────────
MOCK_USERS: dict = {
    "user_001": {
        "user_id": "user_001",
        "name": "김지수",
        "age": 25,
        "interests": ["fashion", "beauty", "lifestyle"],
        "mindset": "trendy",
        "recent_activities": [
            "립스틱 상품 조회",
            "캐주얼 아웃핏 검색",
            "뷰티 유튜버 팔로우",
        ],
        "vector_summary": "패션/뷰티 관심 높음, 20대 여성, 자연스러운 스타일 선호",
    },
    "user_002": {
        "user_id": "user_002",
        "name": "이민준",
        "age": 32,
        "interests": ["sports", "tech", "food"],
        "mindset": "active",
        "recent_activities": [
            "러닝화 상품 조회",
            "단백질 보충제 검색",
            "헬스 유튜버 팔로우",
        ],
        "vector_summary": "스포츠/건강 관심 높음, 30대 남성, 기능성 제품 선호",
    },
    "user_003": {
        "user_id": "user_003",
        "name": "박서연",
        "age": 28,
        "interests": ["travel", "food", "photography"],
        "mindset": "relaxed",
        "recent_activities": [
            "여행 숙소 검색",
            "맛집 리뷰 조회",
            "카메라 악세서리 조회",
        ],
        "vector_summary": "여행/음식/취미 관심 높음, 20대 후반, 경험 중심 소비 성향",
    },
}

DEFAULT_USER = {
    "user_id": "unknown",
    "name": "신규 사용자",
    "age": 25,
    "interests": ["lifestyle"],
    "mindset": "curious",
    "recent_activities": [],
    "vector_summary": "신규 사용자, 선호도 파악 중",
}

# ──────────────────────────────────────────
# 목업 광고 후보 데이터
# ──────────────────────────────────────────
MOCK_ADS: List[dict] = [
    {
        "ad_id": "ad_001",
        "campaign_id": "camp_001",
        "product": "LUNA 매트 립스틱",
        "brand": "LUNA",
        "category": "beauty",
        "description": "촉촉한 매트 립스틱, 자연스러운 누드 베이지 컬러. 하루 종일 지속되는 발색.",
        "bid": 2.5,
        "tags": ["beauty", "cosmetic", "lip", "fashion"],
    },
    {
        "ad_id": "ad_002",
        "campaign_id": "camp_002",
        "product": "ZARA 오버핏 티셔츠",
        "brand": "ZARA",
        "category": "fashion",
        "description": "편안한 오버핏 코튼 티셔츠. 베이직한 컬러와 부드러운 소재.",
        "bid": 1.8,
        "tags": ["fashion", "casual", "top", "lifestyle"],
    },
    {
        "ad_id": "ad_003",
        "campaign_id": "camp_003",
        "product": "INNISFREE 녹차 수분 세럼",
        "brand": "INNISFREE",
        "category": "skincare",
        "description": "제주 녹차 성분 수분 세럼. 민감성 피부에도 순한 수분 보충.",
        "bid": 3.0,
        "tags": ["beauty", "skincare", "moisturizing", "lifestyle"],
    },
    {
        "ad_id": "ad_004",
        "campaign_id": "camp_004",
        "product": "나이키 에어맥스 270",
        "brand": "Nike",
        "category": "sports",
        "description": "에어쿠션 기술로 하루 종일 편안한 러닝화. 스타일과 기능 모두.",
        "bid": 4.0,
        "tags": ["sports", "shoes", "running", "active"],
    },
    {
        "ad_id": "ad_005",
        "campaign_id": "camp_005",
        "product": "로아커 웨하스 초콜릿",
        "brand": "Loacker",
        "category": "food",
        "description": "이탈리아 전통 웨하스에 진한 초콜릿 코팅. 달콤한 오후의 행복.",
        "bid": 1.2,
        "tags": ["food", "snack", "sweet", "lifestyle", "travel"],
    },
    {
        "ad_id": "ad_006",
        "campaign_id": "camp_006",
        "product": "소니 WH-1000XM5 헤드폰",
        "brand": "Sony",
        "category": "tech",
        "description": "업계 최고 수준의 노이즈 캔슬링. 30시간 배터리 지속.",
        "bid": 5.0,
        "tags": ["tech", "music", "travel", "lifestyle"],
    },
]


def get_user(user_id: str) -> dict:
    """사용자 데이터 조회 (없으면 기본값 반환)"""
    return MOCK_USERS.get(user_id, {**DEFAULT_USER, "user_id": user_id})


def retrieve_ad_candidates(interests: list, prompt: str, top_k: int = 3) -> List[dict]:
    """관심사 + 프롬프트 키워드로 광고 후보 필터링

    실제 구현에서는 pgvector 유사도 검색으로 대체됩니다.
    """
    prompt_lower = prompt.lower()
    scored = []

    for ad in MOCK_ADS:
        score = 0.0

        # 관심사 태그 일치
        for interest in interests:
            if interest in ad["tags"]:
                score += 0.4

        # 프롬프트 키워드 일치
        for tag in ad["tags"]:
            if tag in prompt_lower:
                score += 0.3

        # 카테고리 직접 언급
        if ad["category"] in prompt_lower:
            score += 0.2

        # 입찰가 보너스 (정규화)
        score += ad["bid"] / 10.0

        scored.append({**ad, "relevance_score": round(score, 3)})

    scored.sort(key=lambda x: x["relevance_score"], reverse=True)
    return scored[:top_k]
