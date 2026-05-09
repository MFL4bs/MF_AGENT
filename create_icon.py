"""
Script para crear el archivo .ico desde MF_LABS.png
"""
from PIL import Image
from pathlib import Path

def create_icon():
    """Convierte MF_LABS.png a MF_LABS.ico con múltiples tamaños."""
    
    png_path = Path("MF_LABS.png")
    ico_path = Path("MF_LABS.ico")
    
    if not png_path.exists():
        print("ERROR: MF_LABS.png no encontrado")
        return
    
    try:
        # Abrir imagen
        img = Image.open(png_path)
        
        # Convertir a RGBA si no lo está
        if img.mode != 'RGBA':
            img = img.convert('RGBA')
        
        # Crear múltiples tamaños para el .ico
        icon_sizes = [(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
        
        # Guardar como .ico con múltiples tamaños
        img.save(ico_path, format='ICO', sizes=icon_sizes)
        
        print(f"OK Icono creado exitosamente: {ico_path}")
        print(f"   Tamanos incluidos: {', '.join([f'{w}x{h}' for w, h in icon_sizes])}")
        
    except Exception as e:
        print(f"ERROR al crear icono: {e}")
        print("   Instalando Pillow...")
        import subprocess
        subprocess.run(["pip", "install", "Pillow"], check=True)
        print("   Intenta ejecutar el script nuevamente")

if __name__ == "__main__":
    create_icon()
