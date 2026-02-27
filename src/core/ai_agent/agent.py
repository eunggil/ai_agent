"""
LangGraph 기반 피드 생성 에이전트

Pipeline (6단계):
    1. load_context        → 사용자 컨텍스트 로드 (DB)
    2. state_interpreter   → 사용자 의도/감정 분석 (LLM)
    3. retrieve_candidates → 광고/상품/콘텐츠 후보 검색 (pgvector)
    4. strategy_planner    → 결합 전략 수립 (LLM)
    5. creative_generator  → 텍스트 콘텐츠 + 이미지 프롬프트 생성 (LLM)
    6. media_generator     → 이미지/영상 생성 (Imagen / LCM-LoRA / Replicate)

환경변수:
    AI_PROVIDER=vertex | local
    MEDIA_PROVIDER=vertex_imagen | local_diffusers | replicate | none
    IMAGE_MODEL=lcm-lora-sdxl | lcm-lora-sd15 | sdxl | sd15 | flux-schnell
    VIDEO_MODEL=animatediff-lcm | animate-diff | svd
    MEDIA_TYPE=image | video | text
"""
import json
import logging
import os
import re
from typing import Any, Optional

from langgraph.graph import StateGraph, END

from .providers import get_provider, ModelProvider
from .media_providers import get_media_provider, MediaProvider
from .state import FeedAgentState
from .db_data import get_user, retrieve_ad_candidates, retrieve_products, retrieve_reference_contents

logger = logging.getLogger(__name__)

MEDIA_TYPE = os.getenv("MEDIA_TYPE", "image")  # image | video | text


# ══════════════════════════════════════════════
# 노드 1: 사용자 컨텍스트 로드
# ══════════════════════════════════════════════

def _load_context_node(state: FeedAgentState) -> FeedAgentState:
    user_id = state["user_id"]
    user_data = get_user(user_id)

    # long_term_vector를 user_context에서 분리해 state에 별도 저장
    # (retrieve_candidates에서 임베딩 재생성 없이 재사용)
    user_vector = user_data.pop("long_term_vector", None)

    logger.info(
        f"[1/6 load_context] user={user_id}, "
        f"interests={user_data.get('interests')}, "
        f"vector={'있음' if user_vector else '없음'}"
    )
    state["user_context"] = user_data
    state["user_vector"] = user_vector
    return state


# ══════════════════════════════════════════════
# 노드 2: 사용자 상태 해석 (LLM)
# ══════════════════════════════════════════════

def _make_state_interpreter_node(provider: ModelProvider):
    def node(state: FeedAgentState) -> FeedAgentState:
        user = state["user_context"]
        prompt = state["prompt"]

        system = "당신은 SNS 사용자의 상태를 분석하는 전문가입니다. 간결하고 정확하게 JSON으로만 응답하세요."

        llm_prompt = f"""사용자 정보:
- 관심사: {', '.join(user.get('interests', []))}
- 최근 활동: {', '.join(user.get('recent_activities', []))}
- 성향 요약: {user.get('vector_summary', '')}

사용자 요청: "{prompt}"

다음 JSON 형식으로만 응답하세요:
{{
  "intent": "사용자의 핵심 의도 (한 문장)",
  "mood": "현재 감정 상태 (예: 설레는, 편안한, 호기심 있는)",
  "needs": "현재 필요한 것 (한 문장)",
  "recommendation_direction": "어떤 방향의 콘텐츠가 어울리는지 (한 문장)"
}}"""

        logger.info(f"[2/6 state_interpreter] calling {provider.name}")
        try:
            result = _strip_md_json(provider.generate(llm_prompt, system=system))
            json.loads(result)  # 유효성 검증
            state["state_analysis"] = result
        except json.JSONDecodeError:
            state["state_analysis"] = json.dumps({
                "intent": prompt,
                "mood": "중립적",
                "needs": "맞춤형 콘텐츠",
                "recommendation_direction": f"{user.get('interests', ['lifestyle'])[0]} 관련 콘텐츠",
            }, ensure_ascii=False)
        except Exception as e:
            logger.error(f"[state_interpreter] error: {e}")
            state["error"] = f"state_interpreter 실패: {e}"

        return state
    return node


# ══════════════════════════════════════════════
# 노드 3: 광고 후보 검색 (Mock/Vector DB)
# ══════════════════════════════════════════════

