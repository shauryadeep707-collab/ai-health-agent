import os
import sys

# Ensure UTF-8 output on Windows consoles
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader
from torchvision import datasets, transforms
from PIL import Image

# =====================================================================
# [BHAI YAHAN APNA DATASET KA PATH CHANGE KARNA HAI JAB BHI BADALNA HO]
# =====================================================================
DATASET_PATH = r"model train\dataset"
# Example (Agar full path dena ho):
# DATASET_PATH = r"C:\Users\shaur\OneDrive\Desktop\ai heal\model train\dataset"
# =====================================================================

BATCH_SIZE = 64
LEARNING_RATE = 0.001
EPOCHS = 8
MODEL_SAVE_PATH = r"model train\medical_report_cnn.pth"

# 1. Custom CNN Model Architecture
class MedicalReportCNN(nn.Module):
    def __init__(self, num_classes):
        super(MedicalReportCNN, self).__init__()
        self.features = nn.Sequential(
            # Block 1
            nn.Conv2d(1, 16, kernel_size=3, padding=1),
            nn.BatchNorm2d(16),
            nn.ReLU(),
            nn.MaxPool2d(2, 2),  # 128x128 -> 64x64

            # Block 2
            nn.Conv2d(16, 32, kernel_size=3, padding=1),
            nn.BatchNorm2d(32),
            nn.ReLU(),
            nn.MaxPool2d(2, 2),  # 64x64 -> 32x32

            # Block 3
            nn.Conv2d(32, 64, kernel_size=3, padding=1),
            nn.BatchNorm2d(64),
            nn.ReLU(),
            nn.MaxPool2d(2, 2)   # 32x32 -> 16x16
        )
        self.classifier = nn.Sequential(
            nn.Dropout(0.3),
            nn.Linear(64 * 16 * 16, 128),
            nn.ReLU(),
            nn.Linear(128, num_classes)
        )

    def forward(self, x):
        x = self.features(x)
        x = x.view(x.size(0), -1)
        return self.classifier(x)

def main():
    print("=" * 60)
    print("AI HEALTH AGENT - LOCAL CNN MODEL TRAINING")
    print("=" * 60)
    print(f"Dataset Path: {DATASET_PATH}")

    if not os.path.exists(DATASET_PATH):
        print(f"[ERROR] Folder '{DATASET_PATH}' nahi mila!")
        return

    # Image transformations: 128x128, Grayscale, ToTensor
    transform = transforms.Compose([
        transforms.Resize((128, 128)),
        transforms.Grayscale(num_output_channels=1),
        transforms.RandomRotation(10),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.5], std=[0.5])
    ])

    try:
        dataset = datasets.ImageFolder(root=DATASET_PATH, transform=transform)
    except Exception as e:
        print(f"[ERROR] Loading dataset: {e}")
        return

    if len(dataset) == 0:
        print("\n[NOTE] Folder mein abhi koi photos nahi hain!")
        print("Kripya 'model train/dataset/' ke sub-folders mein photos daalein:")
        for sub in sorted(os.listdir(DATASET_PATH)):
            subpath = os.path.join(DATASET_PATH, sub)
            if os.path.isdir(subpath):
                print(f"  -> {subpath}")
        return

    classes = dataset.classes
    num_classes = len(classes)
    print(f"[OK] Total Images Found: {len(dataset)}")
    print(f"[OK] Classes Detected ({num_classes}): {classes}")

    dataloader = DataLoader(dataset, batch_size=BATCH_SIZE, shuffle=True)

    # Use GPU if available, else CPU
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Training Device: {device}")

    model = MedicalReportCNN(num_classes=num_classes).to(device)

    # Resume if previous model exists
    if os.path.exists(MODEL_SAVE_PATH):
        try:
            model.load_state_dict(torch.load(MODEL_SAVE_PATH, map_location=device))
            print("[INFO] Purana trained checkpoint load kar liya gaya hai (Continuing training)!")
        except Exception:
            print("[INFO] Nayi training zero se shuru ho rahi hai...")

    criterion = nn.CrossEntropyLoss()
    optimizer = optim.Adam(model.parameters(), lr=LEARNING_RATE)

    print("\nTraining shuru ho rahi hai...")
    model.train()
    for epoch in range(EPOCHS):
        running_loss = 0.0
        correct = 0
        total = 0

        for images, labels in dataloader:
            images, labels = images.to(device), labels.to(device)

            optimizer.zero_grad()
            outputs = model(images)
            loss = criterion(outputs, labels)
            loss.backward()
            optimizer.step()

            running_loss += loss.item() * images.size(0)
            _, predicted = torch.max(outputs, 1)
            total += labels.size(0)
            correct += (predicted == labels).sum().item()

        epoch_loss = running_loss / total
        epoch_acc = (correct / total) * 100
        print(f"  Epoch [{epoch+1}/{EPOCHS}] | Loss: {epoch_loss:.4f} | Accuracy: {epoch_acc:.1f}%")

    # Save trained model
    torch.save(model.state_dict(), MODEL_SAVE_PATH)
    print("\n" + "=" * 60)
    print(f"Training 100% Complete!")
    print(f"Model Saved at: {MODEL_SAVE_PATH}")
    print("=" * 60)

if __name__ == "__main__":
    main()
