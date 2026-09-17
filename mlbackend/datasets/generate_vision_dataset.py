import os
import csv
import random
from pathlib import Path
from PIL import Image, ImageDraw

CLASSES = [
    "Pepper__bell___Bacterial_spot",
    "Pepper__bell___healthy",
    "Potato___Early_blight",
    "Potato___Late_blight",
    "Potato___healthy",
    "Tomato_Bacterial_spot",
    "Tomato_Early_blight",
    "Tomato_Late_blight",
    "Tomato_Leaf_Mold",
    "Tomato_Septoria_leaf_spot"
]

IMAGES_PER_CLASS = 10
IMG_SIZE = 128

def generate_synthetic_leaf(class_name: str, path: Path):
    """Generates a synthetic 128x128 image with a visual pattern for reproducibility testing."""
    # Base color depends on if it's healthy or not
    is_healthy = "healthy" in class_name.lower()
    
    base_color = (
        random.randint(20, 50),
        random.randint(100, 150) if is_healthy else random.randint(80, 120),
        random.randint(20, 50)
    )
    
    img = Image.new("RGB", (IMG_SIZE, IMG_SIZE), color=base_color)
    draw = ImageDraw.Draw(img)
    
    # Add random leaf-like veins
    for _ in range(5):
        start = (random.randint(0, IMG_SIZE), random.randint(0, IMG_SIZE))
        end = (random.randint(0, IMG_SIZE), random.randint(0, IMG_SIZE))
        draw.line([start, end], fill=(0, 50, 0), width=2)
        
    # If diseased, add disease spots
    if not is_healthy:
        spot_color = (
            random.randint(100, 150) if "mold" in class_name.lower() else random.randint(50, 100),
            random.randint(50, 100),
            random.randint(20, 50)
        )
        for _ in range(random.randint(5, 15)):
            r = random.randint(2, 10)
            cx, cy = random.randint(0, IMG_SIZE), random.randint(0, IMG_SIZE)
            draw.ellipse([cx-r, cy-r, cx+r, cy+r], fill=spot_color)
            
    img.save(path)

def main():
    print("=========================================================")
    print("AgriSaathi Vision Dataset Generator (CI/Reproducibility)")
    print("=========================================================")
    
    root_dir = Path(__file__).resolve().parents[2]
    vision_dir = root_dir / "datasets" / "vision"
    images_dir = vision_dir / "images"
    manifest_path = vision_dir / "vision_manifest.csv"
    
    images_dir.mkdir(parents=True, exist_ok=True)
    
    manifest_rows = []
    
    for cls in CLASSES:
        cls_dir = images_dir / cls
        cls_dir.mkdir(parents=True, exist_ok=True)
        
        print(f"Generating synthetic images for: {cls}")
        for i in range(IMAGES_PER_CLASS):
            filename = f"synth_{i:03d}.jpg"
            img_path = cls_dir / filename
            generate_synthetic_leaf(cls, img_path)
            
            # Group ID assigns groups for GroupShuffleSplit (e.g. simulating same-plant images)
            group_id = f"plant_{i // 3}"
            manifest_rows.append({
                "path": str(Path("vision/images") / cls / filename).replace("\\", "/"),
                "label": cls,
                "group_id": group_id
            })
            
    # Write manifest
    print(f"Writing manifest to {manifest_path}")
    with open(manifest_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["path", "label", "group_id"])
        writer.writeheader()
        for row in manifest_rows:
            writer.writerow(row)
            
    print("Dataset generation complete. The repository can now execute train_vision_model.py end-to-end.")

if __name__ == "__main__":
    main()
