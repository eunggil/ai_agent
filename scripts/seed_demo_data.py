"""
데모 데이터 시드 스크립트
- 사용자 15명, 상품 100개, 광고 캠페인 100개, 콘텐츠 100개 생성
- Vertex AI text-embedding-004 로 임베딩 배치 생성

실행:
    docker compose exec ai-agent python scripts/seed_demo_data.py
"""
import json
import logging
import os
import random
import sys
import uuid
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import psycopg2
import psycopg2.extras
import vertexai
from vertexai.language_models import TextEmbeddingInput, TextEmbeddingModel

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

PROJECT_ID = os.getenv("GCP_PROJECT_ID", "")
REGION = os.getenv("GCP_REGION", "us-central1")
EMBEDDING_MODEL = os.getenv("VERTEX_AI_EMBEDDING_MODEL", "text-embedding-004")
BATCH_SIZE = 20  # Vertex AI 배치 사이즈


# ══════════════════════════════════════════════════════════════
# 원본 데이터 정의
# ══════════════════════════════════════════════════════════════

KOREAN_NAMES = [
    "김지수", "이민준", "박서연", "최도윤", "정하은",
    "강지호", "윤서현", "장민서", "임예린", "한지원",
    "오승준", "신다은", "백현우", "류나연", "송태양",
]

INTEREST_POOLS = {
    "beauty":      ["beauty", "cosmetic", "makeup", "skincare"],
    "fashion":     ["fashion", "style", "clothing", "outfit"],
    "sports":      ["sports", "fitness", "running", "gym"],
    "tech":        ["tech", "gadget", "electronics", "AI"],
    "food":        ["food", "cooking", "restaurant", "snack"],
    "travel":      ["travel", "trip", "tourism", "hotel"],
    "home":        ["home", "interior", "furniture", "decor"],
    "health":      ["health", "wellness", "yoga", "supplement"],
    "photography": ["photography", "camera", "art", "creative"],
    "music":       ["music", "concert", "playlist", "audio"],
    "gaming":      ["gaming", "esports", "console", "mobile"],
    "lifestyle":   ["lifestyle", "daily", "routine", "trend"],
}

MINDSETS = ["trendy", "active", "relaxed", "curious", "creative", "practical", "social"]

ACTIVITY_TEMPLATES = {
    "beauty":      ["립스틱 상품 조회", "파운데이션 리뷰 검색", "뷰티 유튜버 팔로우", "화장품 할인 이벤트 참여"],
    "fashion":     ["캐주얼 아웃핏 검색", "신상 의류 조회", "패션 인플루언서 팔로우", "코디 추천 검색"],
    "sports":      ["러닝화 상품 조회", "단백질 보충제 검색", "헬스 유튜버 팔로우", "운동 루틴 검색"],
    "tech":        ["스마트폰 스펙 비교", "이어폰 리뷰 검색", "IT 뉴스 구독", "신제품 출시 알림 설정"],
    "food":        ["맛집 리뷰 조회", "요리 레시피 검색", "배달 앱 이용", "푸드 유튜버 팔로우"],
    "travel":      ["여행 숙소 검색", "항공권 가격 비교", "여행지 리뷰 조회", "여행 패키지 문의"],
    "home":        ["인테리어 사진 저장", "가구 가격 비교", "홈 데코 검색", "청소 용품 조회"],
    "health":      ["요가 클래스 검색", "건강식품 조회", "헬스장 등록 문의", "의료 정보 검색"],
    "photography": ["카메라 악세서리 조회", "사진 편집 앱 다운로드", "포토그래퍼 팔로우", "스튜디오 예약"],
    "music":       ["음악 스트리밍 이용", "콘서트 티켓 검색", "앨범 리뷰 조회", "악기 검색"],
    "gaming":      ["게임 리뷰 검색", "게임 아이템 구매", "게임 스트리머 팔로우", "콘솔 가격 비교"],
    "lifestyle":   ["라이프스타일 블로그 구독", "일상 용품 쇼핑", "트렌드 뉴스 조회", "SNS 피드 탐색"],
}

