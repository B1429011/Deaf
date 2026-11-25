# Deaf Agent Prototype

這是依照「第六版本架構圖」與「雲地部署圖」建立的第一個可執行原型。

目前先完成一條透明的資料流：

```text
輸入感測資料
  -> 音訊前處理
  -> 聲音分類（YAMNet / PANNs / AST 介面）
  -> 方向估計（DOA / 麥克風陣列介面）
  -> Agent Runtime（Context Builder、Policy / State、Planner / Router）
  -> Structured Event Object
  -> UI 文字、Haptic 振動、LED 燈號
```

## 與第六版本架構的對應

| 架構元件 | 本原型中的程式 |
| --- | --- |
| 麥克風陣列、使用者輸入介面 | `InputEnvelope` |
| 音訊緩衝區、降噪 / VAD | `AudioPreprocessor` |
| YAMNet / PANNs / AST | `SoundClassifier`（目前是可替換的規則式示範） |
| DOA / 麥克風陣列 | `DirectionEstimator`（目前讀取示範方向資料） |
| Agent Orchestrator | `AgentRuntime` |
| Context Builder | `ContextBuilder` |
| Policy / State Store | `PolicyState` |
| Planner / Router | `PlannerRouter` |
| 結構化模型輸出 | `StructuredEvent` |
| UI / Display、Haptic Driver、LED / Light Driver | `OutputAction` |

雲地部署上，這個第一版把感測輸入、前處理與推論流程放在同一個本機程序中，方便先驗證資料格式。之後可將模型服務、資料儲存與 LLM Gateway 分別移到本地端伺服器或雲端。

## 執行

本原型只使用 Python 標準函式庫，不需要額外安裝套件。

```powershell
cd Deaf
..\\.venv\\Scripts\\python.exe -m deaf_agent.cli --demo
```

若尚未建立虛擬環境，也可以使用系統 Python：

```powershell
python -m deaf_agent.cli --demo
```

也可以傳入自己的 JSON：

```powershell
Get-Content .\\examples\\road_horn.json | python -m deaf_agent.cli
```

輸出會包含每個處理階段的結果，便於之後替換成真實模型或硬體驅動。

