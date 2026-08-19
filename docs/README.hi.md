# CodeSaver

CodeSaver एक क्रॉस-प्लेटफ़ॉर्म CLI टूल है जो कोड प्रोजेक्ट के टाइमस्टैम्प वाले ZIP स्नैपशॉट बनाता है। यह केवल Python की standard library का उपयोग करता है, बैकग्राउंड में ऑटोसेव चलाता है और सिस्टम की भाषा पहचानता है।

## त्वरित शुरुआत

```bash
python -m venv .venv
python -m pip install -e .
codesaver
```

मेनू के बिना एक बैकअप बनाएँ:

```bash
codesaver --project-dir ./my-project --backup-dir ./backups --backup-now
```

आर्काइव पुनर्स्थापित करें:

```bash
codesaver --project-dir ./my-project --restore ./backups/my-project_2026-01-20_14-30-00.zip --overwrite
```

डिफ़ॉल्ट ऑटोसेव अंतराल 600 सेकंड है। `--no-autosave` से इसे बंद करें, `--interval 300` से बदलें और `--language de` से भाषा चुनें। `.git`, `__pycache__`, वर्चुअल एनवायरनमेंट और टूल कैश डिफ़ॉल्ट रूप से बाहर रखे जाते हैं।

पूरी जानकारी के लिए [मुख्य README](../README.md) देखें। लाइसेंस MIT है।

