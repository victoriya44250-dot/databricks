# Lab 12 — EU Agricultural Risk Knowledge Assistant

Навчальний RAG-проєкт у Databricks Free Edition. Асистент шукає уривки офіційного звіту World Bank про управління аграрними ризиками в ЄС і формує відповіді з номерами PDF-сторінок. Це вузька база знань одного документа, а не універсальний консультант з агрономії.

## Підтверджений стан

| Етап | Фактичний результат |
|---|---|
| Unity Catalog | `workspace.viktoriia_kalenichenko_lab12`, managed volume `raw_docs` |
| Ingestion | 147 сторінок у `document_pages`, повторне читання з Delta: 147 |
| Підготовка | 144 непорожні сторінки без двох титульних |
| Chunking | 550 фрагментів у `document_chunks` |
| Embeddings | Databricks-managed, `databricks-qwen3-embedding-0-6b`, 1024 виміри |
| AI Search | `document_chunks_index`: Online, 550 проіндексованих рядків |
| Retrieval | top-5 ANN з фільтром сторінок успішно повернув уривки про Італію |
| LLM | `databricks-gpt-oss-120b` повернула `READY` у перевірці `ai_query` |
| QA, evaluation, logging | Реалізовано в `05_rag_complete.ipynb`; результати запуску ще треба додати |
| AI Dev Kit / MCP | Встановлено; через MCP підтверджено 147 сторінок і 550 фрагментів; деталі в `AI_DEV_KIT_EVIDENCE.md` |
| Локальні тести | 7 перевірок допоміжних функцій пройшли; це не інтеграційна перевірка Databricks |
| CI/CD | Конфігурація підготовлена; факт deployment підтверджується лише успішним workflow run |

Стан наведено за отриманими виводами та скриншотами, а не за припущенням, що весь код уже запущено.

## Джерело і межі даних