PRODUCTS = [
    # beauty (15)
    {"category": "beauty", "brand": "LUNA", "name": "매트 립스틱 누드베이지", "desc": "촉촉한 매트 립스틱, 자연스러운 누드 베이지 컬러. 하루 종일 지속되는 발색.", "price": 18000, "tags": ["beauty", "lip", "cosmetic", "fashion"]},
    {"category": "beauty", "brand": "MAC", "name": "루비 립스틱", "desc": "강렬한 레드 컬러의 클래식 립스틱. 비건 성분으로 제작.", "price": 35000, "tags": ["beauty", "lip", "cosmetic", "luxury"]},
    {"category": "beauty", "brand": "NARS", "name": "블러셔 오르가즘", "desc": "복숭아빛 골드 시머 블러셔. 자연스러운 혈색 연출.", "price": 42000, "tags": ["beauty", "blush", "cosmetic", "makeup"]},
    {"category": "beauty", "brand": "Too Faced", "name": "베터 댄 섹스 마스카라", "desc": "볼륨과 컬을 동시에. 워터프루프 포뮬라.", "price": 28000, "tags": ["beauty", "mascara", "eyes", "cosmetic"]},
    {"category": "beauty", "brand": "Charlotte Tilbury", "name": "매직 파운데이션", "desc": "24시간 지속력, 천연 피부 표현. SPF15 함유.", "price": 68000, "tags": ["beauty", "foundation", "makeup", "skincare"]},
    {"category": "beauty", "brand": "Urban Decay", "name": "나키드 아이섀도 팔레트", "desc": "12가지 뉴트럴 톤 아이섀도. 데일리부터 스모키까지.", "price": 75000, "tags": ["beauty", "eyes", "eyeshadow", "makeup"]},
    {"category": "beauty", "brand": "Benefit", "name": "POREfessional 프라이머", "desc": "모공 커버 페이스 프라이머. 매트한 피부 연출.", "price": 45000, "tags": ["beauty", "primer", "makeup", "pore"]},
    {"category": "beauty", "brand": "Fenty Beauty", "name": "프로 필트르 파운데이션", "desc": "50가지 쉐이드. 풀커버 매트 파운데이션.", "price": 52000, "tags": ["beauty", "foundation", "makeup", "inclusive"]},
    {"category": "beauty", "brand": "Dior", "name": "립 글로우 오일", "desc": "촉촉한 틴트 립 오일. 컬러 케어 효과.", "price": 55000, "tags": ["beauty", "lip", "glossy", "luxury"]},
    {"category": "beauty", "brand": "YSL", "name": "루주 퓨르 쿠튀르", "desc": "대담한 컬러와 편안한 착용감의 럭셔리 립스틱.", "price": 62000, "tags": ["beauty", "lip", "luxury", "fashion"]},
    {"category": "beauty", "brand": "Huda Beauty", "name": "리퀴드 매트 립스틱", "desc": "강렬한 발색의 리퀴드 립. 논 드라이 포뮬라.", "price": 30000, "tags": ["beauty", "lip", "cosmetic", "trendy"]},
    {"category": "beauty", "brand": "Armani", "name": "파워 패브릭 파운데이션", "desc": "내추럴 세미매트 마감. 12시간 지속력.", "price": 78000, "tags": ["beauty", "foundation", "luxury", "makeup"]},
    {"category": "beauty", "brand": "Clinique", "name": "블랙 허니 립스틱", "desc": "모든 피부톤에 어울리는 유니버설 쉐이드.", "price": 32000, "tags": ["beauty", "lip", "cosmetic", "classic"]},
    {"category": "beauty", "brand": "Bobbi Brown", "name": "쿠션 파운데이션", "desc": "촉촉한 피부 표현의 쿠션 파운데이션. SPF35.", "price": 65000, "tags": ["beauty", "foundation", "makeup", "moisturizing"]},
    {"category": "beauty", "brand": "Rare Beauty", "name": "소프트 핀치 리퀴드 블러셔", "desc": "소량으로 자연스러운 혈색. 셀레나 고메즈 브랜드.", "price": 38000, "tags": ["beauty", "blush", "liquid", "trendy"]},

    # skincare (10)
    {"category": "skincare", "brand": "INNISFREE", "name": "녹차 수분 세럼", "desc": "제주 녹차 성분 수분 세럼. 민감성 피부에도 순한 수분 보충.", "price": 22000, "tags": ["skincare", "serum", "moisturizing", "natural"]},
    {"category": "skincare", "brand": "SK-II", "name": "페이셜 트리트먼트 에센스", "desc": "피테라™ 성분 90% 이상 함유. 피부 결 개선.", "price": 180000, "tags": ["skincare", "essence", "luxury", "anti-aging"]},
    {"category": "skincare", "brand": "Laneige", "name": "워터뱅크 수분크림", "desc": "히알루론산 집중 수분 공급. 72시간 수분 지속.", "price": 45000, "tags": ["skincare", "moisturizer", "hydrating", "daily"]},
    {"category": "skincare", "brand": "Cosrx", "name": "어드밴스드 스네일 세럼", "desc": "달팽이 분비물 96.3% 함유. 피부 재생 및 보습.", "price": 28000, "tags": ["skincare", "serum", "repair", "Korean"]},
    {"category": "skincare", "brand": "The Ordinary", "name": "나이아신아마이드 10% 세럼", "desc": "모공 개선, 피부 톤 균일화. 부담 없는 가격.", "price": 12000, "tags": ["skincare", "serum", "pore", "brightening"]},
    {"category": "skincare", "brand": "Sulwhasoo", "name": "윤조에센스", "desc": "한방 성분 기반 에센스. 피부 활력과 탄력 개선.", "price": 120000, "tags": ["skincare", "essence", "luxury", "herbal"]},
    {"category": "skincare", "brand": "Belif", "name": "트루 크림 아쿠아 밤", "desc": "오트밀 추출물 함유 수분크림. 민감성 피부 적합.", "price": 38000, "tags": ["skincare", "moisturizer", "sensitive", "daily"]},
    {"category": "skincare", "brand": "Klairs", "name": "비타민 C 세럼", "desc": "5% 비타민C 함유. 미백 및 항산화 효과.", "price": 32000, "tags": ["skincare", "serum", "brightening", "vitamin"]},
    {"category": "skincare", "brand": "Etude House", "name": "순정 콜라겐 앰플", "desc": "콜라겐 고농도 앰플. 탄력 개선 및 주름 완화.", "price": 18000, "tags": ["skincare", "ampoule", "anti-aging", "collagen"]},
    {"category": "skincare", "brand": "Missha", "name": "타임레볼루션 에센스", "desc": "효모 발효 추출물 함유. 피부 장벽 강화.", "price": 65000, "tags": ["skincare", "essence", "ferment", "barrier"]},

    # fashion (15)
    {"category": "fashion", "brand": "ZARA", "name": "오버핏 리넨 셔츠", "desc": "편안한 오버핏 리넨 소재 셔츠. 여름 필수 아이템.", "price": 59000, "tags": ["fashion", "shirt", "linen", "casual"]},
    {"category": "fashion", "brand": "H&M", "name": "슬림 치노 팬츠", "desc": "스트레치 소재 슬림핏 치노 팬츠. 오피스룩에 적합.", "price": 39000, "tags": ["fashion", "pants", "office", "slim"]},
    {"category": "fashion", "brand": "Uniqlo", "name": "에어리즘 V넥 티셔츠", "desc": "흡습속건 소재의 V넥 티셔츠. 사계절 데일리룩.", "price": 19900, "tags": ["fashion", "tshirt", "basic", "daily"]},
    {"category": "fashion", "brand": "Musinsa Standard", "name": "오버핏 후드 집업", "desc": "두꺼운 원단의 오버핏 후드 집업. 스트릿 스타일.", "price": 69000, "tags": ["fashion", "hoodie", "street", "oversized"]},
    {"category": "fashion", "brand": "Adidas", "name": "클래식 트랙 재킷", "desc": "아디다스 클래식 스트라이프 트랙 재킷. 레트로 스타일.", "price": 89000, "tags": ["fashion", "jacket", "sport", "retro"]},
    {"category": "fashion", "brand": "Nike", "name": "테크 플리스 조거", "desc": "테크 플리스 소재 조거 팬츠. 애슬레저 필수템.", "price": 109000, "tags": ["fashion", "pants", "athleisure", "comfort"]},
    {"category": "fashion", "brand": "Levi's", "name": "501 오리지널 청바지", "desc": "클래식 스트레이트 핏 청바지. 시대를 초월한 디자인.", "price": 129000, "tags": ["fashion", "jeans", "classic", "denim"]},
    {"category": "fashion", "brand": "Ralph Lauren", "name": "폴로 피케 셔츠", "desc": "클래식 폴로 피케 셔츠. 비즈니스 캐주얼에 완벽.", "price": 119000, "tags": ["fashion", "polo", "classic", "preppy"]},
    {"category": "fashion", "brand": "Tommy Hilfiger", "name": "스트라이프 네이비 셔츠", "desc": "아이코닉 스트라이프 패턴 셔츠. 아메리칸 클래식.", "price": 99000, "tags": ["fashion", "shirt", "stripe", "classic"]},
    {"category": "fashion", "brand": "Gap", "name": "로고 크루넥 스웨터", "desc": "소프트 코튼 크루넥 스웨터. 미니멀 로고 디자인.", "price": 79000, "tags": ["fashion", "sweater", "basic", "casual"]},
    {"category": "fashion", "brand": "COS", "name": "와이드 레그 슬랙스", "desc": "모던 실루엣 와이드 레그 팬츠. 미니멀 디자인.", "price": 129000, "tags": ["fashion", "pants", "wide", "minimal"]},
    {"category": "fashion", "brand": "Arket", "name": "울 블렌드 코트", "desc": "울 혼방 클래식 코트. 시즌리스 아이템.", "price": 399000, "tags": ["fashion", "coat", "wool", "classic"]},
    {"category": "fashion", "brand": "& Other Stories", "name": "플리츠 미디 스커트", "desc": "우아한 플리츠 미디 스커트. 다양한 상의와 매치 가능.", "price": 149000, "tags": ["fashion", "skirt", "feminine", "elegant"]},
    {"category": "fashion", "brand": "Mango", "name": "더블 브레스트 블레이저", "desc": "세련된 더블 브레스트 블레이저. 오피스룩의 완성.", "price": 179000, "tags": ["fashion", "blazer", "office", "chic"]},
    {"category": "fashion", "brand": "Pull&Bear", "name": "카고 팬츠", "desc": "트렌디한 카고 팬츠. 스트릿 패션 필수템.", "price": 69000, "tags": ["fashion", "pants", "cargo", "street"]},

    # sports (10)
    {"category": "sports", "brand": "Nike", "name": "에어맥스 270", "desc": "에어쿠션 기술로 하루 종일 편안한 러닝화. 스타일과 기능 모두.", "price": 189000, "tags": ["sports", "shoes", "running", "air"]},
    {"category": "sports", "brand": "Adidas", "name": "울트라부스트 23", "desc": "부스트 쿠션 기술 탑재. 마라톤부터 일상까지.", "price": 219000, "tags": ["sports", "shoes", "running", "boost"]},
    {"category": "sports", "brand": "Lululemon", "name": "알라인 요가 레깅스", "desc": "초부드러운 나일론 소재 레깅스. 요가 및 필라테스 최적.", "price": 149000, "tags": ["sports", "yoga", "leggings", "active"]},
    {"category": "sports", "brand": "Under Armour", "name": "테크 2.0 티셔츠", "desc": "빠른 건조 소재의 퍼포먼스 티셔츠. 땀 냄새 방지.", "price": 45000, "tags": ["sports", "tshirt", "performance", "gym"]},
    {"category": "sports", "brand": "Garmin", "name": "포어러너 265 스마트워치", "desc": "GPS 러닝 워치. 심박수, 스트레스 모니터링.", "price": 599000, "tags": ["sports", "watch", "GPS", "health"]},
    {"category": "sports", "brand": "Theragun", "name": "미니 마사지건", "desc": "휴대용 근육 마사지건. 운동 후 회복에 최적.", "price": 249000, "tags": ["sports", "recovery", "massage", "health"]},
    {"category": "sports", "brand": "Reebok", "name": "나노 X3 크로스핏화", "desc": "크로스핏 전용 트레이닝화. 안정성과 유연성의 균형.", "price": 169000, "tags": ["sports", "shoes", "crossfit", "training"]},
    {"category": "sports", "brand": "GNC", "name": "프로 퍼포먼스 단백질", "desc": "유청 단백질 25g 함유. 초콜릿 맛. 근육 회복 지원.", "price": 89000, "tags": ["sports", "protein", "supplement", "gym"]},
    {"category": "sports", "brand": "YETI", "name": "람블러 텀블러 30oz", "desc": "18/8 스테인리스 스틸. 24시간 냉온 유지.", "price": 79000, "tags": ["sports", "bottle", "outdoor", "daily"]},
    {"category": "sports", "brand": "On Running", "name": "클라우드 러닝화", "desc": "스위스 엔지니어링의 클라우드 쿠션 러닝화.", "price": 229000, "tags": ["sports", "shoes", "running", "Swiss"]},

    # food (10)
    {"category": "food", "brand": "Loacker", "name": "웨하스 초콜릿", "desc": "이탈리아 전통 웨하스에 진한 초콜릿 코팅. 달콤한 오후의 행복.", "price": 8500, "tags": ["food", "snack", "chocolate", "sweet"]},
    {"category": "food", "brand": "Pepero", "name": "아몬드 페페로", "desc": "바삭한 아몬드가 가득한 페페로. 선물용으로도 인기.", "price": 1500, "tags": ["food", "snack", "chocolate", "Korean"]},
    {"category": "food", "brand": "Starbucks", "name": "콜드브루 원두커피", "desc": "스타벅스 시그니처 콜드브루. 부드럽고 깊은 커피 맛.", "price": 6500, "tags": ["food", "coffee", "cold brew", "daily"]},
    {"category": "food", "brand": "Nongshim", "name": "신라면 멀티팩", "desc": "매콤한 소고기 국물의 대표 라면. 5개입 묶음.", "price": 4500, "tags": ["food", "ramen", "spicy", "Korean"]},
    {"category": "food", "brand": "Häagen-Dazs", "name": "마카다미아 너트 아이스크림", "desc": "진한 크림과 마카다미아의 조화. 프리미엄 아이스크림.", "price": 12000, "tags": ["food", "icecream", "dessert", "premium"]},
    {"category": "food", "brand": "Oreo", "name": "더블 스터프 쿠키", "desc": "두 배 두꺼운 크림 필링의 오레오. 우유와 환상의 짝꿍.", "price": 5000, "tags": ["food", "cookie", "snack", "sweet"]},
    {"category": "food", "brand": "Pringles", "name": "사워크림 어니언 칩스", "desc": "크리스피하고 맛있는 프링글스. 파티용 대형 사이즈.", "price": 4000, "tags": ["food", "chips", "snack", "party"]},
    {"category": "food", "brand": "Lindt", "name": "엑스트라 다크 초콜릿 90%", "desc": "강렬한 카카오 풍미의 다크 초콜릿. 항산화 성분 풍부.", "price": 9000, "tags": ["food", "chocolate", "dark", "premium"]},
    {"category": "food", "brand": "CJ", "name": "비비고 왕만두", "desc": "꽉 찬 속재료의 대왕 만두. 찜, 구이, 에어프라이어 모두 가능.", "price": 8900, "tags": ["food", "dumpling", "Korean", "meal"]},
    {"category": "food", "brand": "Twix", "name": "트윅스 초콜릿 바", "desc": "바삭한 쿠키 위에 캐러멜과 초콜릿. 달콤한 에너지 충전.", "price": 2000, "tags": ["food", "chocolate", "caramel", "snack"]},

    # tech (10)
    {"category": "tech", "brand": "Sony", "name": "WH-1000XM5 헤드폰", "desc": "업계 최고 수준의 노이즈 캔슬링. 30시간 배터리 지속.", "price": 459000, "tags": ["tech", "headphone", "ANC", "audio"]},
    {"category": "tech", "brand": "Apple", "name": "AirPods Pro 2세대", "desc": "액티브 노이즈 캔슬링 이어폰. 공간 음향 지원.", "price": 359000, "tags": ["tech", "earbuds", "ANC", "Apple"]},
    {"category": "tech", "brand": "Samsung", "name": "갤럭시 버즈 3 Pro", "desc": "고음질 무선 이어폰. 지능형 노이즈 캔슬링.", "price": 299000, "tags": ["tech", "earbuds", "Samsung", "wireless"]},
    {"category": "tech", "brand": "Anker", "name": "65W GaN 충전기", "desc": "초소형 고속 충전기. 노트북·스마트폰 동시 충전 가능.", "price": 49000, "tags": ["tech", "charger", "fast", "portable"]},
    {"category": "tech", "brand": "Belkin", "name": "MagSafe 무선 충전기", "desc": "아이폰 MagSafe 호환 15W 무선 충전기.", "price": 69000, "tags": ["tech", "charger", "wireless", "Apple"]},
    {"category": "tech", "brand": "Logitech", "name": "MX Master 3S 마우스", "desc": "크리에이터를 위한 고성능 무선 마우스. 8000DPI.", "price": 139000, "tags": ["tech", "mouse", "wireless", "productivity"]},
    {"category": "tech", "brand": "Kindle", "name": "킨들 페이퍼화이트 16GB", "desc": "눈부심 없는 300ppi 전자책 리더기. 방수 기능.", "price": 219000, "tags": ["tech", "ereader", "book", "portable"]},
    {"category": "tech", "brand": "GoPro", "name": "Hero 13 액션캠", "desc": "5.3K 울트라 HD 액션캠. 방수 10m.", "price": 599000, "tags": ["tech", "camera", "action", "outdoor"]},
    {"category": "tech", "brand": "JBL", "name": "플립 6 블루투스 스피커", "desc": "방수 방진 포터블 스피커. 12시간 재생.", "price": 189000, "tags": ["tech", "speaker", "bluetooth", "outdoor"]},
    {"category": "tech", "brand": "Baseus", "name": "20000mAh 보조배터리", "desc": "대용량 65W 고속 충전 보조배터리. 노트북도 충전 가능.", "price": 89000, "tags": ["tech", "battery", "portable", "fast"]},

    # travel (10)
    {"category": "travel", "brand": "Samsonite", "name": "코스모라이트 캐리어 28인치", "desc": "초경량 하드케이스 캐리어. 4륜 스피너 휠.", "price": 590000, "tags": ["travel", "luggage", "lightweight", "premium"]},
    {"category": "travel", "brand": "Rimowa", "name": "에센셜 라이트 체크인 M", "desc": "폴리카보네이트 하드쉘 캐리어. 멀티휠 시스템.", "price": 890000, "tags": ["travel", "luggage", "luxury", "carry-on"]},
    {"category": "travel", "brand": "Osprey", "name": "파세크 24L 데이팩", "desc": "인체공학적 배낭. 하이킹 및 여행 겸용.", "price": 179000, "tags": ["travel", "backpack", "hiking", "outdoor"]},
    {"category": "travel", "brand": "Eagle Creek", "name": "패킹 큐브 세트", "desc": "여행 수납 정리 큐브 4종 세트. 짐 정리 필수품.", "price": 59000, "tags": ["travel", "packing", "organize", "essential"]},
    {"category": "travel", "brand": "Sea to Summit", "name": "울트라라이트 여행 타월", "desc": "초경량 속건 여행용 타월. 컴팩트하게 접힘.", "price": 45000, "tags": ["travel", "towel", "lightweight", "outdoor"]},
    {"category": "travel", "brand": "Bose", "name": "QuietComfort 45 헤드폰", "desc": "장거리 비행을 위한 노이즈캔슬링 헤드폰.", "price": 399000, "tags": ["travel", "headphone", "ANC", "flight"]},
    {"category": "travel", "brand": "Lonely Planet", "name": "일본 여행 가이드북", "desc": "최신 정보가 담긴 일본 여행 필수 가이드북.", "price": 28000, "tags": ["travel", "book", "guide", "Japan"]},
    {"category": "travel", "brand": "Nomad", "name": "여행용 멀티 어댑터", "desc": "150개국 호환 멀티 여행용 어댑터. USB-A/C 포함.", "price": 39000, "tags": ["travel", "adapter", "essential", "worldwide"]},
    {"category": "travel", "brand": "Hydro Flask", "name": "32oz 트레블 텀블러", "desc": "진공 단열 스테인리스 텀블러. 여행 필수 보온병.", "price": 79000, "tags": ["travel", "bottle", "insulated", "outdoor"]},
    {"category": "travel", "brand": "Away", "name": "캐리온 알루미늄 캐리어", "desc": "항공사 규격의 알루미늄 기내 반입 캐리어.", "price": 750000, "tags": ["travel", "luggage", "carry-on", "aluminum"]},

    # home (10)
    {"category": "home", "brand": "Dyson", "name": "V15 무선 청소기", "desc": "강력한 흡입력의 무선 스틱 청소기. 레이저 먼지 감지.", "price": 1290000, "tags": ["home", "vacuum", "cleaning", "premium"]},
    {"category": "home", "brand": "Philips Hue", "name": "스마트 LED 스타터팩", "desc": "색온도 조절 가능한 스마트 전구 3개 + 허브.", "price": 199000, "tags": ["home", "smart", "lighting", "IoT"]},
    {"category": "home", "brand": "MUJI", "name": "아로마 디퓨저", "desc": "초음파 방식의 미니 아로마 디퓨저. 7가지 LED 조명.", "price": 49000, "tags": ["home", "aroma", "diffuser", "relax"]},
    {"category": "home", "brand": "Nespresso", "name": "버추오 넥스트 커피머신", "desc": "캡슐형 커피머신. 에스프레소부터 알토까지.", "price": 299000, "tags": ["home", "coffee", "machine", "kitchen"]},
    {"category": "home", "brand": "IKEA", "name": "KALLAX 선반장", "desc": "모듈식 선반장. 취향에 맞게 구성 가능.", "price": 159000, "tags": ["home", "furniture", "storage", "minimal"]},
    {"category": "home", "brand": "Coway", "name": "아이콘 공기청정기", "desc": "4단계 필터링 공기청정기. 스마트 공기질 모니터링.", "price": 399000, "tags": ["home", "air purifier", "health", "smart"]},
    {"category": "home", "brand": "Cuisinart", "name": "14컵 스마트 밥솥", "desc": "다기능 전기압력밥솥. 에너지 절약 모드.", "price": 129000, "tags": ["home", "rice cooker", "kitchen", "cooking"]},
    {"category": "home", "brand": "Yankee Candle", "name": "클린 코튼 캔들 라지", "desc": "깨끗한 코튼 향의 대형 향초. 최대 150시간 연소.", "price": 45000, "tags": ["home", "candle", "aroma", "cozy"]},
    {"category": "home", "brand": "Umbra", "name": "플루토 거울", "desc": "모던한 골드 프레임 벽걸이 거울. 인테리어 포인트.", "price": 89000, "tags": ["home", "mirror", "decor", "modern"]},
    {"category": "home", "brand": "Instant Pot", "name": "듀오 7in1 전기 압력솥", "desc": "압력솥, 슬로우쿠커, 밥솥 등 7가지 기능.", "price": 179000, "tags": ["home", "cooker", "kitchen", "multifunctional"]},

    # health (10)
    {"category": "health", "brand": "Centrum", "name": "멀티비타민 100정", "desc": "23가지 비타민&미네랄 복합 영양제. 면역 및 활력.", "price": 35000, "tags": ["health", "vitamin", "supplement", "daily"]},
    {"category": "health", "brand": "Omega 3 Plus", "name": "오메가3 90캡슐", "desc": "rTG형 오메가3. 혈관 건강 및 두뇌 활동 지원.", "price": 42000, "tags": ["health", "omega3", "supplement", "heart"]},
    {"category": "health", "brand": "Manduka", "name": "PRO 요가매트 6mm", "desc": "프로 전용 두꺼운 요가매트. 미끄럼 방지.", "price": 219000, "tags": ["health", "yoga", "mat", "fitness"]},
    {"category": "health", "brand": "Fitbit", "name": "버사 4 스마트워치", "desc": "건강 추적 스마트워치. 수면, 심박, 스트레스 모니터링.", "price": 329000, "tags": ["health", "wearable", "tracker", "sleep"]},
    {"category": "health", "brand": "Collagen Plus", "name": "저분자 콜라겐 펩타이드", "desc": "피부, 관절, 뼈 건강을 위한 콜라겐 파우더.", "price": 55000, "tags": ["health", "collagen", "supplement", "beauty"]},
    {"category": "health", "brand": "Resistance Band Pro", "name": "저항 밴드 5종 세트", "desc": "홈트 필수 저항 밴드. 강도별 5단계 구성.", "price": 29000, "tags": ["health", "fitness", "home workout", "resistance"]},
    {"category": "health", "brand": "BSN", "name": "시너지ISO 단백질 셰이크", "desc": "낮은 칼로리 고단백 아이솔레이트. 25g 단백질.", "price": 79000, "tags": ["health", "protein", "supplement", "muscle"]},
    {"category": "health", "brand": "Melatonin Max", "name": "멜라토닌 수면 보조제", "desc": "5mg 멜라토닌 함유. 수면 리듬 정상화 도움.", "price": 22000, "tags": ["health", "sleep", "supplement", "wellness"]},
    {"category": "health", "brand": "Foam Roller Pro", "name": "그리드 폼롤러", "desc": "근막 이완 전용 폼롤러. 운동 전후 스트레칭.", "price": 39000, "tags": ["health", "recovery", "massage", "fitness"]},
    {"category": "health", "brand": "Probiotics Lab", "name": "프리미엄 유산균 30포", "desc": "100억 CFU 유산균. 장 건강 및 면역 강화.", "price": 48000, "tags": ["health", "probiotic", "gut", "supplement"]},
]

