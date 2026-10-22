# Esempi di funzioni Muvia

Funzioni pronte per [Muvia](https://muviabi.com/it), ognuna con il suo contratto e un test che gira
sul tuo computer. Importale in un progetto, usale così come sono in un flusso, o parti da una per
scrivere la tua. [Read in English](README.md).

| Tema | Funzione | Cosa fa |
| --- | --- | --- |
| Business | [`receivables_aging`](functions/business/receivables_aging.py) | I crediti aperti di ogni cliente per giorni di ritardo: non scaduti, 1-30, 31-60, 61-90, oltre 90 |
| Business | [`rfm_segments`](functions/business/rfm_segments.py) | Recenza, frequenza e valore di ogni cliente, con un punteggio da 1 a 5, e il suo segmento |
| Business | [`weighted_pipeline`](functions/business/weighted_pipeline.py) | Le trattative aperte per mese di chiusura e fase, pesate per la loro probabilità |
| Business | [`demand_forecast`](functions/business/demand_forecast.py) | Le quantità di ogni prodotto nelle prossime settimane, con una fascia del 95% circa |
| Industria | [`oee`](functions/industrial/oee.py) | Disponibilità, prestazioni, qualità e OEE di ogni turno, giorno o commessa |
| Industria | [`signal_anomalies`](functions/industrial/signal_anomalies.py) | Lo z-score di ogni lettura rispetto a quelle precedenti, e se è un'anomalia |
| Industria | [`stop_events`](functions/industrial/stop_events.py) | Le fermate di una macchina, una riga ciascuna, dal segnale di marcia |
| Industria | [`energy_per_piece`](functions/industrial/energy_per_piece.py) | I wattora per pezzo e quanto si scostano dal solito; energia consumata senza produrre |
| Qualità dei dati | [`column_profile`](functions/data_quality/column_profile.py) | Valori mancanti, valori distinti e intervallo di ogni colonna di qualsiasi tabella |
| Qualità dei dati | [`duplicate_rows`](functions/data_quality/duplicate_rows.py) | Le righe la cui chiave compare più di una volta, raggruppate |
| Qualità dei dati | [`range_checks`](functions/data_quality/range_checks.py) | Le righe con il valore mancante o fuori dall'intervallo che scegli |
| Mercati | [`price_indicators`](functions/markets/price_indicators.py) | Variazione, medie mobili, tendenza, volatilità e RSI di ogni serie di prezzi |
| Mercati | [`price_vs_average`](functions/markets/price_vs_average.py) | Il prezzo di ogni venditore rispetto alla media del giorno per lo stesso prodotto, e la sua posizione |

## Usarne una in Muvia

Ogni funzione è fatta di due file con lo stesso nome: `<chiave>.py`, il codice, e `<chiave>.json`,
nome, descrizione e contratto.

1. Nel tuo progetto apri **Lab → Funzioni** e scegli **Importa**.
2. Seleziona i due file di ogni funzione che vuoi (anche più funzioni insieme).
3. Aggiungi la funzione a un flusso e collega il suo ingresso a una sorgente con le colonne del
   contratto (le trovi nel `.json`), oppure rinomina le colonne nella query della sorgente.

Se il progetto usa già la chiave di una funzione, te ne viene proposta un'altra. Una volta importata
la funzione è tua: cambia codice e contratto nell'editor e provala sulle tue righe.

I nomi e le descrizioni delle funzioni sono in inglese: puoi cambiarli dopo l'importazione.

## Come si scrive una funzione

```python
def transform(inputs, params, ctx):
    rows = inputs["rows"].copy()          # ogni tabella in ingresso è un DataFrame pandas
    rows["total"] = rows["price"] * rows["quantity"]
    return {"rows": rows}                 # un dict con esattamente le uscite del contratto
```

- `inputs` contiene ogni ingresso per nome: una tabella come DataFrame, gli altri come valore.
- `params` contiene i parametri del nodo, come li dichiara il `form_config` del contratto. Leggili
  con `params.get("nome", predefinito)`.
- `ctx.window.start` e `ctx.window.end` sono il periodo dell'esecuzione (`start` è `None` alla prima
  esecuzione del flusso, `end` è escluso); `ctx.logger` scrive nel log dell'esecuzione;
  `ctx.preview` è vero in una prova.
- La funzione restituisce un dict con esattamente le uscite del contratto come chiavi. Scrivi ogni
  `return` come dict con chiavi letterali, così l'editor legge le uscite dal codice.
- Le funzioni girano senza accesso alla rete. Le librerie disponibili sono la libreria standard di
  Python, NumPy, pandas, PyArrow, SciPy, scikit-learn, statsmodels, LightGBM, joblib, Matplotlib,
  openpyxl, PyWavelets e ONNX Runtime.

Il contratto (`contract` nel `.json`) dice cosa la funzione prende e restituisce: le colonne di ogni
porta e il loro tipo (`time`, `string`, `integer`, `float`, `boolean`, `any`), se un'uscita è una
tabella nuova (`"shape": "fixed"`) o il suo ingresso con colonne in più (`"shape": "derived"`), i
parametri, il tempo massimo e dove può girare (`"targets": ["cloud", "edge"]`). Muvia controlla le
righe rispetto al contratto prima e dopo ogni chiamata.

## Eseguire i test

Serve [uv](https://docs.astral.sh/uv/): installa Python 3.14 e le stesse versioni delle librerie
con cui girano le funzioni in Muvia.

```sh
uv sync
uv run pytest
```

`muvia_local.run` chiama una funzione come fa Muvia e controlla ingressi e uscite rispetto al suo
contratto:

```python
from muvia_local import run

outputs = run("functions/industrial/oee", {"production": il_mio_dataframe})
```

È un banco di prova, non Muvia: non limita tempo e memoria, non toglie la rete, e non ha le funzioni
di `ctx` che richiedono una capacità (notifiche, asset, documenti, il modello AI).

## Contribuire

Idee e correzioni sono benvenute. Un nuovo esempio è una coppia di file in `functions/<tema>/` e un
test in `tests/test_<tema>.py` con righe abbastanza poche da controllarle a mano; `uv run pytest`
deve passare.

## Licenza

[MIT](LICENSE).
