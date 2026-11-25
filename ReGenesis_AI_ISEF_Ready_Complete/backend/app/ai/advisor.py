import os
import json
from typing import Dict, Any, List
import httpx
from backend.app.core.config import settings
from backend.app.ai.knowledge_base import retrieve
from backend.app.ai.web_search import search_web, needs_web_search, format_search_context
from backend.app.ai.climate_trace import search_industrial_assets
from backend.app.ai.matching_engine import SmartMatchingEngine

class AIAdvisor:
    """
    Intelligent Assistant grounded in live ReGenesis AI database records.
    Provides guidance on materials, buyers, suppliers, matching results, upcycling routes,
    carbon accounting, and marketplace operations.
    Integrates with LLM API (Gemini/OpenAI) if configured, or runs grounded expert rules.
    """

    SYSTEM_PROMPT = """أنت REGENESIS AI، وكيل متخصص في الاقتصاد الدائري الصناعي وإدارة المخلفات والاستدامة.
أجب بلغة المستخدم (العربية أو الإنجليزية) وبأسلوب مهني واضح ومحدد.
استخدم قاعدة المعرفة المحلية المرفقة (كتالوج 18 خامة و18 مسار تدوير/Upcycling) للإجابة عن مواصفات الخامات، الفحوص، خطوات المعالجة، النواتج المحتملة، القطاعات المستفيدة والقيود.
استخدم بيانات السوق والمصانع التي تصلك فقط عند تسمية المصانع أو ذكر الأسعار أو الكميات أو أماكنها.
ميّز دائماً بين ثلاثة أنواع: (1) دليل منشآت عام ومصدره مذكور لكنه غير متحقق تجارياً، (2) سيناريوهات عرض افتراضية، (3) بيانات أدخلها مستخدم حقيقي. لا تحول الدليل العام إلى مورد متاح ولا السيناريو الافتراضي إلى عرض/طلب حقيقي.
الأسعار والكمّيات وصور بطاقات العرض التجريبية توضيحية فقط إذا كان مصدر السجل demo_synthetic؛ لا تصفها كسعر سوق أو مخزون فعلي.
لا تخترع مصانع أو أسعاراً أو كميات أو نسب مطابقة أو وفراً كربونياً. إذا لم تتوفر البيانات فقل ذلك بوضوح.
ميّز بين الحقائق المسجلة والتوصيات التقديرية. لا تدّعِ تنفيذ إجراء أو تعديل قاعدة البيانات؛ أنت تقرأ وتقترح فقط.
التحليل من صورة يحدد ملاحظات مرئية محتملة فقط ولا يثبت نوع البوليمر أو التركيب الكيميائي أو النقاء أو خلو المادة من الخطر. التزم بفحوص المعمل والاشتراطات قبل المعالجة أو الشراء.
"""

    @classmethod
    def _tool_search_listings(cls, listings: List[Dict[str, Any]], category: str = "", keyword: str = "") -> Dict[str, Any]:
        rows = listings
        if category:
            rows = [x for x in rows if category.lower() in str(x.get("category", "")).lower()]
        if keyword:
            key = keyword.lower()
            rows = [x for x in rows if key in " ".join(str(x.get(k, "")) for k in ("title", "description", "factory", "city", "category")).lower()]
        return {"count": len(rows), "records": rows[:15]}

    @classmethod
    def _tool_search_factories(cls, factories: List[Dict[str, Any]], keyword: str = "", sector: str = "", city: str = "") -> Dict[str, Any]:
        rows = factories
        if keyword:
            key = keyword.lower()
            rows = [x for x in rows if key in " ".join(str(x.get(k, "")) for k in ("name", "sector", "city", "description", "source_name")).lower()]
        if sector:
            rows = [x for x in rows if sector.lower() in str(x.get("sector", "")).lower()]
        if city:
            rows = [x for x in rows if city.lower() in str(x.get("city", "")).lower()]
        return {"count": len(rows), "records": rows[:20], "warning": "Public directory entries may be unverified; demo_synthetic profiles are fictional showcase data."}

    @classmethod
    def _tool_find_opportunities(cls, listings: List[Dict[str, Any]], category: str = "") -> Dict[str, Any]:
        offers, demands = [], []
        for row in listings:
            trade = str(row.get("trade_type") or row.get("tradeType") or "")
            if category and category.lower() not in str(row.get("category", "")).lower():
                continue
            if "عرض" in trade or "offer" in trade.lower():
                offers.append(row)
            elif "طلب" in trade or "demand" in trade.lower():
                demands.append(row)
        pairs = []
        for offer in offers:
            for demand in demands:
                if str(offer.get("category", "")).lower() != str(demand.get("category", "")).lower():
                    continue
                score, details = SmartMatchingEngine.score_listings(offer, demand)
                simulated = offer.get("data_origin") == "demo_synthetic" or demand.get("data_origin") == "demo_synthetic"
                pairs.append({
                    "supplier": offer,
                    "potential_buyer": demand,
                    "shared_category": offer.get("category"),
                    "preliminary_score": score,
                    "score_breakdown": details.get("breakdown", {}),
                    "reasons": details.get("reasons", []),
                    "missing_info": details.get("missing_info", []),
                    "data_status": "سيناريو افتراضي" if simulated else "إعلانات غير متحققة تجارياً",
                    "warning": "فرصة أولية فقط؛ لا تعني قبولاً فنياً أو عرضاً حقيقياً أو صفقة.",
                })
        pairs.sort(key=lambda item: item["preliminary_score"], reverse=True)
        return {"offers": len(offers), "demands": len(demands), "potential_pairs": pairs[:10]}

    @classmethod
    async def _answer_with_ollama(cls, query: str, active_listings: List[Dict[str, Any]], history: List[Dict[str, str]] | None = None, web_results: List[Dict[str, str]] | None = None, factory_records: List[Dict[str, Any]] | None = None) -> Dict[str, Any] | None:
        base = settings.OLLAMA_BASE_URL.rstrip("/")
        tools = [
            {"type": "function", "function": {"name": "search_marketplace", "description": "ابحث في إعلانات السوق مع إظهار ما إذا كان السجل تجريبياً أو مدخلاً من مستخدم.", "parameters": {"type": "object", "properties": {"category": {"type": "string"}, "keyword": {"type": "string"}}, "required": []}}},
            {"type": "function", "function": {"name": "search_factories", "description": "ابحث في دليل المنشآت المصري. اذكر مصدر السجل وحالة التحقق، ولا تفترض وجود عرض مخلفات أو تواصل تجاري.", "parameters": {"type": "object", "properties": {"keyword": {"type": "string"}, "sector": {"type": "string"}, "city": {"type": "string"}}, "required": []}}},
            {"type": "function", "function": {"name": "find_matching_opportunities", "description": "استخرج عروض المخلفات وطلبات المصانع ذات الفئة المشتركة من بيانات المنصة. هذه فرص أولية وليست مطابقة فنية مؤكدة.", "parameters": {"type": "object", "properties": {"category": {"type": "string"}}, "required": []}}},
            {"type": "function", "function": {"name": "estimate_material_pathways", "description": "استرجع إرشادات أولية لمسارات معالجة مادة صناعية من قاعدة المعرفة المحلية.", "parameters": {"type": "object", "properties": {"material": {"type": "string"}}, "required": ["material"]}}},
            {"type": "function", "function": {"name": "estimate_platform_carbon", "description": "احسب تقديراً أولياً للانبعاثات المتجنبة باستخدام معامل الفئة المسجل في بيانات المنصة فقط.", "parameters": {"type": "object", "properties": {"category": {"type": "string"}, "quantity_tons": {"type": "number"}}, "required": ["category", "quantity_tons"]}}},
            {"type": "function", "function": {"name": "search_public_industrial_assets", "description": "ابحث في سجلات منشآت الانبعاثات الصناعية العامة لدى Climate TRACE. هذه السجلات ليست دليلاً على وجود مورد مخلفات أو مشتري ولا تحتوي بالضرورة على بيانات اتصال.", "parameters": {"type": "object", "properties": {"country_code": {"type": "string"}, "sector": {"type": "string"}, "year": {"type": "integer"}, "limit": {"type": "integer"}}, "required": []}}}
        ]
        docs = retrieve(query, limit=5)
        rag_context = "\n".join(f"[{d['title']}] {d['text']}" for d in docs)
        web_context = format_search_context(web_results or []) if web_results else "لم يتم إجراء بحث ويب لهذا السؤال."
        factory_records = factory_records or []
        market_context = json.dumps(active_listings[:80], ensure_ascii=False)
        factory_context = json.dumps(factory_records[:100], ensure_ascii=False)
        system = cls.SYSTEM_PROMPT + f"\nعدد سجلات السوق: {len(active_listings)}. عدد سجلات دليل المنشآت: {len(factory_records)}.\nعينة سجلات السوق (قد تضم سيناريوهات افتراضية موسومة بوضوح):\n{market_context}\nعينة دليل المنشآت مع مصدر البيانات وحالة التحقق: \n{factory_context}\nمعرفة مرجعية مسترجعة (إرشادية وليست بديلاً عن الاختبارات):\n{rag_context}\nنتائج بحث الويب (مصادر خارجية غير موثقة تلقائياً؛ قارنها قبل الاعتماد):\n{web_context}\nاذكر المصادر باستخدام عناوينها وروابطها عند الاستناد إليها، ولا تعتبر مقتطف البحث حقيقة مؤكدة."
        messages = [{"role": "system", "content": system}]
        for item in (history or [])[-10:]:
            role = item.get("role")
            content = str(item.get("content", ""))[:3000]
            if role in ("user", "assistant") and content:
                messages.append({"role": role, "content": content})
        messages.append({"role": "user", "content": query})
        timeout = httpx.Timeout(settings.OLLAMA_TIMEOUT_SECONDS)
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(f"{base}/api/chat", json={"model": settings.OLLAMA_MODEL, "messages": messages, "tools": tools, "stream": False, "options": {"temperature": 0.35}})
            response.raise_for_status()
            payload = response.json()
            message = payload.get("message", {})
            # Execute a bounded number of read-only tools; no database writes are exposed.
            for _ in range(3):
                calls = message.get("tool_calls") or []
                if not calls:
                    break
                messages.append(message)
                for call in calls:
                    fn = call.get("function", {})
                    name, args = fn.get("name"), fn.get("arguments") or {}
                    if isinstance(args, str):
                        try: args = json.loads(args)
                        except json.JSONDecodeError: args = {}
                    if name == "search_marketplace":
                        result = cls._tool_search_listings(active_listings, str(args.get("category", "")), str(args.get("keyword", "")))
                    elif name == "search_factories":
                        result = cls._tool_search_factories(factory_records or [], str(args.get("keyword", "")), str(args.get("sector", "")), str(args.get("city", "")))
                    elif name == "find_matching_opportunities":
                        result = cls._tool_find_opportunities(active_listings, str(args.get("category", "")))
                    elif name == "estimate_material_pathways":
                        docs_for_material = retrieve(str(args.get("material", query)), limit=4)
                        result = {"reference_notes": docs_for_material, "warning": "Preliminary guidance only; laboratory validation required."}
                    elif name == "search_public_industrial_assets":
                        result = await search_industrial_assets(str(args.get("country_code", "EGY")), str(args.get("sector", "manufacturing")), int(args.get("year", 2025)), int(args.get("limit", 10)))
                    elif name == "estimate_platform_carbon":
                        category = str(args.get("category", ""))
                        qty = max(0.0, float(args.get("quantity_tons", 0) or 0))
                        candidates = [x for x in active_listings if category.lower() in str(x.get("category", "")).lower() and x.get("co2_factor") is not None]
                        factor = candidates[0].get("co2_factor") if candidates else None
                        result = ({"category": category, "quantity_tons": qty, "platform_factor_tco2_per_ton": factor, "scenario_result_tco2": round(qty * float(factor), 3), "basis": "user-supplied or documented factor required", "status": "scenario_calculation_only", "warning": "لا تمثل انبعاثات متجنبة فعلية أو شهادة كربون. لا توجد منهجية/معامل موثق في هذه النسخة."} if factor is not None and float(factor) > 0 else {"error": "No verified carbon factor is configured. Supply a documented factor and system boundary before estimating."})
                    else:
                        result = {"error": "Unknown or unavailable tool"}
                    messages.append({"role": "tool", "content": json.dumps(result, ensure_ascii=False)})
                response = await client.post(f"{base}/api/chat", json={"model": settings.OLLAMA_MODEL, "messages": messages, "tools": tools, "stream": False, "options": {"temperature": 0.35}})
                response.raise_for_status()
                payload = response.json()
                message = payload.get("message", {})
            answer = str(message.get("content", "")).strip()
            if not answer:
                return None
            return {"answer": answer, "records_considered": len(active_listings),
                    "mode": "ollama-local-agent", "suggested_actions": ["البحث عن موردين ومشترين", "تحليل مسار إعادة الاستخدام", "مراجعة فرص المطابقة"], "sources": web_results or []}

    @classmethod
    async def stream_answer(cls, query: str, active_listings: List[Dict[str, Any]], history: List[Dict[str, str]] | None = None, factory_records: List[Dict[str, Any]] | None = None):
        """Stream generated text from local Ollama; falls back to the grounded advisor."""
        import httpx
        web_results = []
        if settings.WEB_SEARCH_ENABLED and needs_web_search(query):
            try:
                web_results = await search_web(query, max_results=5)
            except Exception:
                web_results = []
        if settings.OLLAMA_ENABLED:
            docs = retrieve(query, limit=5)
            rag_context = "\n".join(f"[{d['title']}] {d['text']}" for d in docs)
            market = "\n".join(f"- {x.get('factory')}: {x.get('title')} | {x.get('category')} | {x.get('qty')} {x.get('unit','tons')} | {x.get('tradeType')} | {x.get('city')} | السعر {x.get('price')} {x.get('currency','')} | origin={x.get('data_origin')} | basis={x.get('price_basis')}" for x in active_listings[:80])
            facilities = "\n".join(f"- {x.get('name')} | {x.get('sector')} | {x.get('role')} | {x.get('city')} | verified={x.get('is_verified')} | origin={x.get('data_origin')} | source={x.get('source_name')}" for x in (factory_records or [])[:100])
            web_context = format_search_context(web_results) if web_results else "لم يتم إجراء بحث ويب لهذا السؤال."
            messages = [{"role":"system", "content": cls.SYSTEM_PROMPT + "\nكتالوج الخامات ومسارات المعالجة المسترجعة:\n" + rag_context + "\nسجلات سوق المنصة (مع نوع مصدر كل سجل):\n" + market + "\nدليل المنشآت العام/التجريبي (مع المصدر وحالة التحقق):\n" + facilities + "\nنتائج بحث الويب:\n" + web_context + "\nاستشهد بالمصادر بروابطها ولا تعرض مقتطف البحث كحقيقة مؤكدة."}]
            for item in (history or [])[-10:]:
                if item.get("role") in ("user", "assistant") and item.get("content"):
                    messages.append({"role":item["role"],"content":str(item["content"])[:3000]})
            messages.append({"role":"user","content":query})
            try:
                timeout=httpx.Timeout(settings.OLLAMA_TIMEOUT_SECONDS)
                async with httpx.AsyncClient(timeout=timeout) as client:
                    async with client.stream("POST", settings.OLLAMA_BASE_URL.rstrip("/")+"/api/chat", json={"model":settings.OLLAMA_MODEL,"messages":messages,"stream":True,"options":{"temperature":0.3}}) as response:
                        response.raise_for_status()
                        async for line in response.aiter_lines():
                            if not line: continue
                            try: payload=json.loads(line)
                            except json.JSONDecodeError: continue
                            token=payload.get("message",{}).get("content","")
                            if token: yield token
                            if payload.get("done"): return
                return
            except Exception:
                pass
        fallback=await cls.answer(query,active_listings,history,factory_records=factory_records)
        answer=fallback.get("answer","")
        for i in range(0,len(answer),36):
            yield answer[i:i+36]

    @classmethod
    async def answer(cls, query: str, active_listings: List[Dict[str, Any]], history: List[Dict[str, str]] | None = None, factory_records: List[Dict[str, Any]] | None = None) -> Dict[str, Any]:
        msg = query.strip()
        low = msg.lower()
        web_results = []
        if settings.WEB_SEARCH_ENABLED and needs_web_search(msg):
            try:
                web_results = await search_web(msg, max_results=5)
            except Exception:
                web_results = []

        # Prefer a free local model through Ollama. No API key or paid inference is needed.
        if settings.OLLAMA_ENABLED:
            try:
                ollama_result = await cls._answer_with_ollama(msg, active_listings, history, web_results, factory_records)
                if ollama_result:
                    return ollama_result
            except Exception:
                # Keep the platform usable if Ollama is not installed, stopped, or still downloading.
                pass

        # Optional cloud fallback for users who already configured Gemini.
        if settings.GEMINI_API_KEY:
            try:
                import google.generativeai as genai
                genai.configure(api_key=settings.GEMINI_API_KEY)
                model = genai.GenerativeModel("gemini-1.5-flash")
                
                context_summary = f"قاعدة بيانات ReGenesis AI تحتوي على {len(active_listings)} إعلاناً نشطاً للمخلفات والخامات.\n"
                for l in active_listings[:8]:
                    context_summary += f"- {l.get('factory')}: {l.get('title')} ({l.get('qty')} {l.get('unit','طن')}، {l.get('tradeType')}, {l.get('price')} {l.get('currency','EGP')}/{l.get('unit','طن')}, {l.get('city')}, origin={l.get('data_origin')})\n"
                
                factory_context = "\n".join(f"- {f.get('name')} / {f.get('sector')} / {f.get('city')} / verified={f.get('is_verified')} / origin={f.get('data_origin')} / source={f.get('source_name')}" for f in (factory_records or [])[:100])
                system_prompt = (
                    cls.SYSTEM_PROMPT + "\nسجلات السوق الحالية ومصدر كل سجل:\n" + context_summary +
                    "\nدليل المنشآت مع المصدر وحالة التحقق:\n" + factory_context +
                    "\nسؤال المستخدم: " + msg
                )
                response = model.generate_content(system_prompt)
                return {
                    "answer": response.text,
                    "records_considered": len(active_listings),
                    "mode": "llm-gemini-grounded",
                    "suggested_actions": ["استعراض سوق الخامات", "إضافة طلب أو عرض جديد", "تشغيل محاكي الـ Upcycling"],
                    "sources": web_results
                }
            except Exception as e:
                # Fallback to grounded rule-based engine cleanly
                pass

        # Transparent offline fallback using the same packaged knowledge files as the local model.
        # This path is intentionally conservative and labels simulated marketplace records.
        categories = {
            "خشب": ["خشب", "نشارة", "wood", "sawdust", "mdf"],
            "بلاستيك": ["بلاستيك", "pet", "hdpe", "pp", "plastic", "بوليمر", "مواسير"],
            "معادن": ["معدن", "ألومنيوم", "حديد", "نحاس", "صلب", "metal", "aluminum", "copper", "steel"],
            "نسيج": ["نسيج", "قطن", "قماش", "ألياف", "textile", "cotton", "polyester"],
            "زجاج": ["زجاج", "سيراميك", "glass", "cullet"],
            "ورق": ["ورق", "كرتون", "paper", "cardboard"],
            "مطاط": ["مطاط", "إطارات", "rubber", "tire"],
            "إلكترونيات": ["إلكترونيات", "الكترونيات", "لوحات", "pcb", "e-waste"],
            "عضوي": ["عضوي", "غذائي", "food waste", "organic"],
            "مخلفات معدنية/إنشائية": ["خبث", "رماد", "جبس", "إنشائية", "slag", "fly ash", "gypsum"],
        }
        matched_cat = None
        for cat_name, keywords in categories.items():
            if any(k in low for k in keywords):
                matched_cat = cat_name
                break

        relevant_listings = [
            row for row in active_listings
            if not matched_cat or matched_cat in str(row.get("category", ""))
        ]
        suggested_actions = ["تصفح سوق الخامات", "مراجعة مسارات التدوير", "إضافة عرض أو طلب"]

        # Search for facilities when the user asks for a recycler, factory, or supplier.
        facility_hits = []
        wants_facilities = any(w in low for w in ["مصنع", "مصانع", "منشأة", "منشآت", "دليل", "شركة تدوير", "شركات تدوير", "recycler", "factory", "plant"])
        if factory_records and wants_facilities:
            city_filter = next((city for city in ["القاهرة", "الجيزة", "الإسكندرية", "الاسكندرية", "دمياط", "العاشر من رمضان", "السادس من أكتوبر", "برج العرب", "مدينة السادات", "حلوان"] if city in low), "")
            for row in factory_records:
                hay = " ".join(str(row.get(k, "")) for k in ("name", "sector", "role", "city", "description")).lower()
                if city_filter and city_filter not in str(row.get("city", "")):
                    continue
                if matched_cat and matched_cat.lower() not in hay:
                    continue
                if "مصانع" in low or "مصنع" in low or "دليل" in low or "recycler" in low:
                    if "recycler" not in str(row.get("role", "")).lower() and not any(k in hay for k in ["تدوير", "إعادة تدوير", "recycl"]):
                        continue
                facility_hits.append(row)
            facility_hits = facility_hits[:8]

        # Explicit factory-directory questions are answered from source-attributed facility records.
        if wants_facilities and facility_hits and not any(w in low for w in ["مطابق", "match", "buyer", "supplier", "شراء", "بيع"]):
            answer = "سجلات منشآت من الدليل العام المضمّن (كلها غير متحققة داخل المنصة):\n" + "\n".join(
                f"- {f.get('name')} — {f.get('sector')} — {f.get('city')} — الدور المنشور: {f.get('role')} — المصدر: {f.get('source_name') or 'مصدر بيانات غير محدد'} — التحقق داخل REGENESIS: {'متحقق' if f.get('is_verified') else 'غير متحقق'}"
                for f in facility_hits
            ) + "\n\nوجود السجل لا يثبت استمرار النشاط أو توفر خردة أو قبول مادة بعينها. راجع المصدر الأصلي واتصل بالمنشأة وتحقق من التصاريح قبل التعامل."

        # Supply-demand matching is based on recorded listings, not only on a category label.
        elif any(w in low for w in ["مطابق", "مشتري", "مورد", "مصنع", "مصانع", "match", "buyer", "supplier", "شراء", "بيع"]):
            offers = [row for row in active_listings if "عرض" in str(row.get("trade_type") or row.get("tradeType") or "")]
            demands = [row for row in active_listings if "طلب" in str(row.get("trade_type") or row.get("tradeType") or "")]
            if matched_cat:
                offers = [row for row in offers if matched_cat in str(row.get("category", ""))]
                demands = [row for row in demands if matched_cat in str(row.get("category", ""))]
            pairs = []
            for offer in offers:
                for demand in demands:
                    if offer.get("category") == demand.get("category"):
                        score, detail = SmartMatchingEngine.score_listings(offer, demand)
                        pairs.append((score, offer, demand, detail))
            pairs.sort(key=lambda item: item[0], reverse=True)
            if pairs:
                score, offer, demand, detail = pairs[0]
                simulated = offer.get("data_origin") == "demo_synthetic" or demand.get("data_origin") == "demo_synthetic"
                tag = "سيناريو افتراضي للعرض، وليس صفقة فعلية" if simulated else "سجلات إعلانات غير متحققة من الطرفين"
                answer = (
                    f"🎯 فرصة توافق أولية في فئة {offer.get('category')}:\n"
                    f"- العرض: {offer.get('title')} لدى {offer.get('factory')} في {offer.get('city')}، "
                    f"{offer.get('qty')} {offer.get('unit','طن')}، نقاء مسجل {offer.get('purity')}%، "
                    f"قيمة معلنة/توضيحية {offer.get('price')} {offer.get('currency','EGP')}/{offer.get('unit','طن')}.\n"
                    f"- الطلب: {demand.get('title')} لدى {demand.get('factory')} في {demand.get('city')}، "
                    f"{demand.get('qty')} {demand.get('unit','طن')}، مواصفة نقاء مسجلة {demand.get('purity')}%.\n"
                    f"- درجة التوافق الحسابية الأولية: {score}%. {tag}.\n"
                    "هذه ليست موافقة فنية أو تأكيد مخزون أو سعر سوق. يلزم التواصل والتحقق من حداثة البيانات، "
                    "العينة، التحليل المعملي، التراخيص، النقل وشروط التسليم."
                )
            elif facility_hits:
                answer = "وجدت سجلات منشآت قد ترتبط بسؤالك، لكنها لا تثبت وجود عرض مخلفات أو طلب شراء حالي.\n" + "\n".join(
                    f"- {f.get('name')} — {f.get('sector')} — {f.get('city')} — المصدر: {f.get('source_name') or f.get('data_origin')} — التحقق: {'نعم' if f.get('is_verified') else 'غير متحقق'}"
                    for f in facility_hits
                ) + "\nتحقق من النشاط الحالي ونطاق الترخيص قبل التواصل أو التعاقد."
            else:
                answer = f"لا أجد عرضاً وطلباً متوافقين في السجلات الحالية لفئة {matched_cat or 'المادة المطلوبة'}. دليل المنشآت العام ليس بديلاً عن عرض/طلب منشور من المصنع. أضف بيانات مؤكدة أو وسّع البحث بالمحافظة والمواصفة."

        elif any(w in low for w in ["كربون", "co2", "بيئي", "esg", "انبعاث"]):
            answer = (
                "🌿 لا توجد في هذه النسخة صفقات مكتملة موثقة يمكن احتساب انبعاثات متجنبة فعلية لها. "
                "تحتوي إعدادات بعض الفئات على معاملات استرشادية فقط؛ لا تُعامل كمعاملات دورة حياة معتمدة أو شهادة كربون. "
                "للتقدير نحتاج كمية معاد تدويرها فعلياً، المادة والدرجة، وسيناريو المادة البِكر المستبدلة، "
                "الطاقة والنقل والفواقد وحدود النظام، ثم توثيق المنهجية ومراجعتها."
            )

        elif any(w in low for w in ["استفاد", "استفيد", "أستفيد", "استفادة", "أستخدم", "استخدم", "تحويل", "تدوير", "تصنيع", "طريقة", "upcycle", "upcycling", "إعادة استخدام", "معدات", "معالجة"]):
            docs = retrieve(msg, limit=5)
            if docs:
                answer = "♻️ المسارات المرجعية المتاحة في كتالوج REGENESIS:\n\n" + "\n\n".join(
                    f"**{doc.get('title')}**\n{doc.get('text')}"
                    for doc in docs[:4]
                ) + "\n\nهذه مسارات عامة محتملة وليست مواصفة قبول لمصنع بعينه. يجب اختبار الخامة والعينة ومراجعة اشتراطات السلامة واللوائح قبل اعتماد المسار."
            else:
                answer = "حدد نوع الخام أو كوده (مثل PET، HDPE، PP، ألومنيوم، نشارة خشب، قصاصات قطن، زجاج) لأسترجع شروط الفرز والفحوص ومسارات التدوير المتاحة في الكتالوج."

        elif matched_cat:
            rows = relevant_listings[:6]
            docs = retrieve(msg, limit=4)
            summary = "\n".join(
                f"- {r.get('title')} — {r.get('factory')} / {r.get('city')} — {r.get('qty')} {r.get('unit','طن')} — {r.get('tradeType')} — {r.get('price')} {r.get('currency','EGP')}/{r.get('unit','طن')} — المصدر: {r.get('data_origin')}"
                for r in rows
            ) or "لا توجد إعلانات لهذه الفئة حالياً."
            knowledge = "\n\n".join(f"{d.get('title')}: {d.get('text')}" for d in docs[:3])
            answer = f"بيانات فئة {matched_cat} في المنصة:\n{summary}\n\nملاحظات فنية من قاعدة المعرفة:\n{knowledge}\n\nتحقق من المصدر والسعر وحداثة الإعلان؛ سجلات العرض التجريبية ليست عروضاً حقيقية."

        else:
            demo_listings = sum(1 for row in active_listings if row.get("data_origin") == "demo_synthetic")
            public_facilities = sum(1 for row in (factory_records or []) if row.get("data_origin") == "public_directory")
            answer = (
                f"أهلاً بك في REGENESIS AI. قاعدة العرض الحالية تحتوي على {len(active_listings)} سجلاً للسوق، "
                f"منها {demo_listings} سيناريوهات توضيحية، ودليلها يضم {public_facilities} سجلاً عاماً للمنشآت غير المتحققة.\n\n"
                "أستطيع شرح خصائص المواد، الفحوص المعملية، مسارات إعادة التدوير وUpcycling، البحث داخل الإعلانات، "
                "واستخراج فرص توافق أولية. الصور والأسعار والسيناريوهات التجريبية موضحة بوضوح داخل المنصة ولا تمثل صفقات حقيقية."
            )

        if web_results:
            answer += "\n\n**مصادر بحث الويب:**\n" + "\n".join(f"- [{r['title']}]({r['url']}) — {r['snippet'][:240]}" for r in web_results)
        return {
            "answer": answer,
            "records_considered": len(relevant_listings),
            "mode": "database-grounded-rules",
            "suggested_actions": suggested_actions,
            "sources": web_results
        }
