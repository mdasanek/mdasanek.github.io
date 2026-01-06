#!/usr/bin/env python3
"""
Генерирует статичную версию сайта с встроенной галереей
"""
import json
import html
import re

def load_gallery():
    """Загружает данные галереи из gallery.json"""
    try:
        with open('gallery.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        return []

def generate_gallery_html(gallery_items):
    """Генерирует HTML для галереи"""
    html_parts = []
    
    for item in gallery_items:
        src = html.escape(item.get('src', ''))
        caption = item.get('caption', '').strip()
        is_video = item.get('type') == 'video' or any(src.lower().endswith(f'.{ext}') for ext in ['mp4', 'webm'])
        
        if caption:
            caption_escaped = html.escape(caption)
            if is_video:
                html_parts.append(f'''        <div class="block">
            <video src="{src}" autoplay loop muted playsinline style="width:100%;height:auto;"></video>
            <p>{caption_escaped}</p>
        </div>''')
            else:
                html_parts.append(f'''        <div class="block">
            <img src="{src}" alt="{caption_escaped}">
            <p>{caption_escaped}</p>
        </div>''')
        else:
            if is_video:
                html_parts.append(f'        <video src="{src}" autoplay loop muted playsinline style="width:100%;height:auto;"></video>')
            else:
                html_parts.append(f'        <img src="{src}" alt="">')
    
    return '\n'.join(html_parts)

def generate_static_html():
    """Генерирует статичный HTML файл"""
    # Загружаем исходный index.html
    with open('index.html', 'r', encoding='utf-8') as f:
        html_content = f.read()
    
    # Загружаем галерею
    gallery_items = load_gallery()
    gallery_html = generate_gallery_html(gallery_items)
    
    # Заменяем пустую секцию галереи на статичный HTML
    gallery_section_pattern = r'(<section class="gallery" id="gallery">)\s*</section>'
    html_content = re.sub(gallery_section_pattern, r'\1\n' + gallery_html + '\n    </section>', html_content)
    
    # Удаляем динамическую загрузку галереи и заменяем на простую логику прелоадера
    # Находим функцию loadGallery и заменяем её на упрощенную версию
    load_gallery_pattern = r'async function loadGallery\(\) \{.*?hidePreloader\(\);.*?\n    \}'
    
    # Упрощенная версия loadGallery для статичного сайта
    static_load_gallery = '''    async function loadGallery() {
        const gallery = document.getElementById('gallery');
        const preloaderPercent = document.getElementById('preloader-percent');
        
        // В статичной версии все уже загружено, просто ждем немного для стабилизации колонок
        await new Promise(resolve => {
            requestAnimationFrame(() => {
                requestAnimationFrame(() => {
                    setTimeout(resolve, 200);
                });
            });
        });
        
        hidePreloader();
    }'''
    
    html_content = re.sub(load_gallery_pattern, static_load_gallery, html_content, flags=re.DOTALL)
    
    # Сохраняем результат
    output_file = 'index_static.html'
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    return output_file, len(gallery_items)

if __name__ == '__main__':
    try:
        output_file, item_count = generate_static_html()
        print(f'✓ Статичный сайт сгенерирован: {output_file}')
        print(f'  Включено элементов галереи: {item_count}')
    except Exception as e:
        print(f'✗ Ошибка генерации: {e}')
        exit(1)

