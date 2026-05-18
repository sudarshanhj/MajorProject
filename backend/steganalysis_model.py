import torch
import torch.nn as nn
import torch.nn.functional as F
import numpy as np

class SRMConv2d(nn.Module):
    """
    SRM (Spatial Rich Model) Layer:
    This is a specialized preprocessing layer that uses fixed High-Pass Filters.
    Its job is to 'strip away' the image content (like colors and shapes) and 
    highlight the 'noise residuals' where hidden data (steganography) usually leaves traces.
    """
    def __init__(self):
        super(SRMConv2d, self).__init__()
        self.channels = 3  # Standard RGB channels
        
        # Define 3 basic high-pass filters (SRM kernels)
        # 1. KV Kernel (Residuals)
        k1 = np.array([[0, 0, 0, 0, 0],
                       [0, -1, 2, -1, 0],
                       [0, 2, -4, 2, 0],
                       [0, -1, 2, -1, 0],
                       [0, 0, 0, 0, 0]], dtype=np.float32)
        
        # 2. Edge Kernel
        k2 = np.array([[-1, 2, -2, 2, -1],
                       [2, -6, 8, -6, 2],
                       [-2, 8, -12, 8, -2],
                       [2, -6, 8, -6, 2],
                       [-1, 2, -2, 2, -1]], dtype=np.float32)
                       
        # 3. Square Kernel
        k3 = np.array([[0, 0, 0, 0, 0],
                       [0, 0, 0, 0, 0],
                       [0, 1, -2, 1, 0],
                       [0, -2, 4, -2, 0],
                       [0, 1, -2, 1, 0]], dtype=np.float32)

        # Normalize kernels: This ensures the filters don't artificially brighten 
        # or darken the noise map, keeping the mathematical values stable.
        k1 = k1 / 4.0
        k2 = k2 / 12.0
        k3 = k3 / 4.0
        
        # Stack them: (Out_Channels, In_Channels/Groups, H, W)
        # We want to apply each of the 3 filters to each of the 3 RGB channels independently.
        # So we'll have 9 output channels total (3 filters * 3 colors).
        
        filters = []
        for k in [k1, k2, k3]:
            # Replicate for RGB
            filters.append(k) 
            
        filters = np.array(filters) # Shape (3, 5, 5)
        
        # In PyTorch Conv2d: (out_channels, in_channels, kH, kW)
        # We want 3 output channels (one per filter type) per input channel.
        # Actually, simpler approach: Apply 1 filter to R, G, B separately.
        # Let's make 3 filters. We will apply them using group convolution.
        
        # Shape: (3, 1, 5, 5) -> 3 filters, each acts on 1 channel
        weight = torch.from_numpy(filters).unsqueeze(1).type(torch.FloatTensor)
        
        # We repeat this for RGB. 
        # Total weights: (9, 1, 5, 5). 
        # Groups = 3. Input = 3. Output = 9.
        # First 3 outputs = R filtered by k1, k2, k3
        # Next 3 outputs = G filtered by k1, k2, k3...
        
        self.weight = nn.Parameter(weight.repeat(3, 1, 1, 1), requires_grad=False)
        
    def forward(self, x):
        # The forward pass: 
        # 1. Takes the original image 'x' (Batch, 3, H, W)
        # 2. Applies the 3 SRM filters to each color channel.
        # 3. Returns a 'Noise Map' with 9 channels.
        return F.conv2d(x, self.weight, padding=2, groups=3)

class StegoCNN(nn.Module):
    """
    StegoCNN: The AI Detective.
    This model is trained to look at noise maps and decide if the noise looks
    'natural' or if it looks 'artificial' (indicating hidden data).
    """
    def __init__(self):
        super(StegoCNN, self).__init__()
        
        # 1. Pre-processing: SRM Filter
        self.srm = SRMConv2d()
        
        # 2. Feature Extraction
        # Input: 9 channels (residuals). Output: 16 channels.
        self.conv1 = nn.Sequential(
            nn.Conv2d(9, 16, kernel_size=3, padding=1),
            nn.BatchNorm2d(16),
            nn.ReLU(),
            nn.MaxPool2d(2, 2) # Downsample
        )
        
        self.conv2 = nn.Sequential(
            nn.Conv2d(16, 32, kernel_size=3, padding=1),
            nn.BatchNorm2d(32),
            nn.ReLU(),
            nn.MaxPool2d(2, 2)
        )
        
        self.conv3 = nn.Sequential(
            nn.Conv2d(32, 64, kernel_size=3, padding=1),
            nn.BatchNorm2d(64),
            nn.ReLU(),
            nn.MaxPool2d(2, 2)
        )
        
        self.conv4 = nn.Sequential(
            nn.Conv2d(64, 128, kernel_size=3, padding=1),
            nn.BatchNorm2d(128),
            nn.ReLU(),
            nn.AdaptiveAvgPool2d((1, 1)) # Global Average Pooling -> (Batch, 128, 1, 1)
        )
        
        # 3. Final Decision Logic (Classification)
        # We take the 128 learned patterns and condense them into a final answer.
        self.fc = nn.Sequential(
            nn.Linear(128, 64),
            nn.ReLU(),
            nn.Dropout(0.5), # Randomly ignore half the data to prevent 'memorizing' samples.
            nn.Linear(64, 2) # Output: [Probability_Clean, Probability_Stego]
        )
        
    def forward(self, x):
        # x: (Batch, 3, H, W)
        
        # 1. Extract Residuals (The "Secret Sauce")
        x = self.srm(x) # -> (Batch, 9, H, W)
        
        # 2. CNN Layers
        x = self.conv1(x)
        x = self.conv2(x)
        x = self.conv3(x)
        x = self.conv4(x)
        
        # 3. Flatten
        x = x.view(x.size(0), -1) # -> (Batch, 128)
        
        # 4. Classify
        x = self.fc(x)
        
        return x

def get_model():
    return StegoCNN()
