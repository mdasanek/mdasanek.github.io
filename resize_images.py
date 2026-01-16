#!/usr/bin/env python3
"""
Скрипт для уменьшения изображений в галерее до максимального размера 1200px
"""
import json
import os
from PIL import Image

MAX_SIZE = 1200

def load_gallery():
    """Загружает данные галереи из gallery.json"""
    try:
        with open('gallery.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        print("✗ Файл gallery.json не найден")
        return []

def is_image_file(filename):
    """Проверяет, является ли файл изображением (не видео)"""
    if not filename:
        return False
    filename_lower = filename.lower()
    # Исключаем видео форматы
    if filename_lower.endswith(('.mp4', '.webm')):
        return False
    # Проверяем, что это webp (или другой формат изображения)
    return filename_lower.endswith(('.webp', '.jpg', '.jpeg', '.png', '.gif'))

def resize_image(image_path, max_size=MAX_SIZE):
    """
    Уменьшает изображение, если оно больше max_size по любой стороне.
    Сохраняет пропорции.
    Возвращает True, если изображение было изменено, False если нет.
    """
    if not os.path.exists(image_path):
        print(f"  ⚠ Файл не найден: {image_path}")
        return False
    
    try:
        with Image.open(image_path) as img:
            width, height = img.size
            
            # Если обе стороны меньше или равны max_size, ничего не делаем
            if width <= max_size and height <= max_size:
                return False
            
            # Вычисляем новые размеры с сохранением пропорций
            if width > height:
                # Ширина больше - уменьшаем по ширине
                new_width = max_size
                new_height = int(height * (max_size / width))
            else:
                # Высота больше или равны - уменьшаем по высоте
                new_height = max_size
                new_width = int(width * (max_size / height))
            
            # Уменьшаем изображение
            resized_img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
            
            # Сохраняем обратно в тот же файл с максимальным качеством (lossless)
            resized_img.save(image_path, 'WEBP', lossless=True)
            
            print(f"  ✓ {image_path}: {width}x{height} → {new_width}x{new_height}")
            return True
            
    except Exception as e:
        print(f"  ✗ Ошибка при обработке {image_path}: {e}")
        return False

def process_all_images():
    """Обрабатывает все изображения в папке w/"""
    w_dir = 'w'
    
    if not os.path.exists(w_dir):
        print(f"✗ Папка {w_dir} не найдена")
        return
    
    # Получаем все файлы в папке w/
    all_files = os.listdir(w_dir)
    image_files = [f for f in all_files if is_image_file(f)]
    
    if not image_files:
        print(f"✗ Изображения в папке {w_dir} не найдены")
        return
    
    print(f"Найдено изображений в папке {w_dir}: {len(image_files)}")
    print(f"Обрабатываю изображения (максимальный размер: {MAX_SIZE}px)...\n")
    
    processed = 0
    resized = 0
    skipped = 0
    errors = 0
    
    for filename in sorted(image_files):
        image_path = os.path.join(w_dir, filename)
        
        processed += 1
        
        # Обрабатываем изображение
        try:
            if resize_image(image_path, MAX_SIZE):
                resized += 1
            else:
                skipped += 1
        except Exception as e:
            print(f"  ✗ Ошибка при обработке {image_path}: {e}")
            errors += 1
    
    print(f"\n✓ Обработка завершена:")
    print(f"  Обработано изображений: {processed}")
    print(f"  Уменьшено: {resized}")
    print(f"  Оставлено без изменений: {skipped}")
    if errors > 0:
        print(f"  Ошибок: {errors}")

if __name__ == '__main__':
    try:
        process_all_images()
    except KeyboardInterrupt:
        print("\n\n✗ Прервано пользователем")
        exit(1)
    except Exception as e:
        print(f"\n✗ Критическая ошибка: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