def _retrieve_candidates_node(state: FeedAgentState) -> FeedAgentState:
    user = state["user_context"]
    interests = user.get("interests", ["lifestyle"])
    prompt = state["prompt"]
    user_vector = state.get("user_vector")  # load_context에서 받은 long_term_vector

    # user_vector 재사용으로 임베딩 API 호출 최소화
    candidates = retrieve_ad_candidates(interests, prompt, top_k=3, user_vector=user_vector)
    products = retrieve_products(interests, prompt, top_k=3, user_vector=user_vector)
    contents = retrieve_reference_contents(interests, prompt, top_k=2, user_vector=user_vector)

    logger.info(
        f"[3/6 retrieve_candidates] ads={len(candidates)}, "
        f"products={len(products)}, contents={len(contents)}"
    )

    state["ad_candidates"] = candidates
    state["product_candidates"] = products
    state["reference_contents"] = contents
    return state


# ══════════════════════════════════════════════
# 노드 4: 광고 결합 전략 수립 (LLM)
# ══════════════════════════════════════════════

def _make_strategy_planner_node(provider: ModelProvider):
    def node(state: FeedAgentState) -> FeedAgentState:
        candidates_text = "\n".join([
            f"- [{ad['ad_id']}] {ad['brand']} {ad['product']}: {ad['description']} (관련도: {ad['relevance_score']})"
            for ad in state["ad_candidates"]
        ])

        system = "당신은 SNS 광고 전략 전문가입니다. JSON으로만 응답하세요."
        llm_prompt = f"""사용자 상태 분석:
{state['state_analysis']}

광고 후보:
{candidates_text}

가장 적합한 광고를 선택하고 전략을 수립하세요.
다음 JSON 형식으로만 응답하세요:
{{
  "selected_ad_id": "선택한 광고 ID",
  "selected_product": "상품명",
  "selected_brand": "브랜드명",
  "combination_method": "story_blend | inline | subtle 중 선택",
  "rationale": "이 광고를 선택한 이유 (한 문장)",
  "key_message": "핵심 메시지 (한 문장)",
  "visual_direction": "이미지/영상의 시각적 방향 (한 문장, 영어로)"
}}"""

        logger.info(f"[4/6 strategy_planner] calling {provider.name}")
        try:
            result = _strip_md_json(provider.generate(llm_prompt, system=system))
            json.loads(result)
            state["strategy"] = result
        except json.JSONDecodeError:
            first = state["ad_candidates"][0] if state["ad_candidates"] else {}
            state["strategy"] = json.dumps({
                "selected_ad_id": first.get("ad_id", "ad_001"),
                "selected_product": first.get("product", "추천 상품"),
                "selected_brand": first.get("brand", "브랜드"),
                "combination_method": "subtle",
                "rationale": "사용자 관심사와 가장 부합",
                "key_message": "자연스러운 라이프스타일과 함께",
                "visual_direction": "lifestyle photography, natural lighting",
            }, ensure_ascii=False)
        except Exception as e:
            logger.error(f"[strategy_planner] error: {e}")
            state["error"] = f"strategy_planner 실패: {e}"

        return state
    return node


# ══════════════════════════════════════════════
# 노드 5: 크리에이티브 생성 (LLM)
#   - SNS 텍스트 게시물
#   - 이미지/영상 생성용 프롬프트 (영어)
# ══════════════════════════════════════════════