CONTENT_TYPES = ["post", "review", "story", "reel", "ad_creative"]
CONTENT_TEMPLATES = [
    {"type": "post",        "tmpl": "{brand} {product}를 써봤는데 정말 대박이에요! {desc} #일상 #{tag}"},
    {"type": "review",      "tmpl": "{brand} {product} 솔직 리뷰 🔍 장점: {desc} 별점: ⭐⭐⭐⭐⭐ #{tag}"},
    {"type": "story",       "tmpl": "오늘의 픽 ✨ {brand} {product}. {desc} 링크는 바이오에!"},
    {"type": "reel",        "tmpl": "{product} 언박싱 🎁 {brand}에서 새로 나온 {product}. {desc} #shorts #{tag}"},
    {"type": "ad_creative", "tmpl": "[광고] {brand} {product} 지금 특가! {desc} 자세한 내용은 프로필 링크 클릭 👆 #{tag}"},
]


# ══════════════════════════════════════════════════════════════
# DB 연결
# ══════════════════════════════════════════════════════════════

def get_connection():
    return psycopg2.connect(
        host=os.getenv("POSTGRES_HOST", "localhost"),
        port=int(os.getenv("POSTGRES_PORT", "5432")),
        dbname=os.getenv("POSTGRES_DB", "ai_agent"),
        user=os.getenv("POSTGRES_USER", "postgres"),
        password=os.getenv("POSTGRES_PASSWORD", "postgres"),
        cursor_factory=psycopg2.extras.RealDictCursor,
    )


