# PiMS 및 온톨로지 설계

## 목차

1. [온톨로지 개요](#1-온톨로지-개요)
2. [PiMS 아키텍처](#2-pims-아키텍처)
3. [패션/주얼리/코스메틱 온톨로지](#3-패션주얼리코스메틱-온톨로지)
4. [그래프 DB 설계](#4-그래프-db-설계)
5. [LLM 자동화 파이프라인](#5-llm-자동화-파이프라인)
6. [VTO (Virtual Try-On) 설계](#6-vto-virtual-try-on-설계)

---

## 1. 온톨로지 개요

### 1.1 왜 온톨로지가 필요한가?

**문제:**
- UGC/벤더 입력이 예측 불가
- "오프화이트/아이보리/크림" → 같은 색상, 다른 표현
- "슬림핏/레귤러/기본핏" → 표준화 필요
- 코스메틱 "효능 보장" → 금지 표현

**해결:**
- 온톨로지 = "공통 분류체계 + 관계/제약 포함 스키마"
- AI가 이해하는 의미 스키마

### 1.2 데이터 저장 구조 분리

| 저장소 | 역할 | 데이터 유형 |
|--------|------|-----------|
| **RDB** | 운영 진실(SoT) | SKU, 가격, 재고, 옵션, 배송, 정산 |
| **Vector DB** | 유사도 검색 | 콘텐츠/상품/브랜드 임베딩 |
| **Graph DB** | 제약/관계/정책 | 브랜드-정책-권리-캠페인 연결 |

**권장:**
- 초기에 그래프 DB를 "모든 것"으로 시작하지 말고
- **브랜드-상품-캠페인-정책-권리**만 그래프로

---

## 2. PiMS 아키텍처

### 2.1 운영 스키마 vs AI 스키마 분리

```
┌──────────────────────────────────────────────────────────┐
│                    PiMS 운영 RDB (SoT)                   │
│  - SKU, 가격, 재고, 옵션                                  │
│  - 벤더, 정산, 계약                                       │
│  - 승인 워크플로우                                        │
└────────────────────┬─────────────────────────────────────┘
                     │
                     │ 변경 이벤트 (CDC/Event Bus)
                     │
                     ▼
┌──────────────────────────────────────────────────────────┐
│            AI 연료 토큰 (Representation Tokens)          │
│  - PT (Product Token): 정규화된 상품 속성                │
│  - BT (Brand Token): 브랜드 가이드/정책                   │
│  - ATK (Asset Token): 소재 권리/용도                      │
└────────────────────┬─────────────────────────────────────┘
                     │
                     │ 임베딩 생성
                     │
                     ▼
┌──────────────────────────────────────────────────────────┐
│                    Vector DB                             │
│  - 상품 임베딩 (semantic + style)                         │
│  - 브랜드 톤 임베딩                                        │
│  - 콘텐츠 임베딩                                           │
└──────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────┐
│                    Graph DB                              │
│  - 브랜드 - 로고스펙 - 정책룰                             │
│  - 캠페인 - 상품 - 브랜드                                 │
│  - 권리 - 소재                                             │
└──────────────────────────────────────────────────────────┘
```

### 2.2 토큰 스키마 설계

#### Product Token (PT)

```json
{
  "product_id": "P123",
  "version": 1,
  "source": "AI_AGENT",
  "created_at": "2026-02-24T10:00:00Z",

  "normalized": {
    "category_path": "COSMETIC>LIP>LIPSTICK",
    "attributes": {
      "shade_code": "LIP_023",
      "shade_name": "Rose Nude",
      "shade_lab": [52.1, 18.3, 9.2],
      "undertone": "WARM",
      "finish": "SATIN",
      "opacity": "MEDIUM",
      "product_type": "LIPSTICK"
    },
    "style_tags": ["natural", "daily", "mlbb"],
    "target_demographics": {
      "gender": ["WOMEN"],
      "age_range": [20, 39]
    }
  },

  "constraints": {
    "claims_allowed": ["moisturizing", "long_lasting"],
    "claims_forbidden": ["treatment", "cure", "medical"],
    "required_disclaimer": [
      "개인차가 있을 수 있습니다",
      "사용 전 패치테스트 권장"
    ],
    "logo_rules_ref": "logo_spec_001",
    "rights_scope_ref": "rights_001"
  },

  "embeddings": {
    "semantic_ref": "emb_sem_p123_v1",
    "style_ref": "emb_sty_p123_v1"
  }
}
```

#### Brand Token (BT)

```json
{
  "brand_id": "BR456",
  "version": 1,
  "source": "MANUAL",
  "created_at": "2026-02-24T10:00:00Z",

  "identity": {
    "name": "Beauty Brand X",
    "category": "COSMETIC",
    "tier": "PREMIUM",
    "country_of_origin": "KR"
  },

  "guidelines": {
    "logo_spec": {
      "min_size_px": 100,
      "clear_space_ratio": 0.2,
      "allowed_bg": ["LIGHT", "DARK"],
      "forbidden_transform": ["stretch", "rotate", "colorize"]
    },
    "tone_guide": {
      "dos": ["scientific", "trustworthy", "gentle"],
      "donts": ["aggressive", "exaggerated", "slang"],
      "examples": [
        "피부과학 연구로 탄생한",
        "매일 사용해도 안심"
      ]
    },
    "forbidden_phrases": [
      "치료", "완치", "의학적 효과",
      "즉각 효과", "100% 보장"
    ],
    "required_disclaimers": [
      "개인차가 있을 수 있습니다"
    ]
  },

  "assets": {
    "logo_primary": "gs://assets/logo_primary.png",
    "logo_variants": ["gs://assets/logo_white.png"],
    "fonts": ["Pretendard", "Noto Sans KR"],
    "color_palette": {
      "primary": "#FF6B9D",
      "secondary": "#FFC1E3",
      "accent": "#FFE5F1"
    }
  }
}
```

---

## 3. 패션/주얼리/코스메틱 온톨로지

### 3.1 공통 카테고리 트리 (v0)

```
ROOT
├── FASHION
│   ├── TOP (상의)
│   │   ├── TSHIRT
│   │   ├── SHIRT
│   │   ├── BLOUSE
│   │   └── KNIT
│   ├── BOTTOM (하의)
│   │   ├── JEANS
│   │   ├── PANTS
│   │   └── SKIRT
│   ├── OUTER (아우터)
│   │   ├── JACKET
│   │   ├── COAT
│   │   └── CARDIGAN
│   ├── ONEPIECE (원피스)
│   ├── SHOES (신발)
│   ├── BAG (가방)
│   └── ACCESSORY (패션소품)
│
├── JEWELRY
│   ├── RING (반지)
│   ├── NECKLACE (목걸이)
│   ├── EARRING (귀걸이)
│   ├── BRACELET (팔찌)
│   ├── BROOCH (브로치)
│   ├── WATCH (시계)
│   └── OTHER
│
└── COSMETIC
    ├── LIP (립)
    │   ├── LIPSTICK
    │   ├── TINT
    │   ├── GLOSS
    │   └── BALM
    ├── BASE (베이스)
    │   ├── FOUNDATION
    │   ├── CUSHION
    │   ├── CONCEALER
    │   └── PRIMER
    ├── EYE (아이)
    │   ├── EYESHADOW
    │   ├── EYELINER
    │   └── MASCARA
    ├── CHEEK (치크)
    ├── SKINCARE (스킨케어)
    ├── HAIR (헤어)
    ├── BODY (바디)
    └── TOOL (도구)
```

### 3.2 공통 속성 (모든 카테고리)

| Attribute Key | Type | Allowed Values | 필수 | 동의어 매핑 |
|--------------|------|----------------|------|------------|
| `brand_id` | string | BR### | ✓ | - |
| `category_path` | string | FASHION>TOP>TSHIRT | ✓ | 티셔츠→TSHIRT |
| `gender_target` | enum[] | WOMEN/MEN/UNISEX/KIDS | △ | 여성용→WOMEN |
| `age_target` | int[] | [20,39] | ✗ | 2030→[20,39] |
| `price_range` | enum | LOW/MID/HIGH/LUX | ✗ | 프리미엄→HIGH |
| `color_family` | enum | BLACK/WHITE/BEIGE/... | △ | 아이보리→BEIGE |
| `style_tags` | enum[] | MINIMAL/STREET/FEMININE | △ | 미니멀→MINIMAL |
| `season` | enum[] | SS/FW/ALL | ✗ | 사계절→ALL |
| `country_of_origin` | string | KR/JP/... | ✗ | - |
| `sensitive_flags` | json | {medical:false} | ✗ | - |

### 3.3 패션 속성

| Key | Type | Allowed Values | 필수 | 동의어 |
|-----|------|----------------|------|--------|
| `fabric` | enum[] | COTTON/LINEN/WOOL/POLY | △ | 면→COTTON |
| `fit` | enum | SLIM/REGULAR/OVERSIZE/WIDE | △ | 기본핏→REGULAR |
| `silhouette` | enum | STRAIGHT/A_LINE/BOX | ✗ | - |
| `pattern` | enum | SOLID/STRIPE/CHECK | ✗ | 체크→CHECK |
| `length` | enum | CROP/SHORT/MIDI/LONG | ✗ | 롱→LONG |
| `neckline` | enum | CREW/V/BOAT | ✗ | 라운드→CREW |
| `size_system` | enum | KR/US/EU/ALPHA | △ | S/M/L→ALPHA |
| `vto_ready` | bool | true/false | △ | - |

### 3.4 주얼리 속성

| Key | Type | Allowed Values | 필수 | 동의어 |
|-----|------|----------------|------|--------|
| `material` | enum[] | SILVER/GOLD_14K/GOLD_18K/PLATINUM | ✓ | 14k→GOLD_14K |
| `plating` | enum | NONE/RHODIUM/GOLD_PLATED | ✗ | 로듐→RHODIUM |
| `stone_type` | enum[] | DIAMOND/PEARL/CZ | ✗ | 진주→PEARL |
| `stone_grade` | string | VVS1 | ✗ | - |
| `size_spec` | json | {ring_kor:12} | △ | - |
| `allergy_info` | enum[] | NICKEL_FREE/HYPOALLERGENIC | △ | 니켈프리→NICKEL_FREE |
| `care_notice` | string | - | ✗ | - |

### 3.5 코스메틱 속성 (자동화 핵심)

| Key | Type | Allowed Values | 필수 | 동의어 |
|-----|------|----------------|------|--------|
| `product_type` | enum | LIPSTICK/TINT/GLOSS/BALM | ✓ | 립틴트→TINT |
| `shade_name` | string | "Rose Nude" | △ | - |
| `shade_code` | string | LIP_023 | △ | - |
| `shade_lab` | float[3] | [52.1, 18.3, 9.2] | △ | RGB/HEX 변환 |
| `undertone` | enum | WARM/COOL/NEUTRAL | △ | 웜톤→WARM |
| `finish` | enum | MATTE/SATIN/GLOSSY | △ | 글로시→GLOSSY |
| `opacity` | enum | SHEER/MEDIUM/FULL | △ | - |
| `ingredients` | string[] | INCI list | △ | - |
| `skin_type` | enum[] | DRY/OILY/SENSITIVE | ✗ | 민감→SENSITIVE |
| `claims_allowed` | enum[] | MOISTURIZING/SOOTHING | △ | - |
| `claims_forbidden` | enum[] | TREATMENT/CURE | △ | 치료→TREATMENT |
| `required_disclaimer` | string[] | 고지문 텍스트 | △ | - |
| `swatch_assets` | asset_id[] | - | △ | - |

---

## 4. 그래프 DB 설계

### 4.1 노드 타입

#### A) Brand
```
properties:
- brand_id (unique)
- name
- status (ACTIVE/INACTIVE)
- updated_at
```

#### B) Product
```
properties:
- product_id (unique)
- category (FASHION/JEWELRY/COSMETIC)
- status (ACTIVE/INACTIVE)
- updated_at
```

#### C) Campaign
```
properties:
- campaign_id (unique)
- objective (AWARENESS/CTR/CVR/ROAS)
- status (ACTIVE/PAUSED/ENDED)
- start_at
- end_at
```

#### D) Asset
```
properties:
- asset_id (unique)
- asset_type (LOGO/PRODUCT_IMAGE/LOOKBOOK/SWATCH/FONT/BGM/TEMPLATE/VIDEO)
- uri
- checksum
- status (ACTIVE/REVOKED)
- created_at
- updated_at
```

#### E) RightsPolicy
```
properties:
- rights_id (unique)
- scope (IN_APP/AD/EXTERNAL/ALL)
- territory (KR/JP/ALL)
- expires_at (nullable)
- owner (BRAND/VENDOR/THIRD_PARTY)
- notes
```

#### F) PolicyRule
```
properties:
- rule_id (unique)
- rule_type (FORBIDDEN_PHRASE/REQUIRED_DISCLAIMER/CLAIM_ALLOWED/CLAIM_FORBIDDEN/PLACEMENT_RULE)
- severity (BLOCK/WARN)
- applies_to (COSMETIC/FASHION/JEWELRY/ALL)
- version
- payload (json)
```

#### G) LogoSpec
```
properties:
- logo_spec_id (unique)
- min_size_px
- clear_space_ratio
- allowed_bg (LIGHT/DARK/ANY)
- forbidden_transform (json)
- version
```

#### H) ToneGuide
```
properties:
- tone_id (unique)
- dos (json array)
- donts (json array)
- examples (json array)
- version
```

### 4.2 엣지 타입

```
브랜드/정책/권리 체인:
(Brand)-[:HAS_LOGO_SPEC]->(LogoSpec)
(Brand)-[:HAS_TONE_GUIDE]->(ToneGuide)
(Brand)-[:HAS_POLICY_RULE {priority:int}]->(PolicyRule)
(Asset)-[:LICENSED_BY]->(RightsPolicy)
(Brand)-[:OWNS_ASSET]->(Asset)

캠페인/상품 적격성:
(Product)-[:BELONGS_TO]->(Brand)
(Campaign)-[:PROMOTES]->(Product)
(Campaign)-[:USES_ASSET]->(Asset)
(Campaign)-[:HAS_POLICY_RULE]->(PolicyRule)
(Product)-[:HAS_POLICY_RULE]->(PolicyRule)
```

### 4.3 Cypher 쿼리 예시

#### Q1) 캠페인에 연결된 상품과 브랜드
```cypher
MATCH (c:Campaign {campaign_id: $campaign_id})-[:PROMOTES]->(p:Product)-[:BELONGS_TO]->(b:Brand)
RETURN c.campaign_id, p.product_id, b.brand_id, b.name;
```

#### Q2) 캠페인에서 사용 가능한 Asset (권리 체크 포함)
```cypher
MATCH (c:Campaign {campaign_id: $campaign_id})-[:USES_ASSET]->(a:Asset)-[:LICENSED_BY]->(r:RightsPolicy)
WHERE a.status = 'ACTIVE'
  AND (r.expires_at IS NULL OR r.expires_at > datetime())
  AND r.scope IN ['IN_APP', 'AD', 'ALL']
RETURN a.asset_id, a.asset_type, a.uri, r.scope, r.expires_at;
```

#### Q3) 브랜드 로고 스펙/톤 가이드 조회
```cypher
MATCH (b:Brand {brand_id: $brand_id})
OPTIONAL MATCH (b)-[:HAS_LOGO_SPEC]->(ls:LogoSpec)
OPTIONAL MATCH (b)-[:HAS_TONE_GUIDE]->(tg:ToneGuide)
RETURN b.brand_id, ls, tg;
```

#### Q4) 코스메틱 금칙 문구 조회
```cypher
MATCH (b:Brand {brand_id: $brand_id})-[:HAS_POLICY_RULE]->(r1:PolicyRule {rule_type:'FORBIDDEN_PHRASE'})
OPTIONAL MATCH (c:Campaign {campaign_id: $campaign_id})-[:HAS_POLICY_RULE]->(r2:PolicyRule {rule_type:'FORBIDDEN_PHRASE'})
WHERE r1.applies_to IN ['COSMETIC', 'ALL']
RETURN collect(DISTINCT r1.payload) AS brand_forbidden,
       collect(DISTINCT r2.payload) AS campaign_forbidden;
```

#### Q5) 후보 상품 적격성 필터링
```cypher
MATCH (p:Product)-[:BELONGS_TO]->(b:Brand)
WHERE p.product_id IN $product_ids
  AND p.status = 'ACTIVE'
  AND b.status = 'ACTIVE'
RETURN p.product_id, b.brand_id;
```

---

## 5. LLM 자동화 파이프라인

### 5.1 자동화 4단계

```
┌────────────────────────────────────────────────────────┐
│  1. LLM Extraction (구조화 추출)                       │
│     벤더 입력 텍스트/이미지 → JSON                     │
└────────────┬───────────────────────────────────────────┘
             │
┌────────────▼───────────────────────────────────────────┐
│  2. Normalization (표준 코드 매핑)                      │
│     "오프화이트" → COLOR_OFFWHITE                       │
└────────────┬───────────────────────────────────────────┘
             │
┌────────────▼───────────────────────────────────────────┐
│  3. Validation (제약 검증)                              │
│     JSON Schema + SHACL + 룰 체크                       │
└────────────┬───────────────────────────────────────────┘
             │
┌────────────▼───────────────────────────────────────────┐
│  4. Token Generation (PT/BT 생성 및 저장)               │
│     RDB + Vector + Graph 업데이트                       │
└────────────────────────────────────────────────────────┘
```

### 5.2 추출 프롬프트 템플릿

```python
EXTRACTION_PROMPT = """
You are a PiMS normalization engine. Extract structured information from product description.

Ontology Reference:
- Categories: {category_tree}
- Attributes: {attribute_schema}
- Allowed values: {allowed_values}

Product Description:
{product_description}

Images (if available):
{image_urls}

Extract the following information in JSON format:
{{
  "category_path": "COSMETIC>LIP>LIPSTICK",
  "attributes": {{
    "shade_name": "Rose Nude",
    "undertone": "WARM",
    "finish": "SATIN",
    ...
  }},
  "style_tags": ["natural", "daily"],
  "claims_detected": ["moisturizing", "long_lasting"],
  "potential_violations": []
}}

Rules:
1. Use ONLY allowed values from ontology
2. Map synonyms to standard codes
3. Flag potential policy violations
4. If uncertain, mark field as null

Output JSON only.
"""
```

### 5.3 정규화 사전 예시

```python
NORMALIZATION_DICT = {
    "color": {
        "오프화이트": "COLOR_OFFWHITE",
        "아이보리": "COLOR_OFFWHITE",
        "크림": "COLOR_OFFWHITE",
        "베이지": "COLOR_BEIGE",
        "누드": "COLOR_NUDE",
        # ...
    },
    "fit": {
        "슬림": "FIT_SLIM",
        "슬림핏": "FIT_SLIM",
        "타이트": "FIT_SLIM",
        "기본": "FIT_REGULAR",
        "레귤러": "FIT_REGULAR",
        "스탠다드": "FIT_REGULAR",
        "오버": "FIT_OVERSIZE",
        "루즈": "FIT_OVERSIZE",
        # ...
    },
    "finish": {
        "매트": "FINISH_MATTE",
        "무광": "FINISH_MATTE",
        "글로시": "FINISH_GLOSSY",
        "윤광": "FINISH_GLOSSY",
        "새틴": "FINISH_SATIN",
        # ...
    }
}

def normalize_value(field: str, raw_value: str) -> str:
    """동의어를 표준 코드로 매핑"""

    # 정규화 사전 조회
    mapping = NORMALIZATION_DICT.get(field, {})

    # 대소문자 무시 매칭
    normalized = mapping.get(raw_value.lower())

    if normalized:
        return normalized

    # 매칭 실패 시 경고
    logger.warning(f"No normalization for {field}={raw_value}")

    return raw_value  # 원본 반환
```

### 5.4 검증 규칙

```python
def validate_product_token(pt: dict) -> ValidationResult:
    """Product Token 검증"""

    errors = []
    warnings = []

    # 1. 필수 필드 체크
    required_fields = ["category_path", "attributes"]
    for field in required_fields:
        if field not in pt:
            errors.append(f"Missing required field: {field}")

    # 2. 카테고리 검증
    if not is_valid_category(pt.get("category_path")):
        errors.append(f"Invalid category: {pt.get('category_path')}")

    # 3. 코스메틱 특수 검증
    if pt.get("category_path", "").startswith("COSMETIC"):
        # 필수 속성 체크
        required_cosmetic_attrs = ["product_type", "shade_code"]
        for attr in required_cosmetic_attrs:
            if attr not in pt.get("attributes", {}):
                errors.append(f"Missing cosmetic attribute: {attr}")

        # 금칙 표현 체크
        claims_forbidden = pt.get("constraints", {}).get("claims_forbidden", [])
        description = pt.get("description", "")

        for forbidden in claims_forbidden:
            if forbidden in description:
                errors.append(f"Forbidden claim detected: {forbidden}")

    # 4. 일관성 체크
    if "shade_lab" in pt.get("attributes", {}):
        # LAB 값이 있으면 finish/opacity도 필요
        if "finish" not in pt.get("attributes", {}):
            warnings.append("shade_lab present but finish missing")

    return ValidationResult(
        passed=(len(errors) == 0),
        errors=errors,
        warnings=warnings
    )
```

---

## 6. VTO (Virtual Try-On) 설계

### 6.1 코스메틱 VTO (립스틱 예시)

```python
class CosmeticVTO:
    """코스메틱 Virtual Try-On"""

    async def apply_lipstick(
        self,
        selfie_image: Image,
        product: Product
    ) -> VTOResult:
        """셀카에 립스틱 적용"""

        # 1. Face Landmarks 감지
        landmarks = await self.detect_face_landmarks(selfie_image)

        # 2. 입술 영역 세그멘테이션
        lip_mask = self.segment_lips(selfie_image, landmarks)

        # 3. 제품 색상/질감 특성 로드
        shade = product.attributes["shade_lab"]  # LAB color space
        finish = product.attributes["finish"]  # MATTE/SATIN/GLOSSY
        opacity = product.attributes["opacity"]  # SHEER/MEDIUM/FULL

        # 4. 색상/질감 적용 (규칙 기반)
        result_image = self.apply_color_and_texture(
            selfie_image,
            lip_mask,
            shade=shade,
            finish=finish,
            opacity=opacity
        )

        # 5. 후처리 (광택/음영)
        if finish == "GLOSSY":
            result_image = self.add_gloss_effect(result_image, lip_mask)

        # 6. 품질 검증
        quality_check = self.verify_quality(selfie_image, result_image)

        return VTOResult(
            image=result_image,
            quality_score=quality_check.score,
            artifacts=quality_check.artifacts
        )

    async def detect_face_landmarks(
        self,
        image: Image
    ) -> FaceLandmarks:
        """MediaPipe Face Landmarker 사용"""

        # MediaPipe 호출
        landmarks = mediapipe_face_landmarker.detect(image)

        return FaceLandmarks(
            lips_upper=landmarks.lips_upper,
            lips_lower=landmarks.lips_lower,
            confidence=landmarks.confidence
        )

    def segment_lips(
        self,
        image: Image,
        landmarks: FaceLandmarks
    ) -> np.ndarray:
        """입술 마스크 생성"""

        mask = np.zeros(image.shape[:2], dtype=np.uint8)

        # 입술 랜드마크로 폴리곤 생성
        cv2.fillPoly(
            mask,
            [landmarks.lips_upper, landmarks.lips_lower],
            255
        )

        return mask

    def apply_color_and_texture(
        self,
        image: Image,
        mask: np.ndarray,
        shade: Tuple[float, float, float],
        finish: str,
        opacity: str
    ) -> Image:
        """색상 및 질감 적용 (물리 기반)"""

        # LAB → RGB 변환
        rgb_color = lab_to_rgb(shade)

        # 불투명도 계산
        alpha = {
            "SHEER": 0.4,
            "MEDIUM": 0.7,
            "FULL": 0.95
        }[opacity]

        # 입술 영역만 색상 적용
        result = image.copy()
        result[mask > 0] = (
            alpha * rgb_color +
            (1 - alpha) * image[mask > 0]
        )

        # 질감 효과
        if finish == "MATTE":
            result = self.apply_matte_texture(result, mask)
        elif finish == "SATIN":
            result = self.apply_satin_texture(result, mask)

        return result
```

### 6.2 패션 VTO (Vertex AI)

```python
class FashionVTO:
    """패션 Virtual Try-On (Vertex AI 활용)"""

    def __init__(self):
        self.vertex_client = aiplatform.gapic.PredictionServiceClient()

    async def try_on_garment(
        self,
        person_image: str,  # GCS path
        garment_image: str,  # GCS path
        garment_type: str  # "top" | "bottom" | "dress"
    ) -> VTOResult:
        """의류 가상 착용"""

        # Vertex AI Virtual Try-On API 호출
        endpoint = f"projects/{PROJECT_ID}/locations/{LOCATION}/publishers/google/models/imagegeneration@006"

        instances = [{
            "prompt": f"A person wearing {garment_type}",
            "personImage": {
                "gcsUri": person_image
            },
            "garmentImage": {
                "gcsUri": garment_image
            }
        }]

        parameters = {
            "sampleCount": 1,
            "mode": "tryon"
        }

        response = await self.vertex_client.predict(
            endpoint=endpoint,
            instances=instances,
            parameters=parameters
        )

        # 결과 처리
        result_image_gcs = response.predictions[0]["gcsUri"]

        return VTOResult(
            image_url=result_image_gcs,
            confidence=response.predictions[0].get("confidence", 0.0)
        )
```

---

## 7. 운영 가이드

### 7.1 온톨로지 업데이트 프로세스

```
1. 신규 속성/값 제안
   ↓
2. PM/도메인 전문가 검토
   ↓
3. 코드 테이블 업데이트
   ↓
4. 정규화 사전 업데이트
   ↓
5. 기존 PT 재생성 (마이그레이션)
   ↓
6. 임베딩 재생성
```

### 7.2 품질 모니터링

| 지표 | 목표 | 측정 방법 |
|------|------|----------|
| 추출 성공률 | >95% | 성공 / 전체 요청 |
| 정규화 커버리지 | >90% | 매핑 성공 / 전체 값 |
| 정책 위반률 | <1% | 위반 / 전체 토큰 |
| VTO 품질 점수 | >0.85 | 사용자 평가 평균 |

### 7.3 장애 대응

**문제:** 추출 실패
- **원인:** 이미지 품질 낮음, 텍스트 부족
- **대응:** Manual review queue로 라우팅

**문제:** 정규화 실패
- **원인:** 신규 동의어
- **대응:** 사전 자동 업데이트 + 알림

**문제:** 정책 위반
- **원인:** 금칙어 포함
- **대응:** 자동 차단 + 벤더 알림

---

**문서 버전:** 1.0
**최종 수정일:** 2026-02-24
**작성자:** PiMS & Ontology Team
