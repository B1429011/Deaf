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

## 網頁操作（可使用耳機麥克風）

啟動本機網頁伺服器：

```powershell
cd Deaf
python -m deaf_agent.web_server
```

瀏覽器開啟 <http://127.0.0.1:8000>，按「啟用耳機麥克風」並允許權限。瀏覽器會顯示耳機麥克風音量；按「送出目前資料」即可將資料送入 Agent Runtime。按「模擬喇叭事件」可以直接查看完整的喇叭聲提醒流程。

目前網頁已完成麥克風接入、音量讀取、資料送出與結果顯示；聲音分類仍使用示範事件選單，日後接入真實模型後可改為由 YAMNet、PANNs 或 AST 自動產生事件類型。

