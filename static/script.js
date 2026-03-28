// Элементы DOM
const generateBtn = document.getElementById('generateBtn');
const refineBtn = document.getElementById('refineBtn');
const newLogoBtn = document.getElementById('newLogoBtn');
const downloadBtn = document.getElementById('downloadBtn');
const shareBtn = document.getElementById('shareBtn');
const companyName = document.getElementById('companyName');
const styleSelect = document.getElementById('styleSelect');
const customPrompt = document.getElementById('customPrompt');
const refinementPrompt = document.getElementById('refinementPrompt');
const generatorSection = document.getElementById('generatorSection');
const resultSection = document.getElementById('resultSection');
const resultImage = document.getElementById('resultImage');
const usedPrompt = document.getElementById('usedPrompt');
const errorMessage = document.getElementById('errorMessage');
const successMessage = document.getElementById('successMessage');

let currentPrompt = '';
let currentSeed = null;
let currentImageBase64 = '';  // Сохраняем base64 изображения

// Показать ошибку
function showError(message) {
    errorMessage.textContent = message;
    errorMessage.style.display = 'block';
    setTimeout(() => {
        errorMessage.style.display = 'none';
    }, 5000);
}

// Показать успешное сообщение
function showSuccess(message) {
    successMessage.textContent = message;
    successMessage.style.display = 'block';
    setTimeout(() => {
        successMessage.style.display = 'none';
    }, 3000);
}

// Показать загрузку
function setLoading(button, isLoading) {
    const btnText = button.querySelector('.btn-text');
    const loader = button.querySelector('.loader');

    if (isLoading) {
        btnText.style.display = 'none';
        loader.style.display = 'block';
        button.disabled = true;
    } else {
        btnText.style.display = 'inline';
        loader.style.display = 'none';
        button.disabled = false;
    }
}

// Скачать изображение
async function downloadImage() {
    if (!currentImageBase64) {
        showError('Изображение ещё не сгенерировано');
        return;
    }

    try {
        // Создаём blob из base64
        const response = await fetch(`data:image/png;base64,${currentImageBase64}`);
        const blob = await response.blob();

        // Создаём ссылку для скачивания
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `logo_${Date.now()}.png`;
        document.body.appendChild(a);
        a.click();

        // Очищаем
        window.URL.revokeObjectURL(url);
        document.body.removeChild(a);

        showSuccess('✅ Логотип скачан!');
    } catch (error) {
        console.error('Ошибка скачивания:', error);
        showError('Не удалось скачать изображение');
    }
}

// Поделиться изображением
async function shareImage() {
    if (!currentImageBase64) {
        showError('Изображение ещё не сгенерировано');
        return;
    }

    try {
        // Пробуем использовать Web Share API (работает в мобильных браузерах)
        if (navigator.share) {
            // Конвертируем base64 в blob
            const response = await fetch(`data:image/png;base64,${currentImageBase64}`);
            const blob = await response.blob();
            const file = new File([blob], 'logo.png', { type: 'image/png' });

            await navigator.share({
                title: 'Мой логотип',
                text: `Логотип для компании, созданный с помощью ИИ`,
                files: [file]
            });

            showSuccess('✅ Изображение отправлено!');
        } else {
            // Fallback: копируем в буфер обмена (если поддерживается)
            if (navigator.clipboard && window.ClipboardItem) {
                const response = await fetch(`data:image/png;base64,${currentImageBase64}`);
                const blob = await response.blob();

                await navigator.clipboard.write([
                    new ClipboardItem({
                        'image/png': blob
                    })
                ]);

                showSuccess('✅ Изображение скопировано в буфер обмена!');
            } else {
                // Последний fallback: просто скачиваем
                showSuccess('📥 Ваш браузер не поддерживает partage. Скачиваем изображение...');
                await downloadImage();
            }
        }
    } catch (error) {
        if (error.name !== 'AbortError') {
            console.error('Ошибка шаринга:', error);
            // Пробуем скачать как fallback
            await downloadImage();
        }
    }
}

