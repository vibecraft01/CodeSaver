# CodeSaver

CodeSaver أداة متعددة المنصات تعمل من سطر الأوامر لإنشاء لقطات ZIP مؤرخة لمشاريع البرمجة. تستخدم مكتبة Python القياسية فقط، وتنفذ الحفظ التلقائي في الخلفية، وتكتشف لغة النظام.

## البدء السريع

```bash
python -m venv .venv
python -m pip install -e .
codesaver
```

إنشاء نسخة احتياطية واحدة من دون فتح القائمة:

```bash
codesaver --project-dir ./my-project --backup-dir ./backups --backup-now
```

استعادة أرشيف:

```bash
codesaver --project-dir ./my-project --restore ./backups/my-project_2026-01-20_14-30-00.zip --overwrite
```

الفاصل الزمني الافتراضي للحفظ التلقائي هو 600 ثانية. استخدم `--no-autosave` لتعطيله، و`--interval 300` لتغييره، و`--language de` لتحديد اللغة يدوياً. يتم استثناء `.git` و`__pycache__` والبيئات الافتراضية وذاكرة التخزين المؤقت للأدوات افتراضياً.

راجع [README الرئيسي](../README.md) للاطلاع على الوثائق الكاملة. الترخيص MIT.

