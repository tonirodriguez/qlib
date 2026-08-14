# SFM — Pipeline de Entrenamiento con Qlib

## Estrategia: Multivariable vs Univariable

| Enfoque | input_dim | output_dim | Ventaja |
|---------|-----------|------------|---------|
| **Multivariable** | 5 (todas las cryptos) | 5 | Aprende correlaciones cruzadas (BTC → altcoins) |
| **Univariable** | 1 (una crypto) | 1 | Se especializa en la dinámica del activo sin ruido de otras |

Recomendación: entrenar ambos y comparar MAPE. El multivariable suele ganar en activos correlacionados (XLM, ADA); el univariable en BTC y ETH.

## Pipeline de Entrenamiento

### 1. Extracción desde Qlib

```python
def load_and_process_crypto_data(cryptos, start_date, end_date):
    fields = ['$close']
    df_qlib = D.features(cryptos, fields, start_time=start_date, end_time=end_date)
    df_reset = df_qlib.reset_index()

    df_close = df_reset.pivot(index='datetime', columns='instrument', values='$close')[cryptos]
    df_pct = df_close.pct_change().fillna(0)
    df_mean_5 = df_close.rolling(window=5).mean().fillna(df_close)
    df_ratio = (df_mean_5 / df_close).fillna(1.0)

    market_matrix = np.hstack([df_close.values, df_pct.values, df_ratio.values])
    labels_matrix = df_pct.shift(-1).fillna(0).values

    return market_matrix, labels_matrix, df_close, df_pct
```

### 2. Ventanas deslizantes

```python
def make_sliding_windows(market_matrix, labels_matrix, lookback=30):
    X, y = [], []
    for i in range(len(market_matrix) - lookback - 1):
        X.append(market_matrix[i: i + lookback, :])
        y.append(labels_matrix[i + lookback, :])
    return torch.tensor(np.array(X), dtype=torch.float32), \
           torch.tensor(np.array(y), dtype=torch.float32)
```

### 3. Split cronológico (70/15/15)

```python
def split_chronologically(X, y, train_frac=0.70, val_frac=0.15):
    n = len(X)
    train_end = int(n * train_frac)
    val_end = int(n * (train_frac + val_frac))
    return (X[:train_end], y[:train_end]), \
           (X[train_end:val_end], y[train_end:val_end]), \
           (X[val_end:], y[val_end:])
```

### 4. Normalización

```python
scaler = MinMaxScaler(feature_range=(-1, 1))
market_train_scaled = scaler.fit_transform(market_train)
market_val_scaled = scaler.transform(market_val)
market_test_scaled = scaler.transform(market_test)
```

### 5. Entrenamiento con Early Stopping

```python
def train_with_early_stopping(model, train_loader, val_loader, epochs=100,
                              lr=0.001, patience=10, device="cpu", model_path="best.pth"):
    criterion = nn.MSELoss()
    optimizer = optim.AdamW(model.parameters(), lr=lr, weight_decay=1e-4)
    best_val_loss = float("inf")
    patience_counter = 0

    for epoch in range(epochs):
        model.train()
        train_loss = 0.0
        for bx, by in train_loader:
            bx, by = bx.to(device), by.to(device)
            optimizer.zero_grad()
            loss = criterion(model(bx), by)
            loss.backward()
            optimizer.step()
            train_loss += loss.item()
        train_loss /= len(train_loader)

        model.eval()
        val_loss = 0.0
        with torch.no_grad():
            for bx, by in val_loader:
                bx, by = bx.to(device), by.to(device)
                loss = criterion(model(bx), by)
                val_loss += loss.item()
        val_loss /= len(val_loader)

        if val_loss < best_val_loss:
            best_val_loss = val_loss
            patience_counter = 0
            torch.save(model.state_dict(), model_path)
        else:
            patience_counter += 1

        if patience_counter >= patience:
            print(f"Early stopping en época {epoch+1}")
            break

    model.load_state_dict(torch.load(model_path))
    return history
```

### 6. Reentreno final (opcional)

Tras early stopping, se reentrena sobre **train + val** combinado con LR reducido a la mitad durante ~10 épocas.

## Integración con Qlib Model class

```python
from qlib.model.base import Model

class QlibSFMModel(Model):
    def __init__(self, input_dim=3, hidden_dim=64, freq_components=10, output_dim=1, epochs=20, lr=0.001):
        super().__init__()
        self.net = SFMModelRefined(input_dim, hidden_dim, freq_components, output_dim)
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.net.to(self.device)

    def fit(self, dataset):
        df_train = dataset.prepare("train", col_set=["feature", "label"], as_dataframe=True)
        # ... convertir a tensores 3D y entrenar

    def predict(self, dataset):
        df_test = dataset.prepare("test", col_set="feature", as_dataframe=True)
        # ... predecir y devolver pd.Series con index original
        return predictions
```

## Archivos relacionados

- `scripts/crypto/qlib_sfm_pipeline.py`
- `scripts/crypto/qlib_sfm_pipeline.v2.py`
- `scripts/crypto/qlib_sfm_pipeline_grafica.py`
- `scripts/crypto/Modelo_SFM_Crypto.ipynb`
