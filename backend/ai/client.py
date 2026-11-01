import json
import logging
from typing import Any, Dict, List, Tuple
import httpx
from backend.config import settings
from backend.schemas import CandidateAction, Recommendation
from backend.ai.prompts import SYSTEM_PROMPT, format_user_prompt

logger = logging.getLogger("ai_client")

class OpenCodeGoClient:
    """Client for OpenCode Go API (glm-5.3-flash) with robust fallback."""

    def __init__(self):
        self.api_key = settings.OPENCODE_GO_API_KEY
        self.base_url = settings.OPENCODE_GO_BASE_URL.rstrip("/")
        self.model = settings.OPENCODE_GO_MODEL

    async def prioritize_and_explain(
        self,
        inventory_summary: Dict[str, Any],
        candidates: List[CandidateAction]
    ) -> Tuple[List[Recommendation], bool, str]:
        """Queries glm-5.3-flash to explain and rank candidates.
        Returns: (recommendations, is_llm_assisted, notice_message)
        """
        if not candidates:
            return [], True, "لا توجد تحسينات مطلوبة حالياً."

        # If no API key provided, immediately fallback
        if not self.api_key:
            logger.info("OPENCODE_GO_API_KEY is not set. Using local deterministic fallback.")
            return self._local_fallback(candidates), False, "تم استخدام المحرك المحلي (مفتاح API غير متوفر)."

        endpoint = f"{self.base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "User-Agent": "HardwareOptimizer/1.0"
        }

        user_content = format_user_prompt(inventory_summary, candidates)
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_content}
            ],
            "temperature": 0.2,
            "response_format": {"type": "json_object"}
        }

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(endpoint, headers=headers, json=payload)
                if resp.status_code != 200:
                    logger.warning(f"OpenCode Go API returned HTTP {resp.status_code}: {resp.text}")
                    return self._local_fallback(candidates), False, f"تراجع تلقائي للمحرك المحلي (خطأ استجابة {resp.status_code})."

                data = resp.json()
                content = data["choices"][0]["message"]["content"]
                
                # Parse JSON
                parsed = json.loads(content)
                if isinstance(parsed, dict) and "recommendations" in parsed:
                    items = parsed["recommendations"]
                elif isinstance(parsed, list):
                    items = parsed
                else:
                    items = list(parsed.values())[0] if parsed else []

                return self._merge_llm_with_candidates(candidates, items), True, "تم التحليل والتوليد الذكي بواسطة GLM-5.3-Flash."

        except Exception as e:
            logger.error(f"Failed to query OpenCode Go API: {e}")
            return self._local_fallback(candidates), False, "تم التراجع للمحرك المحلي بسبب انقطاع الاتصال بالشبكة."

    def _merge_llm_with_candidates(
        self,
        candidates: List[CandidateAction],
        llm_items: List[Dict[str, Any]]
    ) -> List[Recommendation]:
        """Merges LLM responses strictly against valid candidates, dropping unknown action_ids."""
        candidate_map = {c.action_id.value: c for c in candidates}
        results = []

        seen_actions = set()
        for item in llm_items:
            action_id_str = item.get("action_id")
            if action_id_str in candidate_map and action_id_str not in seen_actions:
                candidate = candidate_map[action_id_str]
                seen_actions.add(action_id_str)
                results.append(Recommendation(
                    action_id=candidate.action_id,
                    subsystem=candidate.subsystem,
                    tier=candidate.tier,
                    title_ar=candidate.title_ar,
                    current_value=candidate.current_value,
                    proposed_value=candidate.proposed_value,
                    priority=int(item.get("priority", 5)),
                    rationale_ar=str(item.get("rationale_ar", candidate.description_ar)),
                    rollback_summary_ar=str(item.get("rollback_summary_ar", "يمكن التراجع بنقرة واحدة من سجل الجلسات.")),
                    requires_admin=candidate.requires_admin,
                    requires_reboot=candidate.requires_reboot,
                    target_identifier=candidate.target_identifier
                ))

        # Include any candidate that LLM missed
        for c in candidates:
            if c.action_id.value not in seen_actions:
                results.append(self._candidate_to_rec(c, default_priority=5))

        # Sort by priority descending
        results.sort(key=lambda r: r.priority, reverse=True)
        return results

    def _local_fallback(self, candidates: List[CandidateAction]) -> List[Recommendation]:
        results = [self._candidate_to_rec(c, default_priority=8 if c.tier == 1 else 5) for c in candidates]
        results.sort(key=lambda r: (r.tier.value, -r.priority))
        return results

    def _candidate_to_rec(self, candidate: CandidateAction, default_priority: int) -> Recommendation:
        rollback_desc = "يمكن التراجع بنقرة واحدة من لوحة التحكم."
        if candidate.action_id.value == "PWR_PLAN_PERF":
            rollback_desc = "إعادة تفعيل خطة الطاقة المتوازنة (Balanced)."
        elif candidate.action_id.value == "GPU_ENABLE_HAGS":
            rollback_desc = "إعادة قيمة HwSchMode إلى 1 ثم إعادة التشغيل."
        elif candidate.action_id.value == "STORAGE_ENABLE_TRIM":
            rollback_desc = "تعيين قيمة DisableDeleteNotify إلى 1."

        return Recommendation(
            action_id=candidate.action_id,
            subsystem=candidate.subsystem,
            tier=candidate.tier,
            title_ar=candidate.title_ar,
            current_value=candidate.current_value,
            proposed_value=candidate.proposed_value,
            priority=default_priority,
            rationale_ar=candidate.description_ar,
            rollback_summary_ar=rollback_desc,
            requires_admin=candidate.requires_admin,
            requires_reboot=candidate.requires_reboot,
            target_identifier=candidate.target_identifier
        )
