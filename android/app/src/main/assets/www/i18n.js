/* Yo'l Guard i18n: ru / uz / en. Loaded after app.js (deferred).
   Static texts: selector map. Dynamic: T(key). Language in localStorage yg_lang. */
const I18N = {
ru: {
tabs: ["SOS", "Случай", "Гараж", "Панель"],
home_kicker: "Экспресс-помощь", home_h1: "Попали в ДТП?<br/>Действуйте спокойно.",
home_sub: "Сфотографируйте — ИИ разберёт, сотрудник подтвердит.", sos: "Я попал в ДТП",
stats: ["код сессии", "статус", "фото"], how: "Как это работает",
steps: ["Отвечаете на 6 вопросов — 30 секунд", "Фотографируете — ИИ анализирует сам",
"Получаете схему и ответ", "Сотрудник пишет вам решение"],
join_h: "Второй участник? Подключитесь по коду",
join_hint: "Первый водитель видит код сессии на главном экране после нажатия «Я попал в ДТП».",
join_id_ph: "ID случая", join_code_ph: "Код сессии", join_btn: "Подключиться как сторона B",
checks: ["Есть пострадавшие", "Участвует пешеход", "Один водитель признал вину",
"Страховка и документы у обоих в порядке", "Оба трезвы", "Согласны по списку повреждений"],
f_inj: "Сколько пострадавших (0 — нет)", f_impact: "По какой части пришёлся удар",
f_comment: "Комментарий (необязательно)", comment_ph: "Напр.: выехал с второстепенной…",
triage_btn: "Проверить", triage_init: "Пока не проверено",
ev_hint_new: "Добавьте 6 фото по списку", ev_hint_full: "Комплект полный", ev_left: "Осталось: ",
ev_queue: "В очереди на отправку: ", camera: "Сфотографировать",
kinds: ["Общий план места", "Оба авто в кадре", "Номер авто A", "Номер авто B", "Разметка и знаки", "Повреждение крупно"],
demo_btn: "Демо-метка (без фото)", video_btn: "🎥 Видео места", rec_btn: "🎙 Голосовая заметка",
rec_stop: "⏹ Остановить запись", w3_fine: "Черновик. Факт подтверждаете вы и специалист.",
diagram_btn: "Собрать черновик схемы", confirm_btn: "Я подтверждаю схему", retry_btn: "Повторить анализ",
ai_loading: "ИИ анализирует фото...", ai_down: "ИИ недоступен, попробуйте позже",
ai_src: "ИИ", ai_cas: "Пострадавшие:", ai_plates: "Номера с фото:", ai_sev: "Тяжесть ущерба:",
w4_h1: "Ответ сотрудника", w4_empty: "Пока тихо. Ответ появится здесь.",
ack: "Понял, жду", help: "Нужна помощь!", w4_h2: "Пакет для страховой",
claim_hint: "Пакет собирает сотрудник (роль specialist).", spec_login: "Войти специалистом",
claim_btn: "Пакет для страховой", prev: "Назад", next: "Далее",
g_kicker: "Мой автомобиль", g_h: "Гараж", plate_ph: "Госномер · 01A777AA",
make_ph: "Марка", model_ph: "Модель", vehicle_btn: "Сохранить авто",
api_h: "Сервер API", api_btn: "Сохранить адрес", login_h: "Вход",
phone_ph: "+99890…", pw_ph: "Пароль", login_btn: "Войти",
push_h: "Уведомления", push_hint: "Push о вердикте и сообщениях вместо опроса. Нужны HTTPS или localhost.",
push_btn: "Включить уведомления", lang_h: "Язык / Til / Language",
a_kicker: "Сотрудник", a_h: "Панель контроля",
a_hint: "Красные случаи (пострадавшие / ГАИ) — вверху. Нажмите на случай для досье.",
a_reload: "Обновить список", search_ph: "Поиск: код/ID",
prev_pg: "← Назад", next_pg: "Далее →",
t_no_inc: "Сначала нажмите «Я попал в ДТП» на главном экране",
t_login_ok: "Вход выполнен", t_login_err: "Ошибка входа: ",
t_case_err: "Не удалось создать случай: ", t_join_need: "Введите ID случая и код сессии",
t_join_err: "Не удалось подключиться: ", t_joined: "Вы подключены как сторона B",
t_triage_err: "Проверка не удалась: ", t_red: "Красный сценарий: следуйте официальному процессу (102).",
t_evl_err: "Не удалось: ", t_dia_err: "Схема не собралась: ",
t_confirmed: "Подтверждено. Второй водитель подтверждает со своего телефона.",
t_conf_err: "Ошибка: ", t_uploading: "Загружаем фото…", t_saved: "Фото сохранено",
t_upl_err: "Ошибка загрузки: ", t_offline_q: "Нет связи — фото в очереди, отправим автоматически",
t_msg_q: "Нет связи — сообщение в очереди", t_q_sent: "Очередь отправлена",
t_dark_blur: "Фото тёмное и размытое — лучше переснять, но отправляем",
t_dark: "Фото тёмное — лучше переснять, но отправляем",
t_blur: "Фото размытое — лучше переснять, но отправляем",
t_dupe: "Похожее фото уже загружено", t_big_video: "Видео больше 50 МБ",
t_video_up: "Загружаем видео…", t_video_ok: "Видео сохранено",
t_voice_up: "Отправляем голосовую…", t_voice_ok: "Голосовая сохранена",
t_voice_short: "Запись слишком короткая", t_no_mic: "Нет доступа к микрофону",
t_claim_forbid: "Пакет собирает сотрудник. Войдите специалистом во вкладке Гараж.",
t_claim_err: "Пакет не собран: ", t_spec_ok: "Вы вошли как специалист. Жмите «Пакет для страховой».",
t_spec_err: "Ошибка: ", t_no_access: "Нет доступа: войдите специалистом во вкладке Гараж.",
t_net_err: "Ошибка сети. Проверьте, запущен ли backend, и повторите.",
t_empty_list: "Случаев пока нет", t_dossier_loading: "Загрузка досье…",
t_dossier_err: "Не удалось загрузить досье. Повторите.",
t_empty_msg: "Пустое сообщение", t_send_err: "Не отправлено: ",
t_no_review: "Ревью-кейс не создан (случай green без замечаний).",
t_need_comment: "Для отклонения нужен комментарий", t_verdict: "Вердикт: ",
t_no_vehicle: "Не сохранено: ", t_push_ok: "Уведомления включены",
t_push_err: "Не удалось подписаться: ", t_push_server: "Push не настроен на сервере",
t_push_no: "Push недоступен здесь (нужны HTTPS/localhost)",
t_push_browser: "Разрешите уведомления в браузере", t_login_first: "Сначала войдите во вкладке Гараж",
st_total: "ДТП всего", st_pending: "на проверке", st_users: "пользователи",
st_photos: "фото", st_red: "красные",
shown: "Показано {a}–{b} из {t}",
d_driver: "Данные водителя", d_no_inj: "пострадавших нет", d_inj: "пострадавших: ",
d_hit: "удар: ", d_comment: "Комментарий:", d_parts: "Участники:",
d_photos: "Фото водителя", d_no_photo: "нет фото", d_ai: "Схема ИИ",
d_draft_warn: "⚠️ Разбор ИИ — черновик, не юридический факт.",
d_todo: "Что делать:", d_casual: "Пострадавшие (из triage, ИИ не выдумывает):",
d_no_ai: "ИИ-анализ ещё не запускался", d_verdict: "Вердикт:", d_chat: "Переписка",
d_empty_chat: "пусто", d_msg_ph: "Текст пользователю...", d_send: "Отправить",
d_comment_ph: "Комментарий к вердикту (обязателен для отклонения)...",
d_btn_ok: "✅ Регистрация завершена", d_btn_field: "🚓 Выезжаем для проверки",
d_btn_reject: "Отклонить", d_from_panel: "из панели",
t_vid_chip: "Видео", t_voice_chip: "Голосовая ✓",
t_offline: "Нет связи с сервером", t_online: "Сервер на связи",
w_steps: ["Проверка eligibility", "Фотофиксация", "Ответ ИИ", "Ответ сотрудника"],
fl_ped: "пешеход", fl_fault: "вина", fl_docs: "доки", fl_sober: "трезв", fl_agree: "согласие",
d_inj_badge: "ПОСТРАДАВШИЕ",
severities: {light: "лёгкие", medium: "средние", heavy: "тяжёлые", unknown: "не определена"}
},
uz: {
tabs: ["SOS", "Holat", "Garaj", "Panel"],
home_kicker: "Tezkor yordam", home_h1: "YTHga uchradingizmi?<br/>Vahimasiz harakat qiling.",
home_sub: "Suratga oling — AI tahlil qiladi, xodim tasdiqlaydi.", sos: "Men YTHga uchradim",
stats: ["sessiya kodi", "holat", "foto"], how: "Qanday ishlaydi",
steps: ["6 ta savolga javob — 30 soniya", "Suratga oling — AI o‘zi tahlil qiladi",
"Chizma va javobni oling", "Xodim sizga qarorni yozadi"],
join_h: "Ikkinchi ishtirokchimisiz? Kod bilan ulaning",
join_hint: "Birinchi haydovchi «Men YTHga uchradim» tugmasidan keyin sessiya kodini ko‘radi.",
join_id_ph: "Holat ID", join_code_ph: "Sessiya kodi", join_btn: "B tomon sifatida ulanish",
checks: ["Jabrlanganlar bor", "Piyoda ishtirok etmoqda", "Bir haydovchi aybni tan oldi",
"Ikkalasida sug‘urta/hujjat joyida", "Ikkalasi hushyor", "Shikast ro‘yxati bo‘yicha kelishilgan"],
f_inj: "Jabrlanganlar soni (0 — yo‘q)", f_impact: "Zarba qaysi qismga tekkan",
f_comment: "Izoh (ixtiyoriy)", comment_ph: "Mas.: ikkinchi darajali yo‘ldan chiqdim…",
triage_btn: "Tekshirish", triage_init: "Hali tekshirilmagan",
ev_hint_new: "Ro‘yxat bo‘yicha 6 ta foto qo‘shing", ev_hint_full: "To‘plam tayyor", ev_left: "Qoldi: ",
ev_queue: "Yuborish navbatida: ", camera: "Suratga olish",
kinds: ["Umumiy plan", "Ikkala avto", "A raqami", "B raqami", "Belgi/chiziq", "Shikast"],
demo_btn: "Demo-belgi (fotosiz)", video_btn: "🎥 Joy videosi", rec_btn: "🎙 Ovozli izoh",
rec_stop: "⏹ Yozuvni to‘xtatish", w3_fine: "Qoralama. Faktni siz va mutaxassis tasdiqlaydi.",
diagram_btn: "Chizma qoralamasini yig‘ish", confirm_btn: "Sxemani tasdiqlayman", retry_btn: "Tahlilni takrorlash",
ai_loading: "AI fotolarni tahlil qilmoqda...", ai_down: "AI mavjud emas, keyinroq urinib ko‘ring",
ai_src: "AI", ai_cas: "Jabrlanganlar:", ai_plates: "Fotodagi raqamlar:", ai_sev: "Shikast og‘irligi:",
w4_h1: "Xodim javobi", w4_empty: "Hozircha tinch. Javob shu yerda chiqadi.",
ack: "Tushundim, kutyapman", help: "Yordam kerak!", w4_h2: "Sug‘urta paketi",
claim_hint: "Paketni xodim yig‘adi (specialist roli).", spec_login: "Mutaxassis sifatida kirish",
claim_btn: "Sug‘urta paketi", prev: "Orqaga", next: "Keyingi",
g_kicker: "Mening avtomobilim", g_h: "Garaj", plate_ph: "Davlat raqami · 01A777AA",
make_ph: "Marka", model_ph: "Model", vehicle_btn: "Avtoni saqlash",
api_h: "API server", api_btn: "Manzilni saqlash", login_h: "Kirish",
phone_ph: "+99890…", pw_ph: "Parol", login_btn: "Kirish",
push_h: "Bildirishnomalar", push_hint: "Hukm va xabarlar haqida push. HTTPS yoki localhost kerak.",
push_btn: "Bildirishnomalarni yoqish", lang_h: "Язык / Til / Language",
a_kicker: "Xodim", a_h: "Nazorat paneli",
a_hint: "Qizil holatlar (jabrlanganlar / GAI) — tepada. Dosye uchun bosing.",
a_reload: "Ro‘yxatni yangilash", search_ph: "Qidiruv: kod/ID",
prev_pg: "← Orqaga", next_pg: "Keyingi →",
t_no_inc: "Avval bosh ekranda «Men YTHga uchradim» ni bosing",
t_login_ok: "Kirish bajarildi", t_login_err: "Kirish xatosi: ",
t_case_err: "Holat yaratilmadi: ", t_join_need: "Holat ID va sessiya kodini kiriting",
t_join_err: "Ulanib bo‘lmadi: ", t_joined: "B tomon sifatida ulandingiz",
t_triage_err: "Tekshiruv o‘tmadi: ", t_red: "Qizil ssenariy: rasmiy jarayonga amal qiling (102).",
t_evl_err: "Bo‘lmadi: ", t_dia_err: "Chizma yig‘ilmadi: ",
t_confirmed: "Tasdiqlandi. Ikkinchi haydovchi o‘z telefonidan tasdiqlaydi.",
t_conf_err: "Xato: ", t_uploading: "Foto yuklanmoqda…", t_saved: "Foto saqlandi",
t_upl_err: "Yuklash xatosi: ", t_offline_q: "Aloqa yo‘q — foto navbatda, avtomatik yuboramiz",
t_msg_q: "Aloqa yo‘q — xabar navbatda", t_q_sent: "Navbat yuborildi",
t_dark_blur: "Foto qorong‘u va xira — qayta olish yaxshiroq, lekin yuboramiz",
t_dark: "Foto qorong‘u — qayta olish yaxshiroq, lekin yuboramiz",
t_blur: "Foto xira — qayta olish yaxshiroq, lekin yuboramiz",
t_dupe: "O‘xshash foto allaqachon yuklangan", t_big_video: "Video 50 MB dan katta",
t_video_up: "Video yuklanmoqda…", t_video_ok: "Video saqlandi",
t_voice_up: "Ovozli yuborilmoqda…", t_voice_ok: "Ovozli saqlandi",
t_voice_short: "Yozuv juda qisqa", t_no_mic: "Mikrofonga ruxsat yo‘q",
t_claim_forbid: "Paketni xodim yig‘adi. Garajda mutaxassis bo‘lib kiring.",
t_claim_err: "Paket yig‘ilmadi: ", t_spec_ok: "Mutaxassis sifatida kirdingiz. «Sug‘urta paketi» ni bosing.",
t_spec_err: "Xato: ", t_no_access: "Ruxsat yo‘q: Garajda mutaxassis bo‘lib kiring.",
t_net_err: "Tarmoq xatosi. Backend ishlayotganini tekshirib, qaytaring.",
t_empty_list: "Hozircha holatlar yo‘q", t_dossier_loading: "Dosye yuklanmoqda…",
t_dossier_err: "Dosyeni yuklab bo‘lmadi. Qaytaring.",
t_empty_msg: "Bo‘sh xabar", t_send_err: "Yuborilmadi: ",
t_no_review: "Review-keys yaratilmagan (izohsiz green holat).",
t_need_comment: "Rad etish uchun izoh kerak", t_verdict: "Hukm: ",
t_no_vehicle: "Saqlanmadi: ", t_push_ok: "Bildirishnomalar yoqildi",
t_push_err: "Obuna bo‘lmadi: ", t_push_server: "Serverda push sozlanmagan",
t_push_no: "Push bu yerda ishlamaydi (HTTPS/localhost kerak)",
t_push_browser: "Brauzerda bildirishnomalarga ruxsat bering", t_login_first: "Avval Garajda kiring",
st_total: "Jami YTH", st_pending: "tekshiruvda", st_users: "foydalanuvchilar",
st_photos: "fotolar", st_red: "qizil",
shown: "Ko‘rsatilgan {a}–{b} / jami {t}",
d_driver: "Haydovchi ma’lumoti", d_no_inj: "jabrlanganlar yo‘q", d_inj: "jabrlanganlar: ",
d_hit: "zarba: ", d_comment: "Izoh:", d_parts: "Ishtirokchilar:",
d_photos: "Haydovchi fotolari", d_no_photo: "foto yo‘q", d_ai: "AI chizmasi",
d_draft_warn: "⚠️ AI tahlili — qoralama, yuridik fakt emas.",
d_todo: "Nima qilish kerak:", d_casual: "Jabrlanganlar (triage dan, AI to‘qimaydi):",
d_no_ai: "AI tahlil hali ishga tushmagan", d_verdict: "Hukm:", d_chat: "Yozishmalar",
d_empty_chat: "bo‘sh", d_msg_ph: "Foydalanuvchiga matn...", d_send: "Yuborish",
d_comment_ph: "Hukmga izoh (rad etishda shart)...",
d_btn_ok: "✅ Ro‘yxatdan o‘tish yakunlandi", d_btn_field: "🚓 Tekshirishga chiqamiz",
d_btn_reject: "Rad etish", d_from_panel: "paneldan",
t_vid_chip: "Video", t_voice_chip: "Ovozli ✓",
t_offline: "Aloqa yo‘q", t_online: "Server aloqada",
w_steps: ["Eligibility tekshiruvi", "Fotofiksatsiya", "AI javobi", "Xodim javobi"],
fl_ped: "piyoda", fl_fault: "ayb", fl_docs: "hujjat", fl_sober: "hushyor", fl_agree: "kelishuv",
d_inj_badge: "JABRLANGANLAR",
severities: {light: "yengil", medium: "o‘rtacha", heavy: "og‘ir", unknown: "aniqlanmagan"}
},
en: {
tabs: ["SOS", "Case", "Garage", "Panel"],
home_kicker: "Express help", home_h1: "Had an accident?<br/>Stay calm.",
home_sub: "Take photos — AI analyses, staff confirms.", sos: "I had an accident",
stats: ["session code", "status", "photos"], how: "How it works",
steps: ["Answer 6 questions — 30 seconds", "Take photos — AI analyses automatically",
"Get the diagram and answer", "Staff writes you the decision"],
join_h: "Second party? Join by code",
join_hint: "The first driver sees the session code on the home screen after tapping “I had an accident”.",
join_id_ph: "Case ID", join_code_ph: "Session code", join_btn: "Join as side B",
checks: ["There are injured people", "A pedestrian is involved", "One driver admitted fault",
"Insurance and documents OK for both", "Both sober", "Agree on the damage list"],
f_inj: "Injured count (0 — none)", f_impact: "Which part was hit",
f_comment: "Comment (optional)", comment_ph: "E.g.: came from a side road…",
triage_btn: "Check", triage_init: "Not checked yet",
ev_hint_new: "Add 6 photos from the list", ev_hint_full: "Set complete", ev_left: "Left: ",
ev_queue: "Queued to send: ", camera: "Take a photo",
kinds: ["Scene overview", "Both cars", "Plate A", "Plate B", "Markings", "Damage close-up"],
demo_btn: "Demo mark (no photo)", video_btn: "🎥 Scene video", rec_btn: "🎙 Voice note",
rec_stop: "⏹ Stop recording", w3_fine: "Draft. You and the specialist confirm the facts.",
diagram_btn: "Build draft diagram", confirm_btn: "I confirm the diagram", retry_btn: "Retry analysis",
ai_loading: "AI is analysing the photos...", ai_down: "AI unavailable, try again later",
ai_src: "AI", ai_cas: "Casualties:", ai_plates: "Plates from photos:", ai_sev: "Damage severity:",
w4_h1: "Staff answer", w4_empty: "Quiet for now. The answer will appear here.",
ack: "Understood, waiting", help: "Need help!", w4_h2: "Insurance package",
claim_hint: "The package is built by staff (specialist role).", spec_login: "Log in as specialist",
claim_btn: "Insurance package", prev: "Back", next: "Next",
g_kicker: "My car", g_h: "Garage", plate_ph: "Plate · 01A777AA",
make_ph: "Make", model_ph: "Model", vehicle_btn: "Save car",
api_h: "API server", api_btn: "Save address", login_h: "Login",
phone_ph: "+99890…", pw_ph: "Password", login_btn: "Log in",
push_h: "Notifications", push_hint: "Push about verdicts and messages instead of polling. Needs HTTPS or localhost.",
push_btn: "Enable notifications", lang_h: "Язык / Til / Language",
a_kicker: "Staff", a_h: "Control panel",
a_hint: "Red cases (injured / police) on top. Tap a case for the dossier.",
a_reload: "Reload list", search_ph: "Search: code/ID",
prev_pg: "← Back", next_pg: "Next →",
t_no_inc: "First tap “I had an accident” on the home screen",
t_login_ok: "Logged in", t_login_err: "Login error: ",
t_case_err: "Could not create case: ", t_join_need: "Enter case ID and session code",
t_join_err: "Could not join: ", t_joined: "Joined as side B",
t_triage_err: "Check failed: ", t_red: "Red scenario: follow the official process (102).",
t_evl_err: "Failed: ", t_dia_err: "Diagram failed: ",
t_confirmed: "Confirmed. The second driver confirms from their phone.",
t_conf_err: "Error: ", t_uploading: "Uploading photo…", t_saved: "Photo saved",
t_upl_err: "Upload error: ", t_offline_q: "Offline — photo queued, will send automatically",
t_msg_q: "Offline — message queued", t_q_sent: "Queue sent",
t_dark_blur: "Photo is dark and blurry — retake recommended, sending anyway",
t_dark: "Photo is dark — retake recommended, sending anyway",
t_blur: "Photo is blurry — retake recommended, sending anyway",
t_dupe: "A similar photo is already uploaded", t_big_video: "Video over 50 MB",
t_video_up: "Uploading video…", t_video_ok: "Video saved",
t_voice_up: "Sending voice note…", t_voice_ok: "Voice note saved",
t_voice_short: "Recording too short", t_no_mic: "No microphone access",
t_claim_forbid: "Staff builds the package. Log in as specialist in Garage.",
t_claim_err: "Package failed: ", t_spec_ok: "Logged in as specialist. Tap “Insurance package”.",
t_spec_err: "Error: ", t_no_access: "No access: log in as specialist in Garage.",
t_net_err: "Network error. Check the backend is running and retry.",
t_empty_list: "No cases yet", t_dossier_loading: "Loading dossier…",
t_dossier_err: "Could not load dossier. Retry.",
t_empty_msg: "Empty message", t_send_err: "Not sent: ",
t_no_review: "No review case (green case without notes).",
t_need_comment: "A comment is required to reject", t_verdict: "Verdict: ",
t_no_vehicle: "Not saved: ", t_push_ok: "Notifications enabled",
t_push_err: "Subscribe failed: ", t_push_server: "Push is not configured on the server",
t_push_no: "Push unavailable here (needs HTTPS/localhost)",
t_push_browser: "Allow notifications in the browser", t_login_first: "Log in via Garage first",
st_total: "Total accidents", st_pending: "pending review", st_users: "users",
st_photos: "photos", st_red: "red",
shown: "Showing {a}–{b} of {t}",
d_driver: "Driver data", d_no_inj: "no injured", d_inj: "injured: ",
d_hit: "impact: ", d_comment: "Comment:", d_parts: "Participants:",
d_photos: "Driver photos", d_no_photo: "no photos", d_ai: "AI diagram",
d_draft_warn: "⚠️ AI analysis is a draft, not a legal fact.",
d_todo: "What to do:", d_casual: "Casualties (from triage, AI doesn't invent):",
d_no_ai: "AI analysis not run yet", d_verdict: "Verdict:", d_chat: "Chat",
d_empty_chat: "empty", d_msg_ph: "Text to user...", d_send: "Send",
d_comment_ph: "Verdict comment (required to reject)...",
d_btn_ok: "✅ Registration complete", d_btn_field: "🚓 On our way to check",
d_btn_reject: "Reject", d_from_panel: "from panel",
t_vid_chip: "Video", t_voice_chip: "Voice ✓",
t_offline: "Offline", t_online: "Server online",
w_steps: ["Eligibility check", "Photo fixation", "AI answer", "Staff answer"],
fl_ped: "pedestrian", fl_fault: "fault", fl_docs: "docs", fl_sober: "sober", fl_agree: "agreement",
d_inj_badge: "INJURED",
severities: {light: "light", medium: "moderate", heavy: "severe", unknown: "unknown"}
}
};
let LANG = localStorage.getItem("yg_lang") || "ru";
if (!I18N[LANG]) LANG = "ru";
function T(k) { const d = I18N[LANG] || I18N.ru; return (k in d) ? d[k] : (I18N.ru[k] || k); }
function applyLang(l) {
  LANG = I18N[l] ? l : "ru";
  try { localStorage.setItem("yg_lang", LANG); } catch {}
  const d = I18N[LANG];
  const set = (sel, v) => { const el = document.querySelector(sel); if (el) el.innerHTML = v; };
  const ph = (sel, v) => { const el = document.querySelector(sel); if (el) el.placeholder = v; };
  document.querySelectorAll(".tab").forEach((b) => {
    const i = { "scr-home": 0, "scr-case": 1, "scr-garage": 2, "scr-admin": 3 }[b.dataset.s];
    if (i !== undefined) b.textContent = d.tabs[i];
  });
  set("#scr-home .kicker", d.home_kicker); set("#scr-home h1", d.home_h1);
  set("#scr-home .sub", d.home_sub); set("#btnSos", d.sos);
  document.querySelectorAll("#scr-home .stat span").forEach((el, i) => { if (d.stats[i]) el.textContent = d.stats[i]; });
  set("#scr-home .card h3", d.how);
  document.querySelectorAll("#scr-home .steps li").forEach((el, i) => { if (d.steps[i]) el.textContent = d.steps[i]; });
  const jc = document.querySelectorAll("#scr-home .card")[1];
  if (jc) {
    const h = jc.querySelector("h3"); if (h) h.textContent = d.join_h;
    const p = jc.querySelector(".hint"); if (p) p.textContent = d.join_hint;
  }
  ph("#joinId", d.join_id_ph); ph("#joinCode", d.join_code_ph); set("#btnJoin", d.join_btn);
  document.querySelectorAll("label.check span").forEach((el, i) => { if (d.checks[i]) el.textContent = d.checks[i]; });
  const fines = document.querySelectorAll("#w1 .fine");
  if (fines[0]) fines[0].textContent = d.f_inj;
  if (fines[1]) fines[1].textContent = d.f_impact;
  if (fines[2]) fines[2].textContent = d.f_comment;
  ph("#cComment", d.comment_ph); set("#btnTriage", d.triage_btn);
  set("#triageOut", d.triage_init); set("#evHint", d.ev_hint_new);
  set("label.camera[for='camInput']", d.camera); set("#btnEv", d.demo_btn);
  set("label.camera[for='vidInput']", d.video_btn); set("#btnRec", d.rec_btn);
  set("#w3 .fine", d.w3_fine); set("#btnDiagram", d.diagram_btn);
  set("#btnConfirm", d.confirm_btn); set("#aiRetry", d.retry_btn);
  const w4h = document.querySelectorAll("#w4 h3");
  if (w4h[0]) w4h[0].textContent = d.w4_h1;
  if (w4h[1]) w4h[1].textContent = d.w4_h2;
  set("#btnAck", d.ack); set("#btnHelp", d.help);
  const w4hint = document.querySelector("#w4 .hint"); if (w4hint) w4hint.textContent = d.claim_hint;
  set("#btnSpecLogin", d.spec_login); set("#btnClaim", d.claim_btn);
  set("#wPrev", d.prev); set("#wNext", d.next);
  set("#scr-garage .kicker", d.g_kicker); set("#scr-garage h2", d.g_h);
  ph("#gPlate", d.plate_ph); ph("#gMake", d.make_ph); ph("#gModel", d.model_ph);
  set("#btnVehicle", d.vehicle_btn); set("#btnApi", d.api_btn);
  ph("#gPhone", d.phone_ph); ph("#gPw", d.pw_ph); set("#btnLogin", d.login_btn);
  set("#btnPush", d.push_btn);
  const gh = document.querySelectorAll("#scr-garage .card h3");
  const want = [null, d.api_h, d.login_h, d.push_h, d.lang_h];
  gh.forEach((el, i) => { if (want[i + 1]) el.textContent = want[i + 1]; });
  const phint = document.querySelector("#scr-garage .card .hint");
  if (phint) phint.textContent = d.push_hint;
  set("#scr-admin .kicker", d.a_kicker); set("#scr-admin h2", d.a_h);
  set("#scr-admin .hint", d.a_hint); set("#btnAdminReload", d.a_reload);
  ph("#fltSearch", d.search_ph); set("#adminPrev", d.prev_pg); set("#adminNext", d.next_pg);
  // evidence kind options
  const ek = document.getElementById("evKind");
  if (ek) [...ek.options].forEach((o, i) => { if (d.kinds[i]) o.textContent = d.kinds[i]; });
  document.querySelectorAll(".langBtn").forEach((b) =>
    b.classList.toggle("activeLang", b.dataset.lang === LANG));
  document.documentElement.lang = LANG === "uz" ? "uz" : LANG;
  if (typeof paint === "function") paint();
  if (typeof pushState === "function") pushState();
}
document.querySelectorAll(".langBtn").forEach((b) =>
  b.addEventListener("click", () => applyLang(b.dataset.lang)));
applyLang(LANG);
