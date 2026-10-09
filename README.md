# Yo'l Guard — AI Accident Resolution (MVP)

## 1. Что это
Смартфон-ассистент при мелком ДТП: регистрация → фото/видео/голосовые → авто-анализ ИИ (Gemini: текст + номера + тяжесть + схема) → ответ сотрудника в приложение. Метрика: время до освобождения полосы.

**Флоу:** сфоткал → ИИ анализирует сам (с прогрессом и повтором) → видишь схему-дорогу, разбор, номера, тяжесть → сотрудник в EXE-панели жмёт «🚓 Выезжаем» или «✅ Зарегистрировано» → текст приходит тебе в шаг 4. Твои кнопки «Понял, жду» / «Нужна помощь» уходят сотруднику. Подтверждения второго водителя НЕ требуется — хватает подтверждения создателя.

**Готовое:** `android/app/build/outputs/apk/debug/app-debug.apk` (WebView, синхронизирован с `frontend/`), `admin/dist/YolGuardAdmin.exe` (панель сотрудника: досье, фото, ИИ, 2 кнопки + пакет + перезапуск ИИ), `frontend/` (PWA: офлайн-очередь, ru/uz/en, диктофон, проверка качества фото).
**Проверено:** pytest 45/45, debug-APK собирается, EXE пересобирается, `node --check` чист, живой разбор Gemini по фото проверен (отвечает ~15–30 сек).

## 2. Архитектура (modular monolith)
`FastAPI /api/v1` + `routers/{auth,incidents,misc,admin,push}`, `services/{rules,ai,images,push}`, SQLAlchemy + опциональный MongoDB. APK = WebView-обёртка над `frontend/`. EXE = tkinter-клиент. Сотрудник работает ТОЛЬКО в EXE (в web/mobile staff-UI нет).

```
Backend / API  →  SQL (users, incidents, evidence-мета, claim, review) + MongoDB (история ИИ, события)
               →  File Storage (uploads/: фото/видео MP4/аудио, только по JWT)
```

## 3. Данные
**SQL (источник истины):** users/roles (driver|specialist|admin|insurer), vehicles (plate unique), incidents (code, status, triage, eligibility), participants (A|B + авто), evidence (kind, sha256, mime, size, gps), diagrams, claim_packages, review_cases, ai_analyses (последний итог), messages, push_subscriptions.
**MongoDB (MONGODB_URI пуст = выключена, всё работает):** каждый запуск ИИ целиком, audit-события, CV-мета файлов. Чтение: `GET /incidents/{id}/ai-history`.

## 4. Запуск
```powershell
cd C:\Users\WnlyPC\Downloads\yolguard\backend
.\.venv\Scripts\python -m pytest -q        # 45 тестов
.\.venv\Scripts\python -m uvicorn app.main:app --port 8002
```
- Веб: `http://127.0.0.1:8002/app/` (НЕ двойным кликом по index.html — будет CORS). API по умолчанию `http://127.0.0.1:8002/api/v1`
- Демо-вход: водитель `+998900000011` / `driver123`; сотрудник `+998900000002` / `spec1234`; админ `+998900000001` / `admin123`
- Токен живёт 30 мин, дальше приложение само обновляет сессию (refresh 7 дней). Протух совсем — войди заново.
- APK: в приложении (Гараж → Сервер API) указать `http://IP-ПК:8002/api/v1`, один Wi-Fi с ПК.
- EXE: запустить `admin/dist/YolGuardAdmin.exe`, войти специалистом → «Обновить список» (поиск: код или госномер).
- Сборка APK: `cd android` + `..\android-sdk\gradle-8.10\bin\gradle :app:assembleDebug --no-daemon` (JDK 21 из `android/.jdk`, путь в `gradle.properties`).
- Сборка EXE: `cd admin` + `..\backend\.venv\Scripts\python -m PyInstaller YolGuardAdmin.spec --noconfirm` (старый EXE перед этим закрыть!).
- Окружение: `backend/.venv` (создать: `py -m venv .venv` + `pip install -r requirements.txt`). Важно: requirements пинит `SQLAlchemy==2.0.54` — колёса 2.1.x не грузятся на этой Windows-машине.

## 5. API /api/v1 (главное)
- POST /auth/register, /auth/login → {user,access,refresh}; POST /auth/refresh {"token"} → {access}
- POST /incidents → {id,code} (авто водителя привязывается само); POST /incidents/{id}/join?code=
- POST /incidents/{id}/triage → {eligibility green|yellow|red, reason} (red = случай у сотрудника, жди письма)
- POST /incidents/{id}/evidence-upload (kind+file: JPEG/PNG/WEBP ≤10МБ, MP4/WEBM ≤50МБ, аудио ≤10МБ) → {evidence_id, url, ai{source,description,plates,damage_severity,svg}}
- GET /incidents/{iid}/evidence/{eid}/file (Bearer или ?token=) | GET /incidents/{id}/ai-history
- POST /incidents/{id}/diagram, /confirm (создатель), /claim-package (specialist, нужно подтверждение создателя), GET .../claim-package (чтение: участники+specialist+insurer)
- GET/POST /incidents/{id}/messages; GET /insurer/incidents (insurer read-only)
- GET /reviews/queue, POST /reviews/{id} {approved|needs_field|rejected} (только из pending; reject с комментарием)
- GET /admin/stats, GET /admin/incidents?skip&limit&status&eligibility&search= (код/госномер), GET /admin/incidents/{id}, POST /admin/incidents/{id}/message
- GET /push/vapid-key, POST /push/subscribe|unsubscribe (Web Push; без VAPID-ключей — polling)
- GET /health

## 6. Security
PBKDF2 200k + JWT typ access/refresh + RBAC (admin bypass), allow-list видов файлов по magic bytes, kind allow-list (anti-traversal), XSS-санитайзер SVG/меток, CORS allow-list (без `*`), SECRET_KEY fail-fast ≥32, rate-limit /auth//join/upload (429), фото только участникам+staff, claim только specialist, insurer только чтение. Секреты только в `backend/.env` (git-ignored). Тесты глушат живой Gemini и чистят за собой dev-БД.

## 7. Структура
```
yolguard/backend/app/{main,config,db,mongo,models,schemas,security,routers/{auth,incidents,misc,admin,push},services/{rules,ai,images,push}}.py
yolguard/backend/{seed.py,requirements.txt,.env.example,tests/, .venv/}
yolguard/frontend/{index.html,app.js,i18n.js,sw.js,ui.js,styles.css,manifest.json,icons/}
yolguard/android/app/src/main/{java/.../MainActivity.java,assets/www (=копия frontend/),res/xml/file_paths.xml}
yolguard/admin/{admin_app.py,YolGuardAdmin.spec,dist/YolGuardAdmin.exe(git-ignored)}
yolguard/postman/*.json  yolguard/*.docx  yolguard/*.pptx
```