def _make_creative_generator_node(provider: ModelProvider):
    def node(state: FeedAgentState) -> FeedAgentState:
        strategy = _parse_json(state.get("strategy", "{}"))
        candidates = state["ad_candidates"]
        media_type = state.get("media_type", MEDIA_TYPE)

        selected_ad = next(
            (ad for ad in candidates if ad["ad_id"] == strategy.get("selected_ad_id")),
            candidates[0] if candidates else {},
        )

        # 관련 상품 컨텍스트 (최대 2개)
        product_context = ""
        product_candidates = state.get("product_candidates", [])
        if product_candidates:
            lines = [
                f"- {p['brand']} {p['name']} ({p['category']}, {p['price']}원): {p['description']}"
                for p in product_candidates[:2]
            ]
            product_context = "\n관련 상품 참고 (이미지 분위기 및 텍스트에 자연스럽게 반영):\n" + "\n".join(lines)

        # 참고 콘텐츠 컨텍스트 (최대 2개)
        content_context = ""
        reference_contents = state.get("reference_contents", [])
        if reference_contents:
            lines = [
                f"- [{c['content_type']}] {c['text'][:80]}"
                for c in reference_contents if c.get("text")
            ]
            if lines:
                content_context = "\n참고 콘텐츠 스타일 (톤앤매너 참고용):\n" + "\n".join(lines)

        system = "당신은 SNS 콘텐츠 크리에이터이자 AI 이미지 프롬프트 전문가입니다. JSON으로만 응답하세요."
        llm_prompt = f"""사용자 상태: {state['state_analysis']}

결합 전략:
- 방식: {strategy.get('combination_method', 'subtle')}
- 핵심 메시지: {strategy.get('key_message', '')}
- 시각 방향: {strategy.get('visual_direction', 'lifestyle photography')}

선택된 광고 상품:
- {selected_ad.get('brand', '')} {selected_ad.get('product', '')}
- 설명: {selected_ad.get('description', '')}
{product_context}{content_context}

생성할 미디어 타입: {media_type}

다음 JSON 형식으로만 응답하세요:
{{
  "text_content": "SNS 텍스트 게시물 (100~200자, 해시태그 2~3개 포함, 광고가 자연스럽게 녹아들도록)",
  "image_prompt": "Stable Diffusion / Imagen 최적화 영어 프롬프트 (상품/브랜드 분위기 묘사, 50~80단어, 사진 스타일 포함)",
  "negative_prompt": "bad quality, blurry, watermark, text overlay, low resolution, deformed"
}}"""

        logger.info(f"[5/6 creative_generator] calling {provider.name}")
        try:
            result = _strip_md_json(provider.generate(llm_prompt, system=system))
            parsed = json.loads(result)

            state["generated_content"] = parsed.get("text_content", "")
            state["image_prompt"] = parsed.get("image_prompt", "")
            state["negative_prompt"] = parsed.get(
                "negative_prompt",
                "bad quality, blurry, watermark, text overlay"
            )
        except json.JSONDecodeError:
            # LLM이 JSON을 못 만든 경우 raw text를 text_content로
            state["generated_content"] = result.strip() if 'result' in locals() else ""
            state["image_prompt"] = (
                f"{selected_ad.get('brand', '')} {selected_ad.get('product', '')}, "
                f"lifestyle photography, natural lighting, Instagram style, "
                f"{strategy.get('visual_direction', '')}"
            )
            state["negative_prompt"] = "bad quality, blurry, watermark"
        except Exception as e:
            logger.error(f"[creative_generator] error: {e}")
            state["error"] = f"creative_generator 실패: {e}"
            state["generated_content"] = ""
            state["image_prompt"] = "lifestyle photography, natural lighting"
            state["negative_prompt"] = "bad quality, blurry"

        logger.info(f"[5/6 creative_generator] text={state['generated_content'][:60]}...")
        logger.info(f"[5/6 creative_generator] image_prompt={state['image_prompt'][:60]}...")
        return state
    return node


# ══════════════════════════════════════════════
# 노드 6: 미디어 생성 (이미지 / 영상)
# ══════════════════════════════════════════════

def _make_media_generator_node(
    media_provider: Optional[MediaProvider],
    video_provider: Optional[MediaProvider],
):
    def node(state: FeedAgentState) -> FeedAgentState:
        media_type = state.get("media_type", MEDIA_TYPE)

        # MEDIA_PROVIDER=none 또는 text 모드 → 스킵
        if media_provider is None or media_type == "text":
            logger.info("[6/6 media_generator] skipped (text-only mode)")
            state["media_data"] = ""
            state["media_metadata"] = {"skipped": True, "reason": "text-only mode"}
            state["media_provider_name"] = "none"
            return state

        image_prompt = state.get("image_prompt") or state.get("generated_content", "")
        negative_prompt = state.get("negative_prompt", "bad quality, blurry")

        try:
            if media_type == "video":
                if video_provider is None:
                    raise RuntimeError(
                        "영상 생성 프로바이더가 없습니다. "
                        "MEDIA_PROVIDER=vertex 또는 MEDIA_PROVIDER=vertex_veo로 설정하고 "
                        "VERTEX_VEO_GCS_BUCKET을 지정하세요."
                    )
                logger.info(f"[6/6 media_generator] type=video, provider={video_provider.name}")
                result = video_provider.generate_video(image_prompt, negative_prompt)
                state["media_provider_name"] = video_provider.name
            else:
                logger.info(f"[6/6 media_generator] type=image, provider={media_provider.name}")
                result = media_provider.generate_image(image_prompt, negative_prompt)
                state["media_provider_name"] = media_provider.name

            state["media_data"] = result.data
            state["media_metadata"] = result.to_dict()
            state["media_metadata"].pop("data", None)  # 메타에서 data 제거 (중복)

        except Exception as e:
            logger.error(f"[media_generator] error: {e}", exc_info=True)
            state["error"] = f"media_generator 실패: {e}"
            state["media_data"] = ""
            state["media_metadata"] = {"error": str(e)}

        return state
    return node


# ══════════════════════════════════════════════
# 에이전트 클래스
# ══════════════════════════════════════════════

