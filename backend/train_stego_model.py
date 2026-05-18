import torch
import torch.nn as nn
import torch.nn.functional as F
import torch.optim as optim
from torch.utils.data import Dataset, DataLoader
from PIL import Image
import numpy as np
import os
import random
from steganalysis_model import StegoCNN

# --- Helper: Simple LSB Embedding for Training Data Generation ---
def embed_lsb_random(img_pil):
    """
    Synthetic Data Generation:
    This 'fakes' a stego image by flipping the Least Significant Bit (LSB) of pixels.
    This gives the AI examples of what hidden data 'looks' like at the pixel level.
    """
    arr = np.array(img_pil.convert("RGB"))
    # Create random binary noise (0 or 1)
    noise = np.random.randint(0, 2, arr.shape, dtype=np.uint8)
    
    # Clear the last bit (& 0xFE) and add our noise (| noise)
    stego_arr = (arr & 0xFE) | noise
    return Image.fromarray(stego_arr)

class StegoDataset(Dataset):
    def __init__(self, image_paths, transform=None):
        self.image_paths = image_paths
        self.transform = transform
        
    def __len__(self):
        return len(self.image_paths) * 2 # Each image gives 1 Cover + 1 Stego
    
    def __getitem__(self, idx):
        # Even indices = Cover, Odd indices = Stego
        img_idx = idx // 2
        is_stego = idx % 2 == 1
        
        try:
            img_path = self.image_paths[img_idx]
            img = Image.open(img_path).convert("RGB")
            
            # Resize for training (standard size)
            img = img.resize((256, 256))
            
            if is_stego:
                img = embed_lsb_random(img)
                label = 1 # Stego
            else:
                label = 0 # Clean
            
            # Convert to Tensor (C, H, W) and Normalize [0,1]
            img_arr = np.array(img).transpose(2, 0, 1) / 255.0
            img_tensor = torch.FloatTensor(img_arr)
            
            return img_tensor, label
            
        except Exception as e:
            # Fallback for bad images
            return torch.zeros(3, 256, 256), 0

def train_model(image_dir, epochs=5):
    """
    Trains the StegoCNN on images found in image_dir.
    """
    # 1. Find images
    exts = ('.png', '.jpg', '.jpeg')
    image_paths = [os.path.join(image_dir, f) for f in os.listdir(image_dir) if f.lower().endswith(exts)]
    
    if not image_paths:
        print("Training Error: No images found in directory.")
        return None
        
    print(f"Dataset initialized: Found {len(image_paths)} images. Generated {len(image_paths)*2} samples (Cover+Stego).")
    
    # 2. Setup
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Device configuration: Training on {device}")
    
    model = StegoCNN().to(device)
    optimizer = optim.Adam(model.parameters(), lr=0.001)
    criterion = nn.CrossEntropyLoss()
    
    dataset = StegoDataset(image_paths)
    dataloader = DataLoader(dataset, batch_size=8, shuffle=True)
    
    # 3. Train Loop
    model.train()
    for epoch in range(epochs):
        total_loss = 0
        correct = 0
        total = 0
        
        for inputs, labels in dataloader:
            inputs, labels = inputs.to(device), labels.to(device)
            
            optimizer.zero_grad()
            outputs = model(inputs)
            loss = criterion(outputs, labels)
            loss.backward()
            optimizer.step()
            
            total_loss += loss.item()
            _, predicted = torch.max(outputs.data, 1)
            total += labels.size(0)
            correct += (predicted == labels).sum().item()
            
        acc = 100 * correct / total
        print(f"   Epoch {epoch+1}/{epochs} | Loss: {total_loss/len(dataloader):.4f} | Acc: {acc:.2f}%")
        
    # 4. Save
    torch.save(model.state_dict(), "stego_model.pth")
    print("Model training complete. Weights saved to 'stego_model.pth'")
    return model

def predict_image(model, img_input):
    """
    Inference Logic:
    Takes an unknown image and runs it through the trained AI 'Detective'.
    Returns a probability score (0.0 to 1.0) of how likely it is to be 'Stego'.
    """
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model.eval() # Important: Tells the AI we are 'testing', not 'learning'.
    
    if isinstance(img_input, str):
        img = Image.open(img_input).convert("RGB")
    else:
        img = img_input.convert("RGB")
        
    img = img.resize((256, 256)) # Standardize size for the neural network
    
    # Convert image to a mathematical 'Tensor' (Decimal numbers instead of Integers)
    img_arr = np.array(img).transpose(2, 0, 1) / 255.0
    img_tensor = torch.FloatTensor(img_arr).unsqueeze(0).to(device)
    
    with torch.no_grad(): # Disable gradient tracking to save memory/speed
        outputs = model(img_tensor)
        probs = F.softmax(outputs, dim=1) # Convert brain signals to percentages
        score_stego = probs[0][1].item() # Extract the 'Stego' probability
        
    return score_stego # Final score (e.g., 0.85 means 85% chance of hidden data)
