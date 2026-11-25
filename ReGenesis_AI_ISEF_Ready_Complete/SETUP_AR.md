# إعداد وتشغيل REGENESIS AI

## 1) تشغيل محلي

راجع خطوات Windows الكاملة في `README_AR.md`. استخدم Python 3.12 كخيار متوافق، وفعّل البيئة الافتراضية قبل تثبيت المكتبات.

## 2) Ollama

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\setup_ollama_windows.ps1
ollama list
```

الموديلات: `qwen3:4b` للمحادثة و`qwen2.5vl:3b` لتحليل الصور. الاستدلال محلي، لكن تنزيل الموديلات يحتاج إنترنت.

## 3) البحث على الإنترنت

في `.env`:

```dotenv
WEB_SEARCH_ENABLED=true
WEB_SEARCH_PROVIDER=tavily
TAVILY_API_KEY=ضع_مفتاحك_هنا
```

أو استخدم `WEB_SEARCH_PROVIDER=brave` مع `BRAVE_SEARCH_API_KEY`. لا ترفع `.env` إلى Git.

## 4) سجلات المصانع

استخدم قالب `datasets/factories_template.csv` ومصدر بيانات مسموحاً بترخيصه. شغّل أداة الاستيراد أولاً بوضع `--dry-run`. جميع السجلات المستوردة غير متحققة حتى يراجعها مسؤول النظام.

## 5) النشر العام

استخدم PostgreSQL وHTTPS وتخزيناً دائماً للملفات ونسخاً احتياطية ومراقبة. إذا استضفت Ollama، أبقِ API داخل شبكة الخادم ولا تعرضه للإنترنت العام.
