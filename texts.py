TEXTS = {
    "uz": {
        "start": (
            "👋 Salom, <b>{name}</b>!\n\n"
            "🧠 <b>QuizMasterUz</b> botiga xush kelibsiz!\n\n"
            "📄 .docx fayl yuboring va quiz boshlang!"
        ),
        "no_sub": (
            "🔒 Bot bilan foydalanish uchun obuna kerak.\n"
            "Narxi: <b>1$</b>\n\n"
            "Murojaat: @Mr_Baxadir"
        ),
        "choose_lang": "🌐 Tilni tanlang / Выберите язык:",
        "lang_set": "✅ O'zbek tili tanlandi!",
        "send_file": "📄 .docx fayl yuboring:",
        "file_error": "❌ Faylni o'qishda xato. Format to'g'riligini tekshiring.",
        "no_questions": "❌ Faylda savollar topilmadi. Formatni tekshiring.",
        "quiz_found": "✅ <b>{title}</b>\n📝 Savollar: <b>{count}</b>\n\nQuiz rejimini tanlang:",
        "mode_seq": "📖 Ketma-ket",
        "mode_shuffle_q": "🔀 Savollar aralash",
        "mode_shuffle_a": "🔀 Variantlar aralash",
        "mode_shuffle_all": "🔀 Hammasi aralash",
        "question": "❓ <b>Savol {num}/{total}</b>\n\n{question}",
        "correct": "✅ To'g'ri!",
        "wrong": "❌ Noto'g'ri! To'g'ri javob: <b>{answer}</b>",
        "result": (
            "🏁 <b>Quiz yakunlandi!</b>\n\n"
            "📊 Natija: <b>{score}/{total}</b>\n"
            "📈 Foiz: <b>{percent}%</b>\n"
            "🏆 Baho: {grade}"
        ),
        "grade_5": "🥇 A'lo (5)",
        "grade_4": "🥈 Yaxshi (4)",
        "grade_3": "🥉 Qoniqarli (3)",
        "grade_2": "❌ Qoniqarsiz (2)",
        "next": "➡️ Keyingi",
        "finish_early": "🏁 Yakunlash",
        "main_menu": "🏠 Bosh menyu",
        "my_quizzes": "📋 Mening quizlarim",
        "new_quiz": "➕ Yangi quiz",
        "help": (
            "📌 <b>Fayl formati:</b>\n\n"
            "<code># QUIZ: Quiz nomi\n\n"
            "Q1: Savol matni\n"
            "A) Variant 1\n"
            "B) Variant 2\n"
            "C) Variant 3\n"
            "D) Variant 4\n"
            "ANSWER: B\n\n"
            "Q2: ...</code>"
        ),
        "no_quizzes": "📭 Hozircha quizlar yo'q.",
        "bot_off": "🔒 Bot hozircha ishlamaydi. Tez orada ochiladi!",
        "status_active": "✅ Obunangiz faol!",
        "status_inactive": "❌ Obunangiz faol emas.",
    },
    "ru": {
        "start": (
            "👋 Привет, <b>{name}</b>!\n\n"
            "🧠 Добро пожаловать в <b>QuizMasterUz</b>!\n\n"
            "📄 Отправьте .docx файл и начните квиз!"
        ),
        "no_sub": (
            "🔒 Для использования бота нужна подписка.\n"
            "Цена: <b>1$</b>\n\n"
            "Написать: @Mr_Baxadir"
        ),
        "choose_lang": "🌐 Tilni tanlang / Выберите язык:",
        "lang_set": "✅ Русский язык выбран!",
        "send_file": "📄 Отправьте .docx файл:",
        "file_error": "❌ Ошибка чтения файла. Проверьте формат.",
        "no_questions": "❌ Вопросы не найдены. Проверьте формат.",
        "quiz_found": "✅ <b>{title}</b>\n📝 Вопросов: <b>{count}</b>\n\nВыберите режим квиза:",
        "mode_seq": "📖 По порядку",
        "mode_shuffle_q": "🔀 Перемешать вопросы",
        "mode_shuffle_a": "🔀 Перемешать варианты",
        "mode_shuffle_all": "🔀 Всё перемешать",
        "question": "❓ <b>Вопрос {num}/{total}</b>\n\n{question}",
        "correct": "✅ Правильно!",
        "wrong": "❌ Неправильно! Правильный ответ: <b>{answer}</b>",
        "result": (
            "🏁 <b>Квиз завершён!</b>\n\n"
            "📊 Результат: <b>{score}/{total}</b>\n"
            "📈 Процент: <b>{percent}%</b>\n"
            "🏆 Оценка: {grade}"
        ),
        "grade_5": "🥇 Отлично (5)",
        "grade_4": "🥈 Хорошо (4)",
        "grade_3": "🥉 Удовлетворительно (3)",
        "grade_2": "❌ Неудовлетворительно (2)",
        "next": "➡️ Далее",
        "finish_early": "🏁 Завершить",
        "main_menu": "🏠 Главное меню",
        "my_quizzes": "📋 Мои квизы",
        "new_quiz": "➕ Новый квиз",
        "help": (
            "📌 <b>Формат файла:</b>\n\n"
            "<code># QUIZ: Название квиза\n\n"
            "Q1: Текст вопроса\n"
            "A) Вариант 1\n"
            "B) Вариант 2\n"
            "C) Вариант 3\n"
            "D) Вариант 4\n"
            "ANSWER: B\n\n"
            "Q2: ...</code>"
        ),
        "no_quizzes": "📭 Квизов пока нет.",
        "bot_off": "🔒 Бот временно недоступен. Скоро откроется!",
        "status_active": "✅ Ваша подписка активна!",
        "status_inactive": "❌ Ваша подписка не активна.",
    }
}


def t(lang: str, key: str, **kwargs) -> str:
    lang = lang if lang in TEXTS else "uz"
    text = TEXTS[lang].get(key, key)
    if kwargs:
        text = text.format(**kwargs)
    return text


def get_grade(percent: float, lang: str) -> str:
    if percent >= 86:
        return t(lang, "grade_5")
    elif percent >= 71:
        return t(lang, "grade_4")
    elif percent >= 56:
        return t(lang, "grade_3")
    else:
        return t(lang, "grade_2")