class FeedAgent:
    """LangGraph 기반 6단계 피드 생성 에이전트"""

    def __init__(self):
        self.provider = get_provider()
        self.media_provider = get_media_provider()
        self.video_provider = self._resolve_video_provider()
        self.graph = self._build_graph()
        logger.info(
            f"FeedAgent ready | LLM={self.provider.name} | "
            f"Image={self.media_provider.name if self.media_provider else 'none'} | "
            f"Video={self.video_provider.name if self.video_provider else 'none'}"
        )

    def _resolve_video_provider(self) -> Optional[MediaProvider]:
        """영상 지원 프로바이더 결정.

        - media_provider가 영상을 지원하면 그대로 사용
        - vertex_imagen처럼 영상 미지원이면 VERTEX_VEO_GCS_BUCKET이
          설정된 경우에 한해 VertexVeoProvider를 별도 생성
        """
        if self.media_provider and self.media_provider.supports_video:
            return self.media_provider
        if os.getenv("VERTEX_VEO_GCS_BUCKET"):
            try:
                from .media_providers.vertex_veo import VertexVeoProvider
                return VertexVeoProvider()
            except Exception as e:
                logger.warning(f"VertexVeoProvider 초기화 실패: {e}")
        return None

    def _build_graph(self) -> Any:
        workflow = StateGraph(FeedAgentState)

        workflow.add_node("load_context", _load_context_node)
        workflow.add_node("state_interpreter", _make_state_interpreter_node(self.provider))
        workflow.add_node("retrieve_candidates", _retrieve_candidates_node)
        workflow.add_node("strategy_planner", _make_strategy_planner_node(self.provider))
        workflow.add_node("creative_generator", _make_creative_generator_node(self.provider))
        workflow.add_node("media_generator", _make_media_generator_node(self.media_provider, self.video_provider))

        workflow.set_entry_point("load_context")
        workflow.add_edge("load_context", "state_interpreter")
        workflow.add_edge("state_interpreter", "retrieve_candidates")
        workflow.add_edge("retrieve_candidates", "strategy_planner")
        workflow.add_edge("strategy_planner", "creative_generator")
        workflow.add_edge("creative_generator", "media_generator")
        workflow.add_edge("media_generator", END)

        return workflow.compile()

    def run(self, user_id: str, prompt: str, media_type: str = MEDIA_TYPE) -> FeedAgentState:
        """에이전트 실행 (동기)

        FastAPI에서: await asyncio.to_thread(agent.run, user_id, prompt, media_type)
        """
        initial_state: FeedAgentState = {
            "user_id": user_id,
            "prompt": prompt,
            "user_context": {},
            "user_vector": None,
            "state_analysis": "",
            "ad_candidates": [],
            "product_candidates": [],
            "reference_contents": [],
            "strategy": "",
            "generated_content": "",
            "image_prompt": "",
            "negative_prompt": "",
            "media_type": media_type,
            "media_data": "",
            "media_metadata": {},
            "provider_name": self.provider.name,
            "media_provider_name": self.media_provider.name if self.media_provider else "none",
            "error": None,
        }
        config = {"run_name": f"feed_{user_id}"}
        handler = _get_langfuse_handler(user_id)
        if handler:
            config["callbacks"] = [handler]
        return self.graph.invoke(initial_state, config=config)


# 싱글턴
_agent_instance: Optional[FeedAgent] = None


def get_agent() -> FeedAgent:
    global _agent_instance
    if _agent_instance is None:
        _agent_instance = FeedAgent()
    return _agent_instance


# ──────────────────────────────────────────
# 유틸
# ──────────────────────────────────────────

def _get_langfuse_handler(user_id: str = ""):
    """Langfuse 트레이싱 콜백 핸들러 반환. 설정 없으면 None."""
    secret_key = os.getenv("LANGFUSE_SECRET_KEY", "")
    public_key = os.getenv("LANGFUSE_PUBLIC_KEY", "")
    if not secret_key or not public_key:
        return None
    try:
        from langfuse.callback import CallbackHandler
        return CallbackHandler(
            secret_key=secret_key,
            public_key=public_key,
            host=os.getenv("LANGFUSE_HOST", "http://langfuse-web:3000"),
            session_id=user_id or None,
        )
    except Exception as e:
        logger.warning(f"Langfuse 초기화 실패 (트레이싱 비활성화): {e}")
        return None


def _strip_md_json(text: str) -> str:
    """LLM 응답에서 JSON 객체만 추출 (```json ... ``` 래퍼 제거)."""
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        return text[start:end + 1]
    return text.strip()


def _parse_json(s: str, default: dict = None) -> dict:
    try:
        return json.loads(s)
    except Exception:
        return default or {}
