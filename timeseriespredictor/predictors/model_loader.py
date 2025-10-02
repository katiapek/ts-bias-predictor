import torch

model = None

def load_model(path="model.pth"):
    global model
    model = torch.load(path)
    model.eval()
    print("Model loaded successfully.")

def predict(close_price):
    # Dummy example - replace with your real model input
    import torch
    x = torch.tensor([close_price], dtype=torch.float32)
    with torch.no_grad():
        return float(model(x).item())