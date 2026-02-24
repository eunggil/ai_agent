"""
LangGraph 에이전트 상태 스키마
"""
from typing import TypedDict, Optional, List


class FeedAgentState(TypedDict):
    """피드 생성 에이전트 상태

    Pipeline (6단계):
        load_context → state_interpreter → retrieve_candidates
                     → strategy_planner → creative_generator
                     → media_generator
    """
    # ── 입력 ──────────────────────────────
    user_id: str
    prompt: str

    # ── load_context ──────────────────────
    user_context: dict           # 사용자 프로필 + 관심사 + 최근 활동

    # ── state_interpreter ─────────────────
    state_analysis: str          # 사용자 의도/감정/니즈 분석 (JSON string)

    # ── retrieve_candidates ───────────────
    ad_candidates: List[dict]    # 광고 후보 목록

    # ── strategy_planner ──────────────────
    strategy: str                # 결합 전략 (JSON string)

    # ── creative_generator ────────────────
    generated_content: str       # SNS 텍스트 게시물
    image_prompt: str            # 이미지/영상 생성용 프롬프트 (영어)
    negative_prompt: str         # 네거티브 프롬프트

    # ── media_generator ───────────────────
    media_type: str              # "image" | "video" | "text"
    media_data: str              # base64 인코딩 데이터
    media_metadata: dict         # 생성 메타데이터 (모델명, 생성시간 등)

    # ── 공통 메타 ─────────────────────────
    provider_name: str           # LLM 프로바이더 이름
    media_provider_name: str     # 미디어 프로바이더 이름
    error: Optional[str]