# ══════════════════════════════════════════════════════════════
# 임베딩 배치 생성
# ══════════════════════════════════════════════════════════════

def batch_embed(model, texts: list[str], task_type: str = "RETRIEVAL_DOCUMENT") -> list[list[float]]:
    results = []
    for i in range(0, len(texts), BATCH_SIZE):
        batch = texts[i:i + BATCH_SIZE]
        inputs = [TextEmbeddingInput(t, task_type) for t in batch]
        resp = model.get_embeddings(inputs)
        results.extend([e.values for e in resp])
        logger.info(f"  임베딩 생성: {min(i + BATCH_SIZE, len(texts))}/{len(texts)}")
    return results


# ══════════════════════════════════════════════════════════════
# 데이터 생성
# ══════════════════════════════════════════════════════════════

def build_users() -> list[dict]:
    users = []
    for i, name in enumerate(KOREAN_NAMES):
        categories = random.sample(list(INTEREST_POOLS.keys()), k=random.randint(2, 4))
        interests = []
        for cat in categories:
            interests.extend(random.sample(INTEREST_POOLS[cat], k=1))
        activities = []
        for cat in categories[:2]:
            activities.extend(random.sample(ACTIVITY_TEMPLATES[cat], k=2))

        profile = {
            "name": name,
            "age": random.randint(20, 45),
            "interests": interests,
            "mindset": random.choice(MINDSETS),
            "recent_activities": activities,
            "vector_summary": f"{', '.join(categories)} 관심, {random.randint(20,45)}대, {random.choice(MINDSETS)} 성향",
        }
        users.append({"user_id": f"user_{i+1:03d}", "profile": profile})
    return users


