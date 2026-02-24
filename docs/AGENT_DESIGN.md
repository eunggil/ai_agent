# AI Agent 상세 설계

## 목차

1. [에이전트 개발 트렌드](#1-에이전트-개발-트렌드)
2. [광고결합 콘텐츠 생성 에이전트](#2-광고결합-콘텐츠-생성-에이전트)
3. [에이전트 그래프 설계](#3-에이전트-그래프-설계)
4. [하이브리드 검색 전략](#4-하이브리드-검색-전략)
5. [광고 랭킹 시스템](#5-광고-랭킹-시스템)
6. [브랜드 안전 장치](#6-브랜드-안전-장치)
7. [Vertex AI 활용](#7-vertex-ai-활용)
8. [구현 로드맵](#8-구현-로드맵)

---

## 1. 에이전트 개발 트렌드

### 1.1 핵심 트렌드 4가지

#### 트렌드 1: 에이전트는 상태머신/그래프 런타임이다

**기존 방식:**
```
사용자 입력 → LLM 호출 → 결과 반환
```

**현재 트렌드:**
```
사용자 입력 → 상태머신 그래프 실행 → 다중 노드 처리 → 결과 반환
```

**핵심 특징:**
- 재시도(Retry)
- 분기(Branching)
- 승인(Approval)
- 중단(Interruption)

**도구:** LangGraph, Vertex AI Agent Engine

> LangGraph는 "에이전트를 그래프로 만드는" 프레임워크로, 각 노드가 독립적인 작업을 수행하고 엣지가 조건부 분기를 처리합니다.

#### 트렌드 2: Agent Ops가 프레임워크만큼 중요

**필수 관측 요소:**
- 프롬프트 버전 관리
- 실험/A-B 테스트
- 트레이스(Trace)
- 비용 추적
- 지연 모니터링
- 오류 분류
- 툴 호출 로그

**Vertex AI의 Agent Ops:**
- 프롬프트 관리 (Vertex AI Prompt Management)
- Agent 라이프사이클 관리
- 세션/메모리 관리

#### 트렌드 3: Tool Governance / 안전장치

**필요성:**
- 조직이 허용한 도구만 사용
- 인젝션 방어
- 데이터 유출 방지
- 권한 관리

**Vertex AI의 Tool Governance:**
- Cloud API Registry로 툴 레지스트리 관리
- 조직 레벨 정책 적용
- 안전한 API 호출

#### 트렌드 4: Hybrid Retrieval (벡터 + 그래프)

**왜 하이브리드인가?**

| 방식 | 강점 | 약점 |
|------|------|------|
| 벡터만 | 의미 유사도 검색 | 제약/정책 무시 가능 |
| 그래프만 | 제약/정책 강제 | 유연성 부족 |
| **하이브리드** | **유사도 + 제약 동시 만족** | **구현 복잡도** |

**광고/커머스에서 특히 유리:**
- 유사도 = 벡터 (어울리는 상품 찾기)
- 정합/제약/권리/정책 = 그래프 (붙일 수 있는지 검증)

---

## 2. 광고결합 콘텐츠 생성 에이전트

### 2.1 목표 플로우 정의

**입력:**
- 사용자가 올릴 콘텐츠 원본 (텍스트/이미지/영상/스크립트)
- 사용자 프롬프트 (선택)
- UMM/마인드셋 상태 (UT)
- 최근 Activity Token 시퀀스 (AT)
- PiMS 상품/브랜드/캠페인 데이터 (PT/BT/CT)
- 재고/가격/소재/권리/로고 가이드

**출력:**
- 광고가 자연스럽게 결합된 콘텐츠
- 결합 근거 (설명가능성)
- 정책 준수 증명

### 2.2 에이전트 파이프라인 (9단계)

```
┌────────────────────────────────────────────────────────────┐
│  1. Ingest & Canonicalize                                  │
│     업로드 콘텐츠 파싱 + 메타 생성                          │
└────────────┬───────────────────────────────────────────────┘
             │
┌────────────▼───────────────────────────────────────────────┐
│  2. Safety/Policy Pre-check                                │
│     금칙/민감 주제/권리/개인정보 위험 1차 차단              │
└────────────┬───────────────────────────────────────────────┘
             │
┌────────────▼───────────────────────────────────────────────┐
│  3. Hybrid Retrieve                                         │
│     Vector: 유사 상품/소재 후보 넓게                        │
│     Graph: 브랜드/캠페인 제약으로 좁히기                    │
└────────────┬───────────────────────────────────────────────┘
             │
┌────────────▼───────────────────────────────────────────────┐
│  4. Ad Candidate Ranking                                    │
│     스코어링/경매로 상위 N개 선정                           │
└────────────┬───────────────────────────────────────────────┘
             │
┌────────────▼───────────────────────────────────────────────┐
│  5. ACT Plan (블루프린트 생성)                              │
│     결합 방식 계획 (로고/노출/카피/CTA)                     │
└────────────┬───────────────────────────────────────────────┘
             │
┌────────────▼───────────────────────────────────────────────┐
│  6. Generate (콘텐츠 생성/변환)                             │
│     텍스트/썸네일/영상 편집                                 │
└────────────┬───────────────────────────────────────────────┘
             │
┌────────────▼───────────────────────────────────────────────┐
│  7. Post-check (품질/정책 검사)                             │
│     로고 훼손, 금칙 문구, 브랜드 톤 검증                    │
└────────────┬───────────────────────────────────────────────┘
             │
┌────────────▼───────────────────────────────────────────────┐
│  8. Publish & Logging                                       │
│     O-token/I-token + 근거 + 비용 저장                      │
└────────────┬───────────────────────────────────────────────┘
             │
┌────────────▼───────────────────────────────────────────────┐
│  9. Feedback Loop                                           │
│     시청/클릭/전환 → UT/성과 반영                           │
└────────────────────────────────────────────────────────────┘
```

---

## 3. 에이전트 그래프 설계

### 3.1 LangGraph 기반 노드 구성

#### State 스키마

```python
from typing import TypedDict, List, Optional
from dataclasses import dataclass

class CampaignState(TypedDict):
    """캠페인 생성 에이전트 상태"""

    # 입력
    input: dict  # brand_id, product_ids, objective, budget, schedule

    # GPR 초안
    draft: dict  # billing_model, optimization_on, frequency_cap, exclusion_rules

    # 타겟 설정
    gpr_targets: List[dict]  # name, signals, intent_strength, est_kpi_range

    # 자동 결합 설정
    auto_combine: dict  # enabled, combine_mode, content_types, fit_slider

    # 정책 검증
    policy: dict  # status(pass/warn/risk), issues, fix_suggestions

    # 예측
    forecast: dict  # est_matches_per_day, est_vtr/ctr, est_cpv/cpc, warnings

    # UI 패킹
    ui_pack: dict  # top_badges, summary_cards, editable_fields

    # Human-in-the-loop
    human: dict  # needs_review, review_reason, review_payload
```

#### 노드 정의

**Node 1: ContextLoad**
```python
async def context_load(state: CampaignState) -> CampaignState:
    """PiMS에서 브랜드 가이드/금칙어/카테고리/상품 메타 로드"""

    brand_id = state["input"]["brand_id"]

    # PiMS 데이터 로드
    brand_data = await pims_client.get_brand(brand_id)
    products = await pims_client.get_products(state["input"]["product_ids"])

    # 컨텍스트 구성
    context = {
        "brand_guidelines": brand_data.guidelines,
        "forbidden_phrases": brand_data.forbidden_phrases,
        "logo_spec": brand_data.logo_spec,
        "products": products
    }

    state["context"] = context
    return state
```

**Node 2: DefaultDraft (GPR)**
```python
async def default_draft(state: CampaignState) -> CampaignState:
    """목표/상품/브랜드 기반 디폴트 초안 생성"""

    objective = state["input"]["objective"]
    category = state["context"]["products"][0].category

    # 과금 모델 결정
    if objective == "awareness":
        billing_model = "CPV"  # Cost Per View
    elif objective == "conversion":
        billing_model = "CPA"  # Cost Per Action
    else:
        billing_model = "CPC"  # Cost Per Click

    # 빈도 캡 설정
    frequency_cap = {
        "max_per_day": 3,
        "max_per_week": 10
    }

    # 기본 제외 룰
    exclusion_rules = {
        "competitor_content": True,
        "sensitive_context": True
    }

    state["draft"] = {
        "billing_model": billing_model,
        "optimization_on": True,
        "frequency_cap": frequency_cap,
        "exclusion_rules": exclusion_rules
    }

    return state
```

**Node 3: Targeting (GPR)**
```python
async def targeting_gpr(state: CampaignState) -> CampaignState:
    """추천 타겟 세트 2~3개 자동 생성"""

    products = state["context"]["products"]

    # 상품 특성 기반 타겟 생성
    targets = []

    # Target Set 1: 관심사 기반
    targets.append({
        "name": "관심사 매칭",
        "signals": ["interest:" + p.category for p in products],
        "intent_strength": "high",
        "est_kpi_range": {"ctr": [0.02, 0.05], "cvr": [0.01, 0.03]},
        "enabled": True
    })

    # Target Set 2: 행동 기반
    targets.append({
        "name": "유사 행동 패턴",
        "signals": ["behavior:similar_purchases"],
        "intent_strength": "medium",
        "est_kpi_range": {"ctr": [0.015, 0.04], "cvr": [0.008, 0.025]},
        "enabled": True
    })

    # Target Set 3: 룩어라이크
    targets.append({
        "name": "전환 고객 유사",
        "signals": ["lookalike:converters"],
        "intent_strength": "high",
        "est_kpi_range": {"ctr": [0.025, 0.06], "cvr": [0.012, 0.035]},
        "enabled": False  # 옵션
    })

    state["gpr_targets"] = targets
    return state
```

**Node 4: AutoCombineRules**
```python
async def auto_combine_rules(state: CampaignState) -> CampaignState:
    """콘텐츠결합형 광고의 자동 결합 규칙 설정"""

    # 기본값: 자동 결합 ON
    state["auto_combine"] = {
        "enabled": True,
        "combine_mode": "natural",  # natural | explicit
        "content_types": ["video", "image"],
        "fit_slider": "standard"  # conservative | standard | expanded
    }

    return state
```

**Node 5: Safety/Policy**
```python
async def safety_policy_check(state: CampaignState) -> CampaignState:
    """브랜드 금칙어/민감 맥락/경쟁/과장표현 룰 체크"""

    issues = []

    # 금칙어 체크
    forbidden = state["context"]["brand_guidelines"]["forbidden_phrases"]
    for product in state["context"]["products"]:
        for phrase in forbidden:
            if phrase in product.description:
                issues.append({
                    "type": "forbidden_phrase",
                    "severity": "high",
                    "details": f"Product contains forbidden phrase: {phrase}"
                })

    # 민감 카테고리 체크
    sensitive_categories = ["alcohol", "gambling", "medical"]
    for product in state["context"]["products"]:
        if product.category in sensitive_categories:
            issues.append({
                "type": "sensitive_category",
                "severity": "medium",
                "details": f"Product in sensitive category: {product.category}"
            })

    # 상태 결정
    if any(issue["severity"] == "high" for issue in issues):
        status = "risk"
        state["human"]["needs_review"] = True
        state["human"]["review_reason"] = "High severity policy issues"
    elif issues:
        status = "warn"
    else:
        status = "pass"

    state["policy"] = {
        "status": status,
        "issues": issues,
        "fix_suggestions": generate_fix_suggestions(issues)
    }

    return state
```

**Node 6: Cost/Forecast**
```python
async def cost_forecast(state: CampaignState) -> CampaignState:
    """예산 대비 예상 결합량 / 예상 KPI 범위 계산"""

    daily_budget = state["input"]["daily_budget"]
    billing_model = state["draft"]["billing_model"]

    # 예상 CPV/CPC 계산
    if billing_model == "CPV":
        est_cost_per_action = 0.10  # $0.10 per view
    elif billing_model == "CPC":
        est_cost_per_action = 0.50  # $0.50 per click
    else:
        est_cost_per_action = 2.00  # $2.00 per conversion

    # 예상 매칭 수
    est_matches_per_day = int(daily_budget / est_cost_per_action)

    # 경고 체크
    warnings = []
    if est_matches_per_day < 100:
        warnings.append({
            "type": "low_volume",
            "message": "결합량이 부족할 수 있습니다. fit_slider를 완화하거나 예산을 증액하세요."
        })

    state["forecast"] = {
        "est_matches_per_day": est_matches_per_day,
        "est_cpv": est_cost_per_action if billing_model == "CPV" else None,
        "est_cpc": est_cost_per_action if billing_model == "CPC" else None,
        "warnings": warnings
    }

    # 결합량 부족 시 Human Review
    if est_matches_per_day < 100:
        state["human"]["needs_review"] = True
        state["human"]["review_reason"] = "Low estimated volume"

    return state
```

**Node 7: UI-Pack**
```python
async def ui_pack(state: CampaignState) -> CampaignState:
    """앱 화면에 뿌릴 요약 카드 생성"""

    # 상위 배지
    badges = [
        "콘텐츠결합형",
        state["auto_combine"]["combine_mode"],
        f"적합도: {state['auto_combine']['fit_slider']}"
    ]

    # 요약 카드
    summary_cards = [
        {
            "title": "타겟 설정",
            "content": f"{len(state['gpr_targets'])}개 타겟 세트",
            "details": [t["name"] for t in state["gpr_targets"] if t["enabled"]]
        },
        {
            "title": "예상 성과",
            "content": f"일일 {state['forecast']['est_matches_per_day']}건 예상",
            "details": state["forecast"].get("warnings", [])
        },
        {
            "title": "정책 상태",
            "content": state["policy"]["status"],
            "details": [i["type"] for i in state["policy"]["issues"]]
        }
    ]

    # 수정 가능한 필드만 노출
    editable_fields = [
        "daily_budget",
        "schedule",
        "fit_slider",
        "frequency_cap"
    ]

    state["ui_pack"] = {
        "top_badges": badges,
        "summary_cards": summary_cards,
        "editable_fields": editable_fields
    }

    return state
```

**Node 8: HumanReview (interrupt)**
```python
async def human_review(state: CampaignState) -> CampaignState:
    """정책 위험/결합량 부족 시 사람 승인 대기"""

    # 이 노드는 interrupt() 호출
    # 사용자가 수정/승인 후 resume

    return state
```

### 3.2 그래프 구성 (LangGraph)

```python
from langgraph.graph import StateGraph, END

# 그래프 생성
workflow = StateGraph(CampaignState)

# 노드 추가
workflow.add_node("context_load", context_load)
workflow.add_node("default_draft", default_draft)
workflow.add_node("targeting_gpr", targeting_gpr)
workflow.add_node("auto_combine_rules", auto_combine_rules)
workflow.add_node("safety_policy", safety_policy_check)
workflow.add_node("cost_forecast", cost_forecast)
workflow.add_node("ui_pack", ui_pack)
workflow.add_node("human_review", human_review)

# 엣지 정의
workflow.set_entry_point("context_load")
workflow.add_edge("context_load", "default_draft")
workflow.add_edge("default_draft", "targeting_gpr")
workflow.add_edge("targeting_gpr", "auto_combine_rules")
workflow.add_edge("auto_combine_rules", "safety_policy")

# 조건부 라우팅
def should_review(state: CampaignState) -> str:
    if state.get("human", {}).get("needs_review"):
        return "human_review"
    return "cost_forecast"

workflow.add_conditional_edges(
    "safety_policy",
    should_review,
    {
        "human_review": "human_review",
        "cost_forecast": "cost_forecast"
    }
)

workflow.add_edge("human_review", "cost_forecast")
workflow.add_edge("cost_forecast", "ui_pack")
workflow.add_edge("ui_pack", END)

# 컴파일
app = workflow.compile(
    checkpointer=checkpointer  # SQLite/Redis/Postgres
)
```

### 3.3 실행 예시

```python
# 입력
initial_state = {
    "input": {
        "brand_id": "BR123",
        "product_ids": ["P456", "P789"],
        "objective": "conversion",
        "daily_budget": 1000,
        "schedule": {
            "start": "2026-03-01",
            "end": "2026-03-31"
        }
    }
}

# 실행
config = {"configurable": {"thread_id": "campaign_001"}}
result = await app.ainvoke(initial_state, config)

# Human-in-the-loop가 필요한 경우
if result["human"]["needs_review"]:
    print(f"승인 필요: {result['human']['review_reason']}")

    # 사용자 수정 후 재개
    # ... 사용자 입력 받기 ...

    # 재개
    result = await app.ainvoke(
        {"human": {"needs_review": False, "approved": True}},
        config
    )
```

---

## 4. 하이브리드 검색 전략

### 4.1 Vector + Graph 결합

```python
async def hybrid_retrieve(
    content_token: ContentToken,
    user_token: UserToken,
    k: int = 20
) -> List[AdCandidate]:
    """
    1단계: 벡터 검색으로 후보 넓게
    2단계: 그래프 제약으로 좁히기
    """

    # 1. 벡터 검색 (의미 유사도)
    query_embedding = content_token.embedding

    vector_candidates = await vector_db.search(
        vector=query_embedding,
        k=k * 2,  # 여유있게 2배
        filters={
            "status": "active",
            "budget_remaining": {"$gt": 0}
        }
    )

    # 2. 그래프 제약 필터링
    eligible_candidates = []

    for candidate in vector_candidates:
        # Cypher 쿼리로 제약 체크
        is_eligible = await graph_db.check_eligibility(
            product_id=candidate.product_id,
            user_context={
                "age": user_token.age,
                "country": user_token.country
            },
            content_flags=content_token.sensitive_flags
        )

        if is_eligible:
            # 근거 체인 가져오기
            rationale = await graph_db.get_rationale(
                product_id=candidate.product_id,
                campaign_id=candidate.campaign_id
            )

            candidate.rationale = rationale
            eligible_candidates.append(candidate)

        if len(eligible_candidates) >= k:
            break

    return eligible_candidates
```

### 4.2 그래프 제약 체크 (Cypher)

```cypher
-- 캠페인 적격성 체크
MATCH (c:Campaign {campaign_id: $campaign_id})-[:PROMOTES]->(p:Product {product_id: $product_id})-[:BELONGS_TO]->(b:Brand)
WHERE c.status = 'ACTIVE'
  AND c.start_at <= datetime()
  AND c.end_at >= datetime()
  AND p.status = 'ACTIVE'
  AND b.status = 'ACTIVE'

-- 타겟팅 룰 체크
OPTIONAL MATCH (p)-[:HAS_POLICY_RULE]->(pr:PolicyRule)
WHERE pr.rule_type = 'TARGET_RESTRICTION'
  AND (
    pr.payload.age_min IS NULL OR pr.payload.age_min <= $user_age
  )
  AND (
    pr.payload.age_max IS NULL OR pr.payload.age_max >= $user_age
  )
  AND (
    pr.payload.countries IS NULL OR $user_country IN pr.payload.countries
  )

-- 권리 체크
OPTIONAL MATCH (c)-[:USES_ASSET]->(a:Asset)-[:LICENSED_BY]->(r:RightsPolicy)
WHERE a.status = 'ACTIVE'
  AND (r.expires_at IS NULL OR r.expires_at > datetime())
  AND r.scope IN ['IN_APP', 'AD', 'ALL']

RETURN count(*) > 0 AS is_eligible;
```

---

## 5. 광고 랭킹 시스템

### 5.1 4단계 프로세스

```python
async def rank_ad_candidates(
    candidates: List[AdCandidate],
    user_token: UserToken,
    content_token: ContentToken
) -> List[AdCandidate]:
    """광고 후보 랭킹 (4단계)"""

    # 1. Candidate Generation (이미 완료)
    # candidates = hybrid_retrieve()

    # 2. Scoring
    scored = []
    for candidate in candidates:
        score = compute_ad_score(candidate, user_token, content_token)
        scored.append((candidate, score))

    # 3. Allocation (다양성/빈도)
    allocated = apply_allocation_rules(scored, user_token)

    # 4. Final Ranking
    ranked = sorted(allocated, key=lambda x: x[1], reverse=True)

    return [candidate for candidate, _ in ranked]
```

### 5.2 스코어링 함수

```python
def compute_ad_score(
    candidate: AdCandidate,
    user_token: UserToken,
    content_token: ContentToken
) -> float:
    """
    스코어 = Bid × pCTR × Relevance × Quality × (1 - Fatigue)
    """

    # Bid (입찰가)
    bid_score = candidate.bid_amount / 10.0  # 정규화

    # pCTR (예측 클릭률)
    pctr = predict_ctr(candidate, user_token)

    # Relevance (의미 적합도)
    relevance = cosine_similarity(
        candidate.embedding,
        content_token.embedding
    )

    # Quality (품질 점수)
    quality = candidate.quality_score

    # Fatigue (피로도 패널티)
    fatigue = compute_fatigue(
        candidate.ad_id,
        user_token.recent_impressions
    )

    # 최종 스코어
    score = (
        0.3 * bid_score +
        0.3 * pctr +
        0.2 * relevance +
        0.1 * quality +
        0.1 * (1 - fatigue)
    )

    return score
```

### 5.3 할당 규칙 (다양성/빈도)

```python
def apply_allocation_rules(
    scored: List[Tuple[AdCandidate, float]],
    user_token: UserToken
) -> List[Tuple[AdCandidate, float]]:
    """다양성 및 빈도 캡 적용"""

    result = []
    brand_count = {}

    for candidate, score in scored:
        brand_id = candidate.brand_id

        # 동일 브랜드 과다 노출 방지
        if brand_count.get(brand_id, 0) >= 2:
            continue

        # 사용자 피로도 체크
        if user_token.ad_fatigue.get(candidate.ad_id, 0) > 3:
            score *= 0.5  # 패널티

        result.append((candidate, score))
        brand_count[brand_id] = brand_count.get(brand_id, 0) + 1

    return result
```

---

## 6. 브랜드 안전 장치

### 6.1 3중 방어 체계

```python
class BrandSafetyGuard:
    """브랜드 안전 3중 방어"""

    async def enforce_safety(
        self,
        generated_content: GeneratedContent,
        brand_spec: BrandSpec
    ) -> SafetyResult:
        """
        1. Template Lock (하드 제약)
        2. Vision Post-check (소프트 검증)
        3. Repair Loop (자동 수정)
        """

        # 1. Template Lock
        locked = self.apply_template_lock(
            generated_content,
            brand_spec.logo_spec
        )

        # 2. Vision Post-check
        check_result = await self.vision_post_check(
            locked,
            brand_spec
        )

        # 3. Repair Loop (위반 시)
        if not check_result.passed:
            repaired = await self.repair_loop(
                locked,
                check_result.violations,
                brand_spec
            )
            return repaired

        return SafetyResult(
            passed=True,
            content=locked
        )

    def apply_template_lock(
        self,
        content: GeneratedContent,
        logo_spec: LogoSpec
    ) -> GeneratedContent:
        """로고 레이어 고정 (생성 모델이 건드리지 못하게)"""

        # 로고를 별도 레이어로 합성
        logo_layer = create_logo_layer(
            logo_spec.image_url,
            position=logo_spec.position,
            min_size=logo_spec.min_size,
            clear_space=logo_spec.clear_space
        )

        # 생성된 콘텐츠 위에 오버레이
        content.add_layer(logo_layer, locked=True)

        return content

    async def vision_post_check(
        self,
        content: GeneratedContent,
        brand_spec: BrandSpec
    ) -> CheckResult:
        """생성 결과에서 로고 영역 감지 및 훼손 체크"""

        violations = []

        # 로고 감지
        logo_detection = await vision_model.detect_logo(
            content.image,
            expected_logo=brand_spec.logo_spec
        )

        # 크기 체크
        if logo_detection.size < brand_spec.logo_spec.min_size:
            violations.append("Logo too small")

        # 여백 체크
        if logo_detection.clear_space < brand_spec.logo_spec.clear_space:
            violations.append("Insufficient clear space")

        # 왜곡 체크
        if logo_detection.distortion > 0.1:
            violations.append("Logo distorted")

        return CheckResult(
            passed=(len(violations) == 0),
            violations=violations
        )

    async def repair_loop(
        self,
        content: GeneratedContent,
        violations: List[str],
        brand_spec: BrandSpec,
        max_retries: int = 3
    ) -> SafetyResult:
        """위반 시 자동 수정"""

        for i in range(max_retries):
            # 위반 유형별 수정
            if "Logo too small" in violations:
                content = self.resize_logo(content, brand_spec.logo_spec)

            if "Insufficient clear space" in violations:
                content = self.adjust_clear_space(content, brand_spec.logo_spec)

            if "Logo distorted" in violations:
                content = self.restore_logo(content, brand_spec.logo_spec)

            # 재검증
            check_result = await self.vision_post_check(content, brand_spec)

            if check_result.passed:
                return SafetyResult(
                    passed=True,
                    content=content,
                    repair_attempts=i + 1
                )

        # 수정 실패
        return SafetyResult(
            passed=False,
            content=content,
            repair_attempts=max_retries,
            error="Failed to repair after max retries"
        )
```

### 6.2 금칙어 및 정책 체크

```python
class PolicyChecker:
    """정책 및 금칙어 체크"""

    async def check_policy(
        self,
        content: GeneratedContent,
        brand_policy: BrandPolicy
    ) -> PolicyResult:
        """브랜드 정책 준수 확인"""

        violations = []

        # 금칙어 체크
        for phrase in brand_policy.forbidden_phrases:
            if phrase in content.text:
                violations.append({
                    "type": "forbidden_phrase",
                    "phrase": phrase,
                    "severity": "high"
                })

        # 필수 고지문 체크
        for disclaimer in brand_policy.required_disclaimers:
            if disclaimer not in content.text:
                violations.append({
                    "type": "missing_disclaimer",
                    "disclaimer": disclaimer,
                    "severity": "medium"
                })

        # 과장 표현 체크 (LLM 기반)
        exaggeration = await self.detect_exaggeration(
            content.text,
            brand_policy.claim_policy
        )

        if exaggeration:
            violations.extend(exaggeration)

        return PolicyResult(
            passed=(len(violations) == 0),
            violations=violations
        )

    async def detect_exaggeration(
        self,
        text: str,
        claim_policy: ClaimPolicy
    ) -> List[dict]:
        """LLM으로 과장 표현 탐지"""

        prompt = f"""
다음 텍스트에서 과장 표현이나 금지된 효능 표현이 있는지 확인하세요.

허용된 표현: {claim_policy.allowed_claims}
금지된 표현: {claim_policy.forbidden_claims}

텍스트:
{text}

과장/금지 표현이 있으면 JSON 형식으로 반환:
[{{"phrase": "...", "reason": "...", "severity": "high|medium|low"}}]

없으면 빈 배열 [] 반환.
"""

        response = await llm.generate(prompt)
        violations = json.loads(response)

        return violations
```

---

## 7. Vertex AI 활용

### 7.1 권장 스택

| 컴포넌트 | Vertex AI 서비스 | 용도 |
|----------|------------------|------|
| 에이전트 런타임 | Vertex AI Agent Engine | 상태 관리, 세션, 메모리 |
| 프롬프트 관리 | Vertex AI Prompt Management | 버전 관리, A/B 테스트 |
| 벡터 검색 | Vertex AI Vector Search | 상품/콘텐츠 유사도 검색 |
| Tool Governance | Cloud API Registry | API 접근 제어 |
| 안전 장치 | Model Armor | 인젝션 방어, 민감정보 필터 |

### 7.2 구현 예시

```python
from google.cloud import aiplatform

# Vertex AI Agent Engine 초기화
aiplatform.init(
    project="addeep-ai-agent",
    location="us-central1"
)

# Agent 생성
agent = aiplatform.Agent(
    display_name="ad-combination-agent",
    agent_type="CONVERSATIONAL",
    tools=[
        {"function_declarations": [pims_tool, ams_tool]},
        {"retrieval": {"vector_store": vector_store_id}}
    ],
    generation_config={
        "temperature": 0.7,
        "top_k": 40,
        "top_p": 0.95
    }
)

# 세션 생성
session = agent.create_session(
    session_id="user_123_session",
    context={
        "user_id": "user_123",
        "mindset_token": ut_data
    }
)

# 메시지 전송
response = session.send_message(
    content="사용자가 업로드한 영상에 립스틱 광고 결합",
    files=["gs://bucket/user_video.mp4"]
)

# Model Armor 적용
from google.cloud import model_armor

armored_response = model_armor.shield(
    response=response,
    policies=[
        "no_injection",
        "no_pii",
        "brand_safety"
    ]
)
```

---

## 8. 구현 로드맵

### Phase 1: 설계 고정 (2주)

**산출물:**
- [x] 에이전트 그래프 노드/상태/입출력 스키마
- [x] 온톨로지 v0 (카테고리/속성/제약)
- [x] 랭킹 v0 (Candidate/Score/Allocation)

**담당:**
- PM: 온톨로지/정책 정의
- Backend: 스키마 구현
- AI: 프롬프트 템플릿

### Phase 2: MVP 구현 (4~6주)

**기능:**
- [ ] Hybrid Retrieve (Vector + Graph)
- [ ] Template Lock + Post-check
- [ ] Trace/Versioning 저장

**기술 스택:**
- LangGraph for 상태머신
- Vertex Vector Search for 벡터 검색
- Neo4j/Neptune for 그래프 제약
- PostgreSQL for 트레이스 저장

### Phase 3: 운영 고도화 (8~12주)

**기능:**
- [ ] Model Armor 통합
- [ ] Tool Governance (API Registry)
- [ ] 실패 분류 → 자동 재시도
- [ ] A/B 테스트 프레임워크

**모니터링:**
- Agent Ops 대시보드
- 비용/지연/오류율 추적
- 정책 위반 알림

### Phase 4: 확장 (3~6개월)

**기능:**
- [ ] 멀티모달 생성 (텍스트+이미지+영상)
- [ ] 실시간 성과 피드백
- [ ] 글로벌 확장 (다국어/다지역)

---

## 9. 운영 지표

### 9.1 성공 지표

| 지표 | 목표 | 측정 방법 |
|------|------|----------|
| 결합 성공률 | >95% | 생성 완료 / 요청 |
| 정책 준수율 | 100% | 정책 위반 0건 |
| 로고 훼손률 | <0.1% | Vision 체크 실패 |
| 평균 생성 시간 | <10s | P95 레이턴시 |
| 사용자 만족도 | >4.0/5.0 | 피드백 평점 |

### 9.2 비용 지표

| 항목 | 예상 비용 | 최적화 목표 |
|------|----------|------------|
| LLM 호출 | $0.05/request | <$0.03 |
| 이미지 생성 | $0.10/image | <$0.08 |
| 벡터 검색 | $0.001/query | <$0.0008 |
| 그래프 쿼리 | $0.002/query | <$0.0015 |

### 9.3 품질 지표

| 지표 | 목표 | 액션 |
|------|------|------|
| 광고 적합도 | >0.8 | 낮으면 타겟팅 재조정 |
| 브랜드 톤 일치 | >0.85 | 낮으면 프롬프트 수정 |
| 사용자 피로도 | <0.3 | 높으면 빈도 캡 강화 |

---

## 부록: 용어 정리

| 용어 | 설명 |
|------|------|
| **UMM** | User Mental Model - 사용자 마인드셋/선호 그래프 |
| **PiMS** | Product Information Management System |
| **AT** | Activity Token - 행동 토큰 |
| **UT** | User Token - 사용자 토큰 |
| **PT** | Product Token - 상품 토큰 |
| **BT** | Brand Token - 브랜드 토큰 |
| **CT** | Content Token - 콘텐츠 토큰 |
| **ACT** | Ad Creative Token - 광고 크리에이티브 토큰 |
| **GPR** | Google Performance Ranking |
| **VTO** | Virtual Try-On |

---

**문서 버전:** 1.0
**최종 수정일:** 2026-02-24
**작성자:** AI Agent Team