// Генерация логотипа
generateBtn.addEventListener('click', async () => {
    const name = companyName.value.trim();

    if (!name) {
        showError('Пожалуйста, введите название компании');
        return;
    }

    setLoading(generateBtn, true);
    errorMessage.style.display = 'none';

    try {
        const response = await fetch('/generate', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                company_name: name,
                style: styleSelect.value,
                custom_prompt: customPrompt.value
            })
        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.error || 'Ошибка генерации');
        }

        // Показываем результат
        currentPrompt = data.prompt;
        currentSeed = data.seed;
        currentImageBase64 = data.image;  // Сохраняем base64
        resultImage.src = `data:image/png;base64,${data.image}`;
        usedPrompt.textContent = data.prompt;

        generatorSection.style.display = 'none';
        resultSection.style.display = 'block';

        // Активируем кнопки
        if (downloadBtn) downloadBtn.style.display = 'flex';
        if (shareBtn) shareBtn.style.display = 'flex';

        // Плавная прокрутка к результату
        resultSection.scrollIntoView({ behavior: 'smooth', block: 'start' });

    } catch (error) {
        showError(error.message);
    } finally {
        setLoading(generateBtn, false);
    }
});

// Доработка логотипа
refineBtn.addEventListener('click', async () => {
    const refinement = refinementPrompt.value.trim();

    if (!refinement) {
        showError('Пожалуйста, опишите что нужно изменить');
        return;
    }

    setLoading(refineBtn, true);
    errorMessage.style.display = 'none';

    try {
        const response = await fetch('/refine', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                original_prompt: currentPrompt,
                refinement: refinement,
                seed: currentSeed
            })
        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.error || 'Ошибка доработки');
        }

        // Обновляем результат
        currentPrompt = data.prompt;
        currentSeed = data.seed;
        currentImageBase64 = data.image;  // Обновляем base64
        resultImage.src = `data:image/png;base64,${data.image}`;
        usedPrompt.textContent = data.prompt;
        refinementPrompt.value = '';

        showSuccess('✅ Логотип обновлён!');

        // Плавная прокрутка к изображению
        resultImage.scrollIntoView({ behavior: 'smooth', block: 'center' });

    } catch (error) {
        showError(error.message);
    } finally {
        setLoading(refineBtn, false);
    }
});

// Создать новый логотип
newLogoBtn.addEventListener('click', () => {
    resultSection.style.display = 'none';
    generatorSection.style.display = 'block';
    refinementPrompt.value = '';
    currentPrompt = '';
    currentSeed = null;
    currentImageBase64 = '';

    // Скрываем кнопки действий
    if (downloadBtn) downloadBtn.style.display = 'none';
    if (shareBtn) shareBtn.style.display = 'none';

    // Плавная прокрутка наверх
    window.scrollTo({ top: 0, behavior: 'smooth' });
});

// Обработчики кнопок скачать и поделиться
if (downloadBtn) {
    downloadBtn.addEventListener('click', downloadImage);
}

if (shareBtn) {
    shareBtn.addEventListener('click', shareImage);
}

// Enter для отправки (Ctrl+Enter в textarea)
companyName.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') {
        generateBtn.click();
    }
});

customPrompt.addEventListener('keypress', (e) => {
    if (e.key === 'Enter' && e.ctrlKey) {
        generateBtn.click();
    }
});

refinementPrompt.addEventListener('keypress', (e) => {
    if (e.key === 'Enter' && e.ctrlKey) {
        refineBtn.click();
    }
});

// Инициализация при загрузке страницы
document.addEventListener('DOMContentLoaded', () => {
    // Скрываем кнопки действий изначально
    if (downloadBtn) downloadBtn.style.display = 'none';
    if (shareBtn) shareBtn.style.display = 'none';

    console.log('🎨 Генератор логотипов готов к работе!');
});