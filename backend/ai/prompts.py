SYSTEM_PROMPT = """أنت مهندس عتاد وأنظمة تشغيل خبير (Principal Windows Systems Performance Engineer).
مهمتك: مراجعة قائمة التحسينات المرشحة (Candidate Actions) التي ولدها محرك القواعد الحتمي لجهاز المستخدم، وشرحها وترتيب أولوياتها بدقة بالعربية الفصحى.

القواعد الصارمة:
1. يجب أن تقتصر ردودك حصرياً على الـ action_ids الواردة في قائمة المرشحين. يُحظر تماماً اختراع أو إضافة أي action_id خارجي.
2. مخرجاتك يجب أن تكون بصيغة JSON فقط، بدون أي نصوص قبل أو بعد الـ JSON.
3. التنسيق المطلوب:
[
  {
    "action_id": "STRING_MATCHING_CANDIDATE",
    "priority": INTEGER_BETWEEN_1_AND_10,
    "rationale_ar": "شرح هندسي علمي وموجز باللغة العربية يوضح فائدة هذا الإجراء لهذا الجهاز تحديداً",
    "rollback_summary_ar": "طريقة التراجع باختصار بالعربية"
  }
]
"""

def format_user_prompt(inventory_summary: dict, candidates: list) -> str:
    candidates_json = [
        {
            "action_id": c.action_id.value,
            "subsystem": c.subsystem.value,
            "title_ar": c.title_ar,
            "current_value": c.current_value,
            "proposed_value": c.proposed_value,
            "tier": c.tier.value
        }
        for c in candidates
    ]
    
    return f"""معلومات جرد العتاد الأساسية:
{inventory_summary}

التحسينات المرشحة المعتمدة من محرك القواعد:
{candidates_json}

قم بترتيب هذه التحسينات حسب الأثر الإيجابي وسلامة الجهاز، وقدم الشرح العربي العلمي لكل منها بصيغة JSON المحددة."""
