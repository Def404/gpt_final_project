RESEARCH_PLAN_JSON_SCHEMA = """
{
    "type": "object",
    "properties": {
        "search_query": {
            "type": "string",
            "description": "Один поисковый запрос по вопросу пользователя"
        }
    },
    "required": ["search_query"],
    "additionalProperties": false
}
""".strip()


ANSWER_JSON_SCHEMA = """
{
    "type": "object",
    "properties": {
        "reasoning_summary": {
            "type": "string",
            "description": "Краткое резюме процесса рассуждений. Около 50 слов."
        },
        "relevant_sources": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "file_name": { "type": "string", "description": "Название файла источника" },
                    "url": { "type": "string", "description": "URL источника (может быть null или пустой строкой)" }
                },
                "required": ["file_name"],
                "additionalProperties": false
            },
            "description": "Список источников, содержащих информацию, непосредственно использованную для ответа. Включайте только источники с прямыми ответами или явными утверждениями, с ключевой информацией, которая сильно поддерживает ответ. Не включайте источники только с косвенно связанной информацией или слабыми связями с ответом. Должен быть включен хотя бы один источник, если есть информация."
        },
        "final_answer": {
            "type": "string",
            "description": "Финальный ответ пользователю в формате markdown. Если это название компании, должно быть извлечено точно так, как оно появляется в вопросе. Если это имя человека, должно быть полное имя. Если это название продукта, должно быть извлечено точно так, как оно появляется в контексте. Без лишней информации, слов или комментариев. При полном отсутствии информации в контексте используй шаблон отказа из системной инструкции."
        }
    },
    "required": ["reasoning_summary", "relevant_sources", "final_answer"],
    "additionalProperties": false
}
""".strip()