def build_products() -> list[dict]:
    items = []
    for i, p in enumerate(PRODUCTS):
        product_data = {
            "name": p["name"],
            "brand": p["brand"],
            "category": p["category"],
            "description": p["desc"],
            "price": p["price"],
            "image_url": f"https://picsum.photos/seed/{p['brand'].lower().replace(' ', '-')}-{i}/400/400",
        }
        items.append({
            "product_id": f"prod_{i+1:03d}",
            "brand_id": p["brand"],
            "product_data": product_data,
            "tags": p["tags"],
            "embed_text": f"{p['name']} {p['desc']} {' '.join(p['tags'])}",
        })
    return items


def build_campaigns(products: list[dict]) -> list[dict]:
    campaigns = []
    for i, p in enumerate(products):
        data = p["product_data"]
        campaign_data = {
            "ad_id": f"ad_{i+1:03d}",
            "product": data["name"],
            "brand": data["brand"],
            "category": data["category"],
            "description": data["description"],
            "bid": round(random.uniform(0.5, 6.0), 1),
            "image_url": data["image_url"],
        }
        campaigns.append({
            "campaign_id": f"camp_{i+1:03d}",
            "brand_id": data["brand"],
            "campaign_data": campaign_data,
            "targeting_rules": {"tags": p["tags"]},
            "embed_text": f"{data['name']} {data['description']} {' '.join(p['tags'])}",
        })
    return campaigns


