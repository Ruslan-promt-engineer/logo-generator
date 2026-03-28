# logo_generator.py
import os
import time
import requests
import logging
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

API_KEY = os.getenv('YANDEX_API_KEY')
FOLDER_ID = os.getenv('FOLDER_ID')

# Валидация конфигурации при импорте
if not API_KEY or API_KEY == 'YOUR_API_KEY_HERE':
    logger.warning("⚠️ YANDEX_API_KEY не настроен!")
if not FOLDER_ID:
    logger.warning("⚠️ FOLDER_ID не настроен!")


def generate_logo(prompt: str, seed: int = None, timeout_seconds: int = 180) -> dict:
    """
    Универсальная функция генерации логотипа через Yandex Art API.
    Работает как в Flask, так и в Telegram-боте.

    Returns:
        dict: {'success': True, 'image': base64_str, 'seed': int} или {'error': '...'}
    """
    if not API_KEY or not FOLDER_ID:
        return {'error': 'Серверная ошибка: API не настроен'}

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Api-Key {API_KEY}"
    }

    if seed is None:
        seed = int(time.time())

    payload = {
        "modelUri": f"art://{FOLDER_ID}/yandex-art/latest",
        "generationOptions": {
            "seed": seed,
            "aspectRatio": {"widthRatio": "1", "heightRatio": "1"}
        },
        "messages": [{"weight": "1", "text": prompt}]
    }

    try:
        # Создаём операцию
        create_resp = requests.post(
            'https://llm.api.cloud.yandex.net/foundationModels/v1/imageGenerationAsync',
            headers=headers, json=payload, timeout=30
        )

        if create_resp.status_code != 200:
            logger.error(f"Ошибка создания: {create_resp.text}")
            return {'error': f'Ошибка API: {create_resp.status_code}'}

        operation_id = create_resp.json().get('id')
        if not operation_id:
            return {'error': 'Не получен ID операции'}

        # Polling с экспоненциальной задержкой
        attempt = 0
        start_time = time.time()

        while attempt < 60 and (time.time() - start_time) < timeout_seconds:
            time.sleep(min(2 ** attempt, 10))  # 2, 4, 8, 10, 10... сек

            status_resp = requests.get(
                f'https://llm.api.cloud.yandex.net/operations/{operation_id}',
                headers=headers, timeout=30
            )

            if status_resp.status_code != 200:
                continue  # Пробуем ещё раз при сетевых сбоях

            result = status_resp.json()

            if result.get('done'):
                if 'error' in result:
                    return {'error': f"Генерация: {result['error']}"}

                image = result.get('response', {}).get('image')
                if image:
                    return {'success': True, 'image': image, 'seed': seed}
                return {'error': 'Изображение не найдено в ответе'}

            attempt += 1

        return {'error': 'Превышено время ожидания генерации'}

    except requests.exceptions.Timeout:
        return {'error': 'Таймаут запроса к API'}
    except Exception as e:
        logger.exception(f"Неожиданная ошибка: {e}")
        return {'error': f'Внутренняя ошибка: {str(e)}'}