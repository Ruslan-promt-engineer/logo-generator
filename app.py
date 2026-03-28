# app.py
from flask import Flask, render_template, request, jsonify
import os
import base64
from dotenv import load_dotenv

# ✅ Импорт общей функции генерации
from logo_generator import generate_logo

load_dotenv()

app = Flask(__name__)

# 🔐 Валидация конфигурации при старте
if not os.getenv('YANDEX_API_KEY') or os.getenv('YANDEX_API_KEY') == 'YOUR_API_KEY_HERE':
    raise RuntimeError("❌ Ошибка: YANDEX_API_KEY не установлен в переменных окружения")

if not os.getenv('FOLDER_ID'):
    raise RuntimeError("❌ Ошибка: FOLDER_ID не установлен в переменных окружения")

# 🎨 Заготовленные стили для логотипов
PRESET_STYLES = {
    'minimalist': 'минималистичный логотип, чистый дизайн, простые геометрические формы',
    'modern': 'современный логотип, яркие цвета, динамичный дизайн',
    'geometric': 'геометрический логотип, четкие линии, абстрактные формы',
    'vintage': 'винтажный логотип, ретро стиль, классические элементы',
    'tech': 'технологичный логотип, футуристичный стиль, цифровой дизайн',
    'corporate': 'корпоративный логотип, профессиональный вид, строгий стиль',
    'creative': 'креативный логотип, художественный стиль, яркие цвета',
    'elegant': 'элегантный логотип, изысканный дизайн, утонченные формы'
}


@app.route('/')
def index():
    """Главная страница"""
    return render_template('index.html', styles=PRESET_STYLES)


@app.route('/generate', methods=['POST'])
def generate():
    """Обработка запроса на генерацию логотипа"""
    data = request.json

    company_name = data.get('company_name', '').strip()
    custom_prompt = data.get('custom_prompt', '').strip()
    style = data.get('style', '')

    # 🔍 Валидация входных данных
    if not company_name:
        return jsonify({'error': 'Введите название фирмы'}), 400

    if len(company_name) > 100:
        return jsonify({'error': 'Название компании слишком длинное'}), 400

    # Экранирование спецсимволов для безопасности промпта
    company_name = company_name.replace('"', '\\"').replace("'", "\\'")

    # 🧩 Формируем финальный промпт
    base_prompt = f'Создай логотип для компании "{company_name}".'

    if style and style in PRESET_STYLES:
        base_prompt += f' {PRESET_STYLES[style]}.'

    if custom_prompt:
        # Ограничиваем длину пользовательского промпта
        custom_prompt = custom_prompt[:500]
        base_prompt += f' {custom_prompt}.'

    base_prompt += ' Логотип должен быть на прозрачном или белом фоне, профессиональный вид.'

    # 🚀 Вызов общей функции генерации
    result = generate_logo(base_prompt)

    if 'error' in result:
        app.logger.error(f"Ошибка генерации: {result['error']}")
        return jsonify({'error': result['error']}), 500

    return jsonify({
        'success': True,
        'image': result['image'],
        'prompt': base_prompt,
        'seed': result['seed']
    })


@app.route('/refine', methods=['POST'])
def refine():
    """Доработка существующего логотипа с сохранением базовой структуры"""
    data = request.json

    original_prompt = data.get('original_prompt', '').strip()
    refinement = data.get('refinement', '').strip()
    original_seed = data.get('seed')

    # 🔍 Валидация
    if not original_prompt or not refinement:
        return jsonify({'error': 'Необходимы оригинальный промпт и дополнение'}), 400

    if len(refinement) > 300:
        return jsonify({'error': 'Описание доработки слишком длинное'}), 400

    # 🧩 Объединяем промпты
    new_prompt = f'{original_prompt} Дополнительно: {refinement}'

    # 🚀 Вызов общей функции с тем же seed для сохранения структуры
    result = generate_logo(new_prompt, seed=original_seed)

    if 'error' in result:
        app.logger.error(f"Ошибка доработки: {result['error']}")
        return jsonify({'error': result['error']}), 500

    return jsonify({
        'success': True,
        'image': result['image'],
        'prompt': new_prompt,
        'seed': result['seed']
    })


# 🔧 Health check endpoint для мониторинга
@app.route('/health')
def health():
    return jsonify({'status': 'ok', 'service': 'logo-generator-api'}), 200


if __name__ == '__main__':
    # 📝 Настройка логирования
    import logging

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('app.log', encoding='utf-8'),
            logging.StreamHandler()
        ]
    )

    app.logger.info("🚀 Flask-приложение запущено")

    # ⚙️ Запуск сервера
    # Для продакшена используйте gunicorn: gunicorn -w 4 -b 0.0.0.0:5000 app:app
    app.run(debug=True, host='0.0.0.0', port=5000)