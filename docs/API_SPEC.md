# API 명세서

## 목차

1. [인증](#1-인증)
2. [피드 API](#2-피드-api)
3. [AI 생성 API](#3-ai-생성-api)
4. [미디어 API](#4-미디어-api)
5. [사용자 API](#5-사용자-api)
6. [광고 API (내부)](#6-광고-api-내부)
7. [에러 코드](#7-에러-코드)

---

## 1. 인증

### 1.1 Authentication

모든 API는 Bearer 토큰 기반 인증을 사용합니다.

```http
Authorization: Bearer <access_token>
```

### 1.2 토큰 발급

```http
POST /v1/auth/token
Content-Type: application/json

{
  "grant_type": "password",
  "username": "user@example.com",
  "password": "password123"
}

Response 200 OK:
{
  "access_token": "eyJhbGci...",
  "refresh_token": "eyJhbGci...",
  "token_type": "Bearer",
  "expires_in": 3600
}
```

---

## 2. 피드 API

### 2.1 기본 피드 조회

```http
GET /v1/feed
Authorization: Bearer <token>

Query Parameters:
- limit: int (default: 20, max: 50)
- cursor: string (pagination cursor)
- feed_type: string ("basic" | "personalized")

Response 200 OK:
{
  "feed_id": "feed_abc123",
  "type": "basic",
  "items": [
    {
      "id": "item_1",
      "type": "content",
      "content_id": "cnt_123",
      "content": {
        "title": "...",
        "description": "...",
        "media_url": "https://cdn.example.com/video.mp4",
        "thumbnail_url": "https://cdn.example.com/thumb.jpg",
        "duration_seconds": 75,
        "category": "wellness"
      },
      "position": 0
    },
    {
      "id": "item_2",
      "type": "ad",
      "ad_id": "ad_456",
      "ad": {
        "title": "...",
        "description": "...",
        "media_url": "...",
        "landing_url": "...",
        "placement_type": "inline"
      },
      "position": 10
    }
  ],
  "metadata": {
    "total_items": 20,
    "content_count": 18,
    "ad_count": 2
  },
  "next_cursor": "cursor_xyz"
}
```

### 2.2 피드 갱신

```http
POST /v1/feed/refresh
Authorization: Bearer <token>

Request Body:
{
  "feed_type": "basic"
}

Response 202 Accepted:
{
  "status": "refreshing",
  "estimated_time_seconds": 2,
  "feed_id": "feed_new123"
}

Response 200 OK (immediate):
{
  "status": "ready",
  "feed_id": "feed_new123",
  "items": [...]
}
```

---

## 3. AI 생성 API

### 3.1 AI 피드 생성 요청

```http
POST /v1/ai/generate-feed
Content-Type: application/json

Request Body:
{
  "user_id": "user_001",
  "prompt": "오늘 기분 좋은 패션 아이템 추천해줘"
}

Response 200 OK:
{
  "user_id": "user_001",
  "state": {
    "emotion": "기대감",
    "intent": "패션 쇼핑",
    "context": "일상적인 스타일 탐색"
  },
  "strategy": {
    "ad_placement": "inline",
    "content_tone": "밝고 트렌디한"
  },
  "creative": {
    "title": "오늘의 추천 패션 아이템",
    "body": "...",
    "cta": "지금 바로 확인하기"
  },
  "ad_candidates": [
    {
      "campaign_id": "camp_001",
      "title": "캠페인명",
      "score": 0.87,
      "image_url": "https://picsum.photos/..."
    }
  ],
  "generated_image_url": "http://localhost:8000/v1/media/generated_abc123.webp"
}

Response 400 Bad Request (quota exceeded):
{
  "error": "quota_exceeded",
  "message": "Daily AI generation limit reached (5/5)",
  "quota": {
    "used": 5,
    "limit": 5,
    "reset_at": "2026-02-25T00:00:00Z"
  }
}
```

### 3.2 생성 상태 조회

```http
GET /v1/ai/status/{request_id}
Authorization: Bearer <token>

Response 200 OK (processing):
{
  "request_id": "req_xyz789",
  "status": "processing",
  "progress": {
    "current_stage": "creative_generation",
    "stages": [
      {"name": "state_interpretation", "status": "completed"},
      {"name": "strategy_planning", "status": "completed"},
      {"name": "creative_generation", "status": "in_progress"}
    ]
  },
  "estimated_remaining_seconds": 4
}

Response 200 OK (completed):
{
  "request_id": "req_xyz789",
  "status": "completed",
  "result": {
    "content_id": "gen_abc123",
    "media": {
      "type": "video",
      "url": "https://cdn.example.com/generated/video_123.mp4",
      "thumbnail_url": "https://cdn.example.com/generated/thumb_123.jpg",
      "duration_seconds": 75
    },
    "script": {
      "full_text": "...",
      "scenes": [...]
    },
    "integrated_ads": [
      {
        "ad_id": "ad_456",
        "placement_type": "story_blend",
        "timestamp": "10-20s"
      }
    ]
  },
  "metadata": {
    "generation_time_seconds": 6.8,
    "cost_usd": 0.18
  }
}

Response 200 OK (failed):
{
  "request_id": "req_xyz789",
  "status": "failed",
  "error": {
    "code": "generation_timeout",
    "message": "Generation took too long and was terminated"
  }
}
```

### 3.3 생성 히스토리

```http
GET /v1/ai/history
Authorization: Bearer <token>

Query Parameters:
- limit: int (default: 10, max: 50)
- offset: int (default: 0)

Response 200 OK:
{
  "total": 47,
  "items": [
    {
      "request_id": "req_xyz789",
      "prompt": "오늘 기분 좋은 영상 보여줘",
      "status": "completed",
      "content_id": "gen_abc123",
      "thumbnail_url": "...",
      "created_at": "2026-02-24T14:30:00Z",
      "generation_time_seconds": 6.8
    },
    ...
  ]
}
```

### 3.4 생성 취소

```http
DELETE /v1/ai/cancel/{request_id}
Authorization: Bearer <token>

Response 200 OK:
{
  "request_id": "req_xyz789",
  "status": "cancelled"
}
```

---

## 4. 미디어 API

AI 생성 이미지/영상 파일을 다운로드합니다.

### 4.1 미디어 파일 다운로드

```http
GET /v1/media/{filename}

Path Parameters:
- filename: 생성된 미디어 파일명 (예: generated_abc123.webp)

Response 200 OK:
Content-Type: image/webp (또는 video/mp4)
[Binary file content]

Response 404 Not Found:
{
  "detail": "미디어 파일을 찾을 수 없습니다."
}
```

**사용 예시:**

AI 피드 생성 응답에서 `generated_image_url` 필드로 파일명을 확인한 뒤 다운로드합니다.

```bash
# 1. AI 피드 생성
curl -X POST http://localhost:8000/v1/ai/generate-feed \
  -H "Content-Type: application/json" \
  -d '{"user_id": "user_001", "prompt": "패션 아이템 추천"}' \
  | jq '.generated_image_url'
# → "http://localhost:8000/v1/media/generated_abc123.webp"

# 2. 이미지 다운로드
curl http://localhost:8000/v1/media/generated_abc123.webp \
  --output generated_image.webp
```

**생성 파일 형식:**
- 이미지: WebP (Vertex AI Imagen → PNG → WebP 변환, quality=85)
- 파일 저장 위치: `./generated_media/` (로컬 디렉토리에 영구 보관)

---

## 5. 사용자 API

### 4.1 프로필 조회

```http
GET /v1/user/profile
Authorization: Bearer <token>

Response 200 OK:
{
  "user_id": "user_123",
  "profile": {
    "display_name": "홍길동",
    "avatar_url": "...",
    "age": 32,
    "gender": "female",
    "country": "KR",
    "language": "ko"
  },
  "subscription": {
    "tier": "premium",
    "start_date": "2026-01-01",
    "end_date": "2027-01-01",
    "auto_renew": true,
    "features": [
      "unlimited_ai_generation",
      "ad_free",
      "priority_support"
    ]
  },
  "quotas": {
    "ai_generations_today": 3,
    "ai_generations_limit": -1,  // -1 = unlimited
    "last_reset": "2026-02-24T00:00:00Z"
  },
  "preferences": {
    "favorite_categories": ["wellness", "travel", "food"],
    "content_length": "medium",
    "notification_enabled": true
  }
}
```

### 4.2 선호도 업데이트

```http
PATCH /v1/user/preferences
Authorization: Bearer <token>
Content-Type: application/json

Request Body:
{
  "favorite_categories": ["wellness", "travel", "food", "tech"],
  "content_length": "short",
  "notification_enabled": false
}

Response 200 OK:
{
  "preferences": {
    "favorite_categories": ["wellness", "travel", "food", "tech"],
    "content_length": "short",
    "notification_enabled": false
  }
}
```

### 4.3 통계 조회

```http
GET /v1/user/stats
Authorization: Bearer <token>

Query Parameters:
- period: string ("7d" | "30d" | "90d" | "all")

Response 200 OK:
{
  "period": "30d",
  "activity": {
    "total_views": 234,
    "total_likes": 45,
    "total_shares": 12,
    "total_comments": 8,
    "avg_session_duration_minutes": 23.5,
    "session_count": 56
  },
  "ai_usage": {
    "total_generations": 18,
    "avg_generation_time_seconds": 7.2,
    "total_cost_usd": 3.24,
    "favorite_prompts": [
      "오늘 기분 좋은 영상",
      "명상 콘텐츠"
    ]
  },
  "content_breakdown": {
    "wellness": 0.35,
    "travel": 0.25,
    "food": 0.20,
    "tech": 0.15,
    "others": 0.05
  }
}
```

### 4.4 AI 생성 할당량 조회

```http
GET /v1/user/quota
Authorization: Bearer <token>

Response 200 OK:
{
  "quota": {
    "used_today": 3,
    "limit_daily": 5,
    "remaining": 2,
    "reset_at": "2026-02-25T00:00:00Z"
  },
  "cost_quota": {
    "used_today_usd": 0.54,
    "limit_daily_usd": 2.00,
    "remaining_usd": 1.46
  },
  "tier": "free",
  "upgrade_available": {
    "tier": "premium",
    "benefits": [
      "unlimited_ai_generation",
      "faster_processing",
      "priority_support"
    ],
    "price_monthly_usd": 9.99
  }
}
```

---

## 6. 광고 API (내부)

**Note:** 이 API는 광고주 대시보드와 내부 시스템에서만 사용됩니다.

### 5.1 캠페인 생성

```http
POST /v1/ads/campaigns
Authorization: Bearer <advertiser_token>
Content-Type: application/json

Request Body:
{
  "name": "Summer Health Promotion",
  "description": "...",
  "budget": {
    "total": 10000.00,
    "daily": 500.00,
    "currency": "USD"
  },
  "schedule": {
    "start_date": "2026-03-01",
    "end_date": "2026-03-31",
    "timezone": "Asia/Seoul"
  },
  "targeting": {
    "age_range": [25, 40],
    "genders": ["all"],
    "countries": ["KR", "JP"],
    "interests": ["health", "wellness"]
  },
  "ads": [
    {
      "creative_urls": {
        "image": "https://...",
        "video": "https://..."
      },
      "landing_url": "https://...",
      "bid_amount": 2.50,
      "bid_type": "cpm"
    }
  ]
}

Response 201 Created:
{
  "campaign_id": "camp_789",
  "status": "pending_review",
  "ads": [
    {
      "ad_id": "ad_456",
      "status": "pending_review"
    }
  ]
}
```

### 5.2 캠페인 성과 조회

```http
GET /v1/ads/campaigns/{campaign_id}/performance
Authorization: Bearer <advertiser_token>

Query Parameters:
- start_date: date (ISO 8601)
- end_date: date (ISO 8601)
- group_by: string ("day" | "hour")

Response 200 OK:
{
  "campaign_id": "camp_789",
  "period": {
    "start_date": "2026-03-01",
    "end_date": "2026-03-07"
  },
  "summary": {
    "impressions": 125430,
    "clicks": 5234,
    "conversions": 234,
    "ctr": 0.0417,
    "cvr": 0.0447,
    "spend_usd": 2543.20,
    "revenue_usd": 7234.50,
    "roi": 2.84
  },
  "daily_breakdown": [
    {
      "date": "2026-03-01",
      "impressions": 18234,
      "clicks": 756,
      "conversions": 34,
      "spend_usd": 364.68,
      "revenue_usd": 1045.20
    },
    ...
  ],
  "ad_breakdown": [
    {
      "ad_id": "ad_456",
      "impressions": 62715,
      "clicks": 2617,
      "conversions": 117,
      "ctr": 0.0417,
      "cvr": 0.0447
    }
  ]
}
```

---

## 7. 에러 코드

### 6.1 HTTP 상태 코드

| 코드 | 의미 | 설명 |
|------|------|------|
| 200 | OK | 요청 성공 |
| 201 | Created | 리소스 생성 성공 |
| 202 | Accepted | 비동기 처리 시작 |
| 400 | Bad Request | 잘못된 요청 |
| 401 | Unauthorized | 인증 실패 |
| 403 | Forbidden | 권한 없음 |
| 404 | Not Found | 리소스 없음 |
| 429 | Too Many Requests | Rate limit 초과 |
| 500 | Internal Server Error | 서버 에러 |
| 503 | Service Unavailable | 서비스 일시 중단 |

### 6.2 애플리케이션 에러 코드

```json
{
  "error": {
    "code": "error_code",
    "message": "Human readable error message",
    "details": {
      // Additional error details
    }
  }
}
```

| 에러 코드 | HTTP | 의미 |
|----------|------|------|
| `invalid_request` | 400 | 요청 형식 오류 |
| `missing_parameter` | 400 | 필수 파라미터 누락 |
| `invalid_parameter` | 400 | 파라미터 값 오류 |
| `authentication_failed` | 401 | 인증 실패 |
| `token_expired` | 401 | 토큰 만료 |
| `insufficient_permission` | 403 | 권한 부족 |
| `resource_not_found` | 404 | 리소스 없음 |
| `quota_exceeded` | 429 | 할당량 초과 |
| `rate_limit_exceeded` | 429 | Rate limit 초과 |
| `generation_failed` | 500 | AI 생성 실패 |
| `generation_timeout` | 500 | AI 생성 타임아웃 |
| `service_unavailable` | 503 | 서비스 일시 중단 |

### 6.3 에러 응답 예시

```json
// 할당량 초과
{
  "error": {
    "code": "quota_exceeded",
    "message": "Daily AI generation limit reached (5/5)",
    "details": {
      "quota": {
        "used": 5,
        "limit": 5,
        "reset_at": "2026-02-25T00:00:00Z"
      },
      "upgrade_tier": "premium",
      "upgrade_url": "/subscription/upgrade"
    }
  }
}

// 생성 실패
{
  "error": {
    "code": "generation_failed",
    "message": "Failed to generate content due to safety filters",
    "details": {
      "reason": "unsafe_content",
      "violated_policies": ["violence", "explicit_content"]
    }
  }
}

// Rate limit 초과
{
  "error": {
    "code": "rate_limit_exceeded",
    "message": "Too many requests. Please try again later.",
    "details": {
      "limit": 100,
      "window_seconds": 60,
      "retry_after_seconds": 23
    }
  }
}
```

---

## 8. Rate Limits

### 7.1 사용자 API

| 엔드포인트 | Free Tier | Premium Tier |
|-----------|-----------|--------------|
| `GET /v1/feed` | 60/min | 300/min |
| `POST /v1/ai/generate-feed` | 5/day | unlimited |
| `GET /v1/ai/status/*` | 120/min | 300/min |
| `GET /v1/user/*` | 60/min | 120/min |

### 7.2 Rate Limit 헤더

```http
X-RateLimit-Limit: 60
X-RateLimit-Remaining: 45
X-RateLimit-Reset: 1709024400
```

---

## 9. Webhooks (선택적)

### 8.1 AI 생성 완료 Webhook

광고주나 사용자는 AI 생성 완료 시 Webhook을 받을 수 있습니다.

```http
POST {webhook_url}
Content-Type: application/json

{
  "event": "ai_generation_completed",
  "timestamp": "2026-02-24T14:35:00Z",
  "data": {
    "request_id": "req_xyz789",
    "user_id": "user_123",
    "status": "completed",
    "content_id": "gen_abc123",
    "content_url": "https://...",
    "generation_time_seconds": 6.8
  }
}
```

### 8.2 Webhook 서명 검증

모든 Webhook 요청은 HMAC-SHA256 서명이 포함됩니다.

```http
X-Webhook-Signature: sha256=<signature>
```

검증:
```python
import hmac
import hashlib

def verify_webhook(payload: str, signature: str, secret: str) -> bool:
    expected = hmac.new(
        secret.encode(),
        payload.encode(),
        hashlib.sha256
    ).hexdigest()

    return hmac.compare_digest(f"sha256={expected}", signature)
```

---

**문서 버전:** 1.1
**최종 수정일:** 2026-02-25
