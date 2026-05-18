import torch
import cv2
import numpy as np
import base64


def get_last_conv_layer(model):
    """
    Finds the last Conv2d layer in a PyTorch model.
    This is the target layer for Grad-CAM hook registration.
    """
    for layer in reversed(list(model.modules())):
        if isinstance(layer, torch.nn.Conv2d):
            return layer
    raise Exception("No Conv2d layer found in model")


def generate_gradcam(model, image_tensor, original_size=None, original_image_np=None):
    """
    Generates a Hybrid Grad-CAM + Canny Edge heatmap.

    Args:
        model: PyTorch model.
        image_tensor: (1, C, H, W) torch tensor, normalized per model requirements.
        original_size: (width, height) tuple of the user's original image.
        original_image_np: numpy array (H, W, 3) BGR of the original image for Canny edge detection.

    Returns:
        (heatmap_b64, pred_class, confidence)
        heatmap_b64 is None if image is CLEAN (pred_class == 0) with low confidence.
    """
    model.eval()

    gradients = []
    activations = []

    target_layer = get_last_conv_layer(model)

    def forward_hook(module, input, output):
        activations.append(output.detach())

    def backward_hook(module, grad_in, grad_out):
        gradients.append(grad_out[0].detach())

    f_hook = target_layer.register_forward_hook(forward_hook)
    b_hook = target_layer.register_full_backward_hook(backward_hook)

    device = next(model.parameters()).device
    image_tensor = image_tensor.to(device)
    image_tensor.requires_grad_(True)

    try:
        # Forward pass
        output = model(image_tensor)

        pred_class = torch.argmax(output, dim=1)
        confidence = torch.softmax(output, dim=1)[0, pred_class].item()

        # ─── CLEAN IMAGE SUPPRESSION ─────────────────────────────────────────
        # If model is confident the image is CLEAN, return no heatmap.
        if pred_class.item() == 0 and confidence > 0.55:
            return None, pred_class.item(), float(confidence)

        # Backward pass for the predicted class only
        model.zero_grad()
        output[0, pred_class].backward()

        if len(gradients) == 0 or len(activations) == 0:
            raise ValueError("Gradients/Activations not captured — hook registration failed")

        grad = gradients[-1].cpu().data.numpy()[0]   # (C, H, W)
        act  = activations[-1].cpu().data.numpy()[0] # (C, H, W)

        weights = np.mean(grad, axis=(1, 2))          # (C,)
        cam = np.zeros(act.shape[1:], dtype=np.float32)

        for i, w in enumerate(weights):
            cam += w * act[i]

        # ReLU — suppress negative contributions
        cam = np.maximum(cam, 0)

        # ─── FULL-FRAME RESOLUTION ALIGNMENT ─────────────────────────────────
        # Always resize to the ORIGINAL image dimensions — never 224x224
        if original_size:
            target_w, target_h = original_size  # PIL .size = (width, height)
        elif original_image_np is not None:
            target_h, target_w = original_image_np.shape[:2]
        else:
            target_h, target_w = image_tensor.shape[2], image_tensor.shape[3]

        cam = cv2.resize(cam, (target_w, target_h))

        # Standard Min-Max Normalization
        cam_min = np.min(cam)
        cam_max = np.max(cam)
        if cam_max > cam_min:
            cam = (cam - cam_min) / (cam_max - cam_min)
        else:
            return None, pred_class.item(), float(confidence)

        # Convert to uint8 heatmap using JET colormap
        heatmap_uint8 = np.uint8(255 * cam)
        heatmap_colored = cv2.applyColorMap(heatmap_uint8, cv2.COLORMAP_JET)

        # ─── HYBRID CANNY EDGE INTEGRATION ───────────────────────────────────
        # If we have the original image, extract structural edges and blend them
        # into the heatmap. This highlights image structure irrespective of
        # where the hidden data is located.
        if original_image_np is not None:
            orig_resized = cv2.resize(original_image_np, (target_w, target_h))
            gray = cv2.cvtColor(orig_resized, cv2.COLOR_BGR2GRAY)
            # Canny edge detection — detect structural boundaries
            edges = cv2.Canny(gray, threshold1=50, threshold2=150)
            # Dilate edges slightly for visibility
            kernel = np.ones((2, 2), np.uint8)
            edges = cv2.dilate(edges, kernel, iterations=1)
            # Convert edges to a 3-channel cyan overlay
            edge_overlay = np.zeros_like(heatmap_colored)
            edge_overlay[edges > 0] = [255, 255, 0]  # Cyan edges in BGR
            # Blend: 80% heatmap + 20% edge overlay
            heatmap_colored = cv2.addWeighted(heatmap_colored, 0.80, edge_overlay, 0.20, 0)

        # Encode to PNG Base64
        _, buffer = cv2.imencode('.png', heatmap_colored)
        heatmap_b64 = base64.b64encode(buffer).decode('utf-8')

        return heatmap_b64, pred_class.item(), float(confidence)

    finally:
        f_hook.remove()
        b_hook.remove()
