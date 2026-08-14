# SFM — Arquitectura PyTorch

## Celda SFM (SFMCell / SFMCellRefined)

La celda extiende una LSTM estándar añadiendo **descomposición en frecuencias** en el estado oculto. El flujo interno:

1. **Puertas LSTM** (input, forget, output, cell update) con activaciones sigmoid/tanh
2. **Actualización del estado de frecuencia** $S_t$ usando la matriz de pesos $W\_\omega$ (hidden_dim × K)
3. **Transformada Inversa de Fourier aproximada**: colapsa las $K$ frecuencias de vuelta al espacio oculto
4. **Estado oculto combinado**: $h_t = o_t \odot \tanh(c_t + h_{freq})$

### SFMCell (versión base)

```python
class SFMCell(nn.Module):
    def __init__(self, input_dim, hidden_dim, freq_components):
        super().__init__()
        self.hidden_dim = hidden_dim
        self.K = freq_components

        self.W_i = nn.Linear(input_dim + hidden_dim, hidden_dim)
        self.W_f = nn.Linear(input_dim + hidden_dim, hidden_dim)
        self.W_o = nn.Linear(input_dim + hidden_dim, hidden_dim)
        self.W_z = nn.Linear(input_dim + hidden_dim, hidden_dim)
        self.W_omega = nn.Parameter(torch.randn(hidden_dim, self.K))
        self.W_phi = nn.Parameter(torch.randn(hidden_dim, self.K))
        self.W_u = nn.Linear(self.K, 1)

    def forward(self, x, states):
        h_prev, c_prev, S_prev = states
        combined = torch.cat((x, h_prev), dim=1)

        i = torch.sigmoid(self.W_i(combined))
        f = torch.sigmoid(self.W_f(combined))
        o = torch.sigmoid(self.W_o(combined))
        z = torch.tanh(self.W_z(combined))

        c_t = f * c_prev + i * z

        W_w_expanded = self.W_omega.unsqueeze(0).expand(x.size(0), -1, -1)
        S_t = f.unsqueeze(-1) * S_prev + i.unsqueeze(-1) * torch.tanh(W_w_expanded)

        h_freq = torch.mean(S_t * torch.sin(W_w_expanded), dim=-1)
        h_t = o * torch.tanh(c_t + h_freq)

        return h_t, (h_t, c_t, S_t)
```

### SFMCellRefined (con Dropout)

Añade regularización vía dropout en la entrada combinada y en los componentes de frecuencia. Es la versión usada en producción.

```python
class SFMCellRefined(nn.Module):
    def __init__(self, input_dim, hidden_dim, freq_components, dropout_rate=0.2):
        super().__init__()
        self.hidden_dim = hidden_dim
        self.K = freq_components
        self.W_i = nn.Linear(input_dim + hidden_dim, hidden_dim)
        self.W_f = nn.Linear(input_dim + hidden_dim, hidden_dim)
        self.W_o = nn.Linear(input_dim + hidden_dim, hidden_dim)
        self.W_z = nn.Linear(input_dim + hidden_dim, hidden_dim)
        self.W_omega = nn.Parameter(torch.randn(hidden_dim, self.K))
        self.dropout = nn.Dropout(dropout_rate)

    def forward(self, x, states):
        h_prev, c_prev, S_prev = states
        combined = torch.cat((x, h_prev), dim=1)
        combined_drop = self.dropout(combined)

        i = torch.sigmoid(self.W_i(combined_drop))
        f = torch.sigmoid(self.W_f(combined_drop))
        o = torch.sigmoid(self.W_o(combined_drop))
        z = torch.tanh(self.W_z(combined_drop))

        c_t = f * c_prev + i * z

        W_w_expanded = self.W_omega.unsqueeze(0).expand(x.size(0), -1, -1)
        S_t = f.unsqueeze(-1) * S_prev + i.unsqueeze(-1) * torch.tanh(W_w_expanded)

        h_freq = torch.mean(self.dropout(S_t) * torch.sin(W_w_expanded), dim=-1)
        h_t = o * torch.tanh(c_t + h_freq)

        return h_t, (h_t, c_t, S_t)
```

## Modelo SFM Completo

Procesa una secuencia completa paso a paso a través de la celda SFM:

```python
class SFMModelRefined(nn.Module):
    def __init__(self, input_dim, hidden_dim, freq_components, output_dim, dropout_rate=0.2):
        super().__init__()
        self.hidden_dim = hidden_dim
        self.K = freq_components
        self.cell = SFMCellRefined(input_dim, hidden_dim, freq_components, dropout_rate)
        self.fc = nn.Linear(hidden_dim, output_dim)

    def forward(self, x):
        batch_size, seq_len, _ = x.size()
        h = torch.zeros(batch_size, self.hidden_dim).to(x.device)
        c = torch.zeros(batch_size, self.hidden_dim).to(x.device)
        S = torch.zeros(batch_size, self.hidden_dim, self.K).to(x.device)

        for t in range(seq_len):
            h, (h, c, S) = self.cell(x[:, t, :], (h, c, S))

        return self.fc(h)
```

## Optimizador

Usar **AdamW** en lugar de Adam estándar. AdamW desacopla el weight decay de la actualización adaptativa, lo que estabiliza celdas recurrentes personalizadas:

```python
optimizer = optim.AdamW(model.parameters(), lr=lr, weight_decay=1e-4)
```

## Archivos relacionados

- `scripts/crypto/qlib_sfm_pipeline.py`
- `scripts/crypto/qlib_sfm_pipeline.v2.py`
- `scripts/crypto/qlib_sfm_pipeline_grafica.py`
