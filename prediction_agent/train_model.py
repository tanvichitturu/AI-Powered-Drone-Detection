import os
import shutil
from ultralytics import YOLO

def train_drone_model():
    # 1. Setup absolute paths so the script never gets lost
    current_dir = os.path.dirname(os.path.abspath(__file__))
    dataset_yaml = os.path.join(current_dir, '..', 'drone_dataset', 'data.yaml')
    runs_dir = os.path.join(current_dir, 'runs')
    weights_dir = os.path.join(current_dir, 'weights')
    
    print("[TRAINING] Downloading and initializing YOLOv8 Nano base model...")
    model = YOLO("yolov8n.pt")
    
    print(f"[TRAINING] Starting training pipeline using: {dataset_yaml}")
    
    # 2. Run the training process
    model.train(
        data=dataset_yaml,
        epochs=50,
        imgsz=640,
        project=runs_dir,
        name="drone_training_run",
        exist_ok=True # Overwrites the run folder if you train multiple times
    )
    
    # 3. Locate the newly minted weights
    trained_model_path = os.path.join(runs_dir, 'drone_training_run', 'weights', 'best.pt')
    final_model_path = os.path.join(weights_dir, 'yolo_drone_model.pt')
    
    # 4. Create weights directory if you haven't already
    os.makedirs(weights_dir, exist_ok=True)
    
    # 5. Auto-install the model for the detection agent
    if os.path.exists(trained_model_path):
        print(f"\n[TRAINING] Moving fresh model to {final_model_path}...")
        shutil.copy(trained_model_path, final_model_path)
        print("[SUCCESS] Training complete! Your detection agent is ready to hunt drones.")
    else:
        print("\n[ERROR] Training finished, but 'best.pt' could not be found.")

if __name__ == '__main__':
    train_drone_model()