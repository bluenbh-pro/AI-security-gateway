"""
Agent 결과 캐싱 시스템

목적: Orchestrator 평가 성능 개선
- A1, A2, A3, A5의 동일 입력에 대한 재계산 방지
- 동일 프롬프트(A1, A3, A5)나 프롬프트+context(A2) 캐시

캐시 전략:
- A1: hash(prompt) → A1Result
- A2: hash(prompt + user_context) → A2Result
- A3: hash(prompt) → A3Result
- A5: hash(prompt) → A5Result
"""

import hashlib
import json
from typing import Dict, Any, Optional, Tuple
from pathlib import Path
import os


class AgentCache:
    """각 Agent별 결과 캐싱"""

    def __init__(self, cache_dir: str = ".cache/agent_cache"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        # 메모리 캐시 (빠른 접근용)
        self.memory_cache = {
            "a1": {},
            "a2": {},
            "a3": {},
            "a5": {}
        }

        # 캐시 통계
        self.stats = {
            "a1_hits": 0,
            "a1_misses": 0,
            "a2_hits": 0,
            "a2_misses": 0,
            "a3_hits": 0,
            "a3_misses": 0,
            "a5_hits": 0,
            "a5_misses": 0,
        }

    @staticmethod
    def _make_key(prompt: str, user_context: Optional[Dict[str, Any]] = None) -> str:
        """프롬프트(+user_context) 기반 캐시 키 생성"""
        if user_context:
            # A2용: prompt + user_context 해시
            combined = f"{prompt}||{json.dumps(user_context, sort_keys=True, ensure_ascii=False)}"
        else:
            # A1, A3, A5용: prompt만 해시
            combined = prompt

        return hashlib.md5(combined.encode('utf-8')).hexdigest()

    # ═══════════════════════════════════════════════════════════════
    # A1 캐시
    # ═══════════════════════════════════════════════════════════════

    def get_a1(self, prompt: str) -> Optional[Dict[str, Any]]:
        """A1 결과 조회"""
        key = self._make_key(prompt)

        if key in self.memory_cache["a1"]:
            self.stats["a1_hits"] += 1
            return self.memory_cache["a1"][key]

        self.stats["a1_misses"] += 1
        return None

    def set_a1(self, prompt: str, result: Dict[str, Any]) -> None:
        """A1 결과 저장"""
        key = self._make_key(prompt)
        self.memory_cache["a1"][key] = result

    # ═══════════════════════════════════════════════════════════════
    # A2 캐시
    # ═══════════════════════════════════════════════════════════════

    def get_a2(self, prompt: str, user_context: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """A2 결과 조회"""
        key = self._make_key(prompt, user_context)

        if key in self.memory_cache["a2"]:
            self.stats["a2_hits"] += 1
            return self.memory_cache["a2"][key]

        self.stats["a2_misses"] += 1
        return None

    def set_a2(self, prompt: str, user_context: Dict[str, Any], result: Dict[str, Any]) -> None:
        """A2 결과 저장"""
        key = self._make_key(prompt, user_context)
        self.memory_cache["a2"][key] = result

    # ═══════════════════════════════════════════════════════════════
    # A3 캐시
    # ═══════════════════════════════════════════════════════════════

    def get_a3(self, prompt: str) -> Optional[Dict[str, Any]]:
        """A3 결과 조회"""
        key = self._make_key(prompt)

        if key in self.memory_cache["a3"]:
            self.stats["a3_hits"] += 1
            return self.memory_cache["a3"][key]

        self.stats["a3_misses"] += 1
        return None

    def set_a3(self, prompt: str, result: Dict[str, Any]) -> None:
        """A3 결과 저장"""
        key = self._make_key(prompt)
        self.memory_cache["a3"][key] = result

    # ═══════════════════════════════════════════════════════════════
    # A5 캐시
    # ═══════════════════════════════════════════════════════════════

    def get_a5(self, prompt: str) -> Optional[Dict[str, Any]]:
        """A5 결과 조회"""
        key = self._make_key(prompt)

        if key in self.memory_cache["a5"]:
            self.stats["a5_hits"] += 1
            return self.memory_cache["a5"][key]

        self.stats["a5_misses"] += 1
        return None

    def set_a5(self, prompt: str, result: Dict[str, Any]) -> None:
        """A5 결과 저장"""
        key = self._make_key(prompt)
        self.memory_cache["a5"][key] = result

    # ═══════════════════════════════════════════════════════════════
    # 캐시 통계
    # ═══════════════════════════════════════════════════════════════

    def get_stats(self) -> Dict[str, Any]:
        """캐시 히트율 통계"""
        stats_detail = {}

        for agent in ["a1", "a2", "a3", "a5"]:
            hits = self.stats.get(f"{agent}_hits", 0)
            misses = self.stats.get(f"{agent}_misses", 0)
            total = hits + misses
            hit_rate = (hits / total * 100) if total > 0 else 0

            stats_detail[agent] = {
                "hits": hits,
                "misses": misses,
                "total": total,
                "hit_rate": hit_rate
            }

        return stats_detail

    def print_stats(self) -> None:
        """캐시 통계 출력"""
        stats = self.get_stats()

        print("\n" + "=" * 80)
        print("[Agent Cache Statistics]")
        print("=" * 80)

        total_hits = sum(s["hits"] for s in stats.values())
        total_requests = sum(s["total"] for s in stats.values())
        overall_hit_rate = (total_hits / total_requests * 100) if total_requests > 0 else 0

        for agent, detail in stats.items():
            print(f"\nAgent {agent.upper()}:")
            print(f"  Hits:     {detail['hits']:4} / {detail['total']:4} = {detail['hit_rate']:6.2f}%")

        print(f"\n{'─'*80}")
        print(f"Overall Hit Rate: {total_hits:4} / {total_requests:4} = {overall_hit_rate:6.2f}%")
        print(f"Expected Time Savings: {overall_hit_rate:.1f}% (LLM 호출 감소)")
        print("=" * 80)

    def clear(self) -> None:
        """캐시 초기화"""
        self.memory_cache = {
            "a1": {},
            "a2": {},
            "a3": {},
            "a5": {}
        }
        self.stats = {
            "a1_hits": 0,
            "a1_misses": 0,
            "a2_hits": 0,
            "a2_misses": 0,
            "a3_hits": 0,
            "a3_misses": 0,
            "a5_hits": 0,
            "a5_misses": 0,
        }


# 글로벌 캐시 인스턴스
_cache_instance = None


def get_cache() -> AgentCache:
    """전역 캐시 인스턴스 획득"""
    global _cache_instance
    if _cache_instance is None:
        _cache_instance = AgentCache()
    return _cache_instance
