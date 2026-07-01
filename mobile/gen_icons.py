from PIL import Image
import os

src = r'D:\Projects\MF_AGENT\MF_LABS.png'
base = r'D:\Projects\mf_agent_mobile\android\app\src\main\res'

img = Image.open(src).convert('RGBA')
bg = Image.new('RGBA', img.size, (255, 255, 255, 255))
bg.paste(img, mask=img.split()[3])
img_flat = bg.convert('RGB')

sizes = {
    'mipmap-mdpi':    48,
    'mipmap-hdpi':    72,
    'mipmap-xhdpi':   96,
    'mipmap-xxhdpi':  144,
    'mipmap-xxxhdpi': 192,
}

for folder, size in sizes.items():
    path = os.path.join(base, folder, 'ic_launcher.png')
    img_flat.resize((size, size), Image.LANCZOS).save(path, 'PNG')
    print(f'{folder}: {size}x{size} -> {os.path.getsize(path)} bytes')

print('Iconos generados correctamente.')