def build_contents(products: list[dict]) -> list[dict]:
    contents = []
    for i in range(100):
        p = random.choice(products)
        data = p["product_data"]
        tmpl = random.choice(CONTENT_TEMPLATES)
        tag = random.choice(p["tags"])
        text = tmpl["tmpl"].format(
            brand=data["brand"], product=data["name"],
            desc=data["description"][:30], tag=tag
        )
        metadata = {
            "text": text,
            "product_id": p["product_id"],
            "brand": data["brand"],
            "category": data["category"],
            "image_url": data["image_url"],
        }
        contents.append({
            "content_id": f"cont_{i+1:03d}",
            "content_type": tmpl["type"],
            "metadata": metadata,
            "embed_text": text,
        })
    return contents


# ══════════════════════════════════════════════════════════════
# DB 삽입
# ══════════════════════════════════════════════════════════════

def insert_users(conn, users, embeddings_long, embeddings_short):
    with conn.cursor() as cur:
        for u, ev_long, ev_short in zip(users, embeddings_long, embeddings_short):
            cur.execute(
                """INSERT INTO users (user_id, profile, long_term_vector, short_term_vector)
                   VALUES (%s, %s, %s::vector, %s::vector)
                   ON CONFLICT (user_id) DO UPDATE
                   SET profile = EXCLUDED.profile,
                       long_term_vector = EXCLUDED.long_term_vector,
                       short_term_vector = EXCLUDED.short_term_vector""",
                (u["user_id"], json.dumps(u["profile"], ensure_ascii=False), ev_long, ev_short),
            )
    logger.info(f"사용자 {len(users)}명 삽입 완료")