World Bank, *Solutions for Better Agri-Risk Management in the European Union*, March 2026.
[Офіційний PDF](https://documents1.worldbank.org/curated/en/099032326044016306/pdf/P510294-1b00a8b1-c76f-419d-953a-46bd5805c044.pdf).

Файл: `P510294-1b00a8b1-c76f-419d-953a-46bd5805c044.pdf`.
Шлях: `/Volumes/workspace/viktoriia_kalenichenko_lab12/raw_docs/`.
World Bank Ukraine виключено. FAO/IPCC не входять до поточного індексу. IPCC був виключений після досягнення parser token limit на одній сторінці; цей збій не маскувався пропуском сторінок.

Один PDF є document-based dataset: після ingestion це набір сторінок з текстом і метаданими. Завдання не встановлює мінімальної кількості документів. Корпус достатній для навчального процесу RAG, але не доводить якість для всіх аграрних питань. PDF не включено до Git; зберігається офіційне посилання і provenance.

## Обробка і параметри

`PDF → document_pages → очищення → document_chunks → AI Search → top-k evidence → LLM → rag_runs`.

- `pypdf==7.1.1` витягає текст кожної сторінки. Метадані: ім'я і шлях файла, SHA-256, номер PDF-сторінки та кількість символів.
- Сторінка 147 порожня; 1 і 2 — титульні. Raw-таблиця зберігає всі 147 сторінок. Для поділу використано 144.
- Нормалізовано CRLF, пробіли, NUL, надлишкові порожні рядки; прибрано окремий номер на початку сторінки. Переноси рядків збережено.
- Переноси слів на межі рядків не з'єднувалися автоматично: не кожен дефіс є переносом. Це відоме обмеження. Таблиці можуть втрачати структуру колонок; числові відповіді необхідно звіряти з PDF.
- `RecursiveCharacterTextSplitter`: 1200 **символів**, overlap 200, separators `\n\n`, `\n`, пробіл, порожній рядок. Поділ виконується окремо для кожної сторінки; фрагмент не перетинає її межу. 200 — цільовий overlap, фактичний може бути меншим. Речення та слова з переносами іноді розриваються.
- Chunk ID — SHA-256 від SHA-256 файла, сторінки, профілю, порядкового номера та тексту фрагмента. Профіль: `recursive_chars_1200_overlap_200_v1`.
- Колонки chunks: `chunk_id`, `chunk_profile`, `file_name`, `source_sha256`, `page_number`, `chunk_index`, `chunk_text`, `char_count`.
- Індекс: Delta Sync, Standard endpoint `lab12_agri_search`, primary key `chunk_id`, embedding column `chunk_text`, Triggered sync. CDF увімкнений. Окрема embedding writeback table не створюється; вектори зберігає індекс.
- Пошук: ANN, top-k=5. Незалежний від запитання фільтр виключає титульні/порожню сторінки, сторінки 3–6 і 96–97, помічені як службові матеріали/бібліографія. Це ручний фільтр конкретного документа, не універсальна класифікація. Він може відкинути корисні посилання; решта сторінок не гарантовано позбавлені шуму.

## Запуск QA

1. Імпортувати `notebooks/05_rag_complete.ipynb` у Databricks Workspace.
2. Обрати Serverless; виконати комірки згори вниз. Встановлення SDK і restart включені.
3. Перевірити дві demo-відповіді: із retrieval і без нього. Вхідні уривки друкуються для звірки.
4. У віджеті `run_evaluation` встановити `true`, виконати evaluation-комірку і наступну monitoring-комірку. Це 8 запитань × 2 режими = до 16 LLM-викликів плюс два demo-виклики. Bundle job передає цей параметр автоматично.
5. Зберегти notebook з результатами. Заповнити `evaluation_review.csv` за фактичними відповідями.

Notebook самодостатній. Він не перезаписує `document_pages`, `document_chunks` чи індекс. `rag_runs` доповнюється новими рядками. Повторний запуск створює нові вимірювання, тому для аналізу використовується `session_id`. Версія SDK записується в журнал; dependency поки не pinned, після успішного запуску її варто зафіксувати.

## Оцінювання

Вісім development cases у `evaluation_cases.json`: 6 запитань із перевіреними опорними сторінками, 2 без відповіді в документі. Очікувані відповіді не передаються моделі. Однакові модель і запитання використовуються з retrieval та без нього. Це невелика ручна перевірка, не незалежний benchmark.

Автоматично збираються: latency, помилки, наявність очікуваної сторінки у top-5 і коректність номерів цитованих сторінок. `citation_format_ok` перевіряє формат і входження сторінки до контексту; **не перевіряє, чи твердження дійсно випливає з цитати**. Expected-page hit теж не гарантує, що потрібний уривок сторінки знайдено. Для baseline ці retrieval-метрики не застосовуються.

Для кожної пари відповідей вручну оцінити:

- relevance: 0 — не відповідає; 1 — частково; 2 — відповідає питанню;
- completeness: 0 — ключових фактів немає; 1 — частково; 2 — основні факти наявні;
- unsupported claims: є/немає/невідомо після звірки з джерелом;
- missing context: чи був потрібний факт серед отриманих уривків;
- out-of-scope: чи відмовилася модель вигадувати відповідь.

Не оголошуємо перемогу RAG заздалегідь. Перші retrieval-проби показали шум від змісту й бібліографії; фільтр поліпшив конкретний запит про Італію. Порівняльні висновки додаються після виконання оцінювання.

## Логування, доступ і вартість

`rag_runs` містить prompt, response, question, режим, IDs і сторінки evidence, модель, SDK version, час і статус. Prompt включає використані уривки, що дозволяє перевірити відповідь. Вхідні запити в цій лабораторній мають стосуватися публічного звіту: не вводити приватні дані, бо вони потраплять до журналу.

Доступ контролює Unity Catalog: потрібні USE CATALOG, USE SCHEMA, SELECT для даних/індексу, а для створення журналу CREATE TABLE і для дописування MODIFY. Для raw volume — READ VOLUME; WRITE VOLUME лише тому, хто завантажує дані. Перегляд реальних grants додано в останню комірку, широкі права автоматично не надаються. Фактичні успадковані права потрібно перевірити, а не вважати відсутніми через порожній екран Permissions.

Notebook використовує авторизацію поточної сесії. Токени не записуються у код чи Git. Для CI потрібен окремо налаштований доступ до правильного workspace. Triggered sync і невеликий top-k обмежують зайві обчислення; Free Edition має квоти. При зміні chunks необхідна синхронізація індексу. Якщо пауза перевищує строк зберігання Delta-змін, може знадобитися відновлення синхронізації.

## Part B: агент, AI Dev Kit та CI/CD

Агент підготував QA notebook, перевірки, Bundle, workflow і документацію. Це саме по собі **не означає**, що MCP і CI/CD вже виконані.

У поточному upstream [AI Dev Kit](https://github.com/databricks-solutions/ai-dev-kit) навички встановлюються через Databricks AI Tools, а MCP server має окремий installer. На Windows використовується `install.ps1`, еквівалент Linux `install.sh`. Для відтворюваності потрібно зберегти commit встановленого kit і фактичний результат інсталяції.

`databricks.yml` додає два Serverless jobs: `rag_smoke` перевіряє 550 унікальних непорожніх chunks та роботу фільтрованого retrieval; `rag_qa` запускає відповіді, порівняння і журналювання. Наявні UC-об'єкти й індекс є prerequisites, Bundle не створює їх повторно. Повна відтворюваність ingestion потребує експорту вже виконаних notebooks 01–04 з workspace.

Для локальної перевірки:

```powershell
python -m unittest discover -s tests -v
python build_notebook.py
databricks bundle validate --strict -t dev -p lab12_free
databricks bundle plan -t dev -p lab12_free
```

Після перегляду плану:

```powershell
databricks bundle deploy -t dev -p lab12_free
databricks bundle run -t dev -p lab12_free rag_smoke
databricks bundle run -t dev -p lab12_free rag_qa
```

Для репозиторію Week 8 папка цього проєкту має бути `lab12-rag/`, а файл `.github/workflows/lab12.yml` треба розмістити у **корені репозиторію**, не всередині папки лабораторної. PR запускає тести. Merge у main або ручний запуск запускає validation, deployment і smoke test. Секрети `LAB12_DATABRICKS_HOST` та `LAB12_DATABRICKS_TOKEN` відокремлені від Azure PROD Week 8; потрібне environment `lab12-dev`. Якщо токени недоступні у workspace, спочатку налаштувати підтримувану workload identity/OAuth-авторизацію і відповідно змінити workflow; локальний browser-login не є CI credentials. Не використовувати старі PROD credentials для нового Free workspace.

CI/CD у цій версії є підготовленою конфігурацією, доки не додано посилання на успішний run. Локальний deploy не є доказом GitHub CI/CD. PR review і перевірка плану потрібні перед merge. Локальний `RUN_PART_B.ps1 -Deploy -RunQA` поєднує ці кроки; при перенесенні проєкту передати `-KitPath` зі шляхом до встановленого AI Dev Kit.

## Критичний висновок

Агент прискорив підготовку коду й документації. Людина визначала релевантність джерела, відхилила Ukraine-звіт, перевірила витягнутий текст і обсяг корпусу, спостерігала стан індексу та має оцінити відповіді. Найважливіші ручні рішення: scope, права, витрати, перевірка чисел і доречність цитат.

RAG дає моделі доступ до конкретного звіту й дозволяє перевіряти джерело; prompting alone покладається на знання моделі. RAG не усуває галюцинації, якщо пошук приніс нерелевантний або неповний контекст. Менші chunks точніші для пошуку, але можуть втрачати зв'язки; більші зберігають більше контексту, але додають шум і tokens. 1200/200 — стартова конфігурація; оптимальність без порівняльного експерименту не заявляється.

## Документація

- [Databricks AI Search queries](https://docs.databricks.com/aws/en/ai-search/query-ai-search)
- [ai_query](https://docs.databricks.com/aws/en/sql/language-manual/functions/ai_query)
- [Bundle examples](https://docs.databricks.com/aws/en/dev-tools/bundles/examples)
- [AI Dev Kit MCP setup](https://github.com/databricks-solutions/ai-dev-kit/tree/main/databricks-mcp-server)