def insert_products(conn, products, embeddings):
    with conn.cursor() as cur:
        for p, emb in zip(products, embeddings):
            cur.execute(
                """INSERT INTO products (product_id, brand_id, product_data, embedding)
                   VALUES (%s, %s, %s, %s::vector)
                   ON CONFLICT (product_id) DO UPDATE
                   SET product_data = EXCLUDED.product_data,
                       embedding = EXCLUDED.embedding""",
                (p["product_id"], p["brand_id"],
                 json.dumps(p["product_data"], ensure_ascii=False), emb),
            )
    logger.info(f"상품 {len(products)}개 삽입 완료")


def insert_campaigns(conn, campaigns, embeddings):
    with conn.cursor() as cur:
        for c, emb in zip(campaigns, embeddings):
            cur.execute(
                """INSERT INTO campaigns (campaign_id, brand_id, campaign_data, targeting_rules, embedding)
                   VALUES (%s, %s, %s, %s, %s::vector)
                   ON CONFLICT (campaign_id) DO UPDATE
                   SET campaign_data = EXCLUDED.campaign_data,
                       targeting_rules = EXCLUDED.targeting_rules,
                       embedding = EXCLUDED.embedding""",
                (c["campaign_id"], c["brand_id"],
                 json.dumps(c["campaign_data"], ensure_ascii=False),
                 json.dumps(c["targeting_rules"], ensure_ascii=False), emb),
            )
    logger.info(f"캠페인 {len(campaigns)}개 삽입 완료")


def insert_contents(conn, contents, embeddings):
    with conn.cursor() as cur:
        for c, emb in zip(contents, embeddings):
            cur.execute(
                """INSERT INTO contents (content_id, content_type, metadata, embedding)
                   VALUES (%s, %s, %s, %s::vector)
                   ON CONFLICT (content_id) DO UPDATE
                   SET content_type = EXCLUDED.content_type,
                       metadata = EXCLUDED.metadata,
                       embedding = EXCLUDED.embedding""",
                (c["content_id"], c["content_type"],
                 json.dumps(c["metadata"], ensure_ascii=False), emb),
            )
    logger.info(f"콘텐츠 {len(contents)}개 삽입 완료")


# ══════════════════════════════════════════════════════════════
# 메인
# ══════════════════════════════════════════════════════════════

def main():
    random.seed(42)

    logger.info(f"Vertex AI 초기화: project={PROJECT_ID}, model={EMBEDDING_MODEL}")
    vertexai.init(project=PROJECT_ID, location=REGION)
    model = TextEmbeddingModel.from_pretrained(EMBEDDING_MODEL)

    # 데이터 생성
    users = build_users()
    products = build_products()
    campaigns = build_campaigns(products)
    contents = build_contents(products)

    logger.info(f"생성: 사용자 {len(users)}명, 상품 {len(products)}개, 캠페인 {len(campaigns)}개, 콘텐츠 {len(contents)}개")

    # 임베딩 일괄 생성
    logger.info("=== 사용자 임베딩 생성 ===")
    user_long_texts  = [u["profile"]["vector_summary"] for u in users]
    user_short_texts = [" ".join(u["profile"]["recent_activities"]) for u in users]
    emb_user_long  = batch_embed(model, user_long_texts)
    emb_user_short = batch_embed(model, user_short_texts)

    logger.info("=== 상품 임베딩 생성 ===")
    emb_products = batch_embed(model, [p["embed_text"] for p in products])

    logger.info("=== 캠페인 임베딩 생성 ===")
    emb_campaigns = batch_embed(model, [c["embed_text"] for c in campaigns])

    logger.info("=== 콘텐츠 임베딩 생성 ===")
    emb_contents = batch_embed(model, [c["embed_text"] for c in contents])

    # DB 삽입
    logger.info("=== DB 삽입 ===")
    conn = get_connection()
    try:
        insert_users(conn, users, emb_user_long, emb_user_short)
        insert_products(conn, products, emb_products)
        insert_campaigns(conn, campaigns, emb_campaigns)
        insert_contents(conn, contents, emb_contents)
        conn.commit()
        logger.info("✅ 모든 데모 데이터 삽입 완료!")
    except Exception as e:
        conn.rollback()
        logger.error(f"오류: {e}", exc_info=True)
        sys.exit(1)
    finally:
        conn.close()


if __name__ == "__main__":
    main()
